from pathlib import Path

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

LOCALHOST_ORIGINS = [
    "http://localhost",
    "http://localhost:3000",
    "http://127.0.0.1",
    "http://127.0.0.1:3000",
]


def build_client(tmp_path: Path) -> TestClient:
    data_dir = tmp_path / "data"
    settings = Settings(
        app_env="test",
        data_dir=data_dir,
        uploads_dir=data_dir / "uploads",
        sqlite_path=data_dir / "memory_lens_test.db",
        allowed_origins=LOCALHOST_ORIGINS,
        chunk_processing_delay_seconds=0.0,
    )
    return TestClient(create_app(settings))


def test_healthz(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_session_and_chunk_flow(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    create_session_response = client.post("/v1/sessions")
    assert create_session_response.status_code == 200
    session_payload = create_session_response.json()
    session_id = session_payload["session_id"]

    upload_response = client.post(
        f"/v1/sessions/{session_id}/chunks",
        data={"start_ms": "0", "end_ms": "800", "source": "wearable", "device_id": "dev-1"},
        files={"file": ("chunk.wav", b"abc123", "audio/wav")},
    )
    assert upload_response.status_code == 200
    chunk_payload = upload_response.json()
    assert chunk_payload["status"] == "queued"
    assert chunk_payload["session_id"] == session_id

    session_get_response = client.get(f"/v1/sessions/{session_id}")
    assert session_get_response.status_code == 200
    session_data = session_get_response.json()

    assert session_data["session"]["session_id"] == session_id
    assert len(session_data["chunks"]) == 1
    assert session_data["chunks"][0]["source"] == "wearable"
    assert session_data["chunks"][0]["status"] in {"queued", "processed"}


def test_upload_to_missing_session_returns_404(tmp_path: Path) -> None:
    client = build_client(tmp_path)

    upload_response = client.post(
        "/v1/sessions/not-found/chunks",
        data={"start_ms": "0", "end_ms": "100", "source": "wearable"},
        files={"file": ("chunk.wav", b"abc123", "audio/wav")},
    )

    assert upload_response.status_code == 404


def test_upload_negative_time_range_returns_400(tmp_path: Path) -> None:
    client = build_client(tmp_path)
    create_session_response = client.post("/v1/sessions")
    session_id = create_session_response.json()["session_id"]

    upload_response = client.post(
        f"/v1/sessions/{session_id}/chunks",
        data={"start_ms": "-1", "end_ms": "100", "source": "wearable"},
        files={"file": ("chunk.wav", b"abc123", "audio/wav")},
    )

    assert upload_response.status_code == 400
