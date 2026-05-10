from __future__ import annotations

import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings
from app.db import (
    create_chunk,
    create_session,
    get_session,
    init_db,
    list_chunks_by_session,
    update_chunk_status,
)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def process_chunk(db_path: Path, chunk_id: str, delay_seconds: float) -> None:
    time.sleep(delay_seconds)
    update_chunk_status(db_path, chunk_id, status="processed", updated_at=utc_now_iso())


def sanitize_filename(filename: str) -> str:
    safe_name = Path(filename).name.strip()
    safe_name = re.sub(r"[^A-Za-z0-9._-]", "_", safe_name)
    return safe_name or "chunk.bin"


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.from_env()

    settings.data_dir.mkdir(parents=True, exist_ok=True)
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    settings.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
    init_db(settings.sqlite_path)

    app = FastAPI(title="Memory Lens API", version="0.1.0")
    app.state.settings = settings

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/v1/sessions")
    def create_session_endpoint() -> dict[str, str]:
        session_id = str(uuid.uuid4())
        created_at = utc_now_iso()
        session = create_session(settings.sqlite_path, session_id=session_id, created_at=created_at)
        return session

    @app.post("/v1/sessions/{session_id}/chunks")
    async def upload_session_chunk(
        session_id: str,
        background_tasks: BackgroundTasks,
        file: UploadFile = File(...),
        start_ms: int = Form(...),
        end_ms: int = Form(...),
        source: str = Form(...),
        device_id: str | None = Form(None),
    ) -> dict[str, str | int | None]:
        if start_ms < 0 or end_ms < 0 or end_ms <= start_ms:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Chunk time range must be non-negative and "
                    "end_ms must be greater than start_ms"
                ),
            )

        session = get_session(settings.sqlite_path, session_id=session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        chunk_id = str(uuid.uuid4())
        now = utc_now_iso()
        safe_filename = sanitize_filename(file.filename or "chunk.bin")
        chunk_filename = f"{chunk_id}_{safe_filename}"
        session_upload_dir = settings.uploads_dir / session_id
        session_upload_dir.mkdir(parents=True, exist_ok=True)
        destination = session_upload_dir / chunk_filename

        with destination.open("wb") as output:
            output.write(await file.read())

        chunk = create_chunk(
            settings.sqlite_path,
            {
                "chunk_id": chunk_id,
                "session_id": session_id,
                "file_path": str(destination),
                "start_ms": start_ms,
                "end_ms": end_ms,
                "source": source,
                "device_id": device_id,
                "status": "uploaded",
                "created_at": now,
                "updated_at": now,
            },
        )

        queued_at = utc_now_iso()
        update_chunk_status(settings.sqlite_path, chunk_id, status="queued", updated_at=queued_at)
        chunk["status"] = "queued"
        chunk["updated_at"] = queued_at

        background_tasks.add_task(
            process_chunk,
            db_path=settings.sqlite_path,
            chunk_id=chunk_id,
            delay_seconds=settings.chunk_processing_delay_seconds,
        )

        return chunk

    @app.get("/v1/sessions/{session_id}")
    def get_session_endpoint(session_id: str) -> dict[str, object]:
        session = get_session(settings.sqlite_path, session_id=session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        chunks = list_chunks_by_session(settings.sqlite_path, session_id=session_id)
        return {"session": session, "chunks": chunks}

    return app


app = create_app()
