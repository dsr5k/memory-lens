from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_LOCALHOST_ORIGINS = [
    "http://localhost",
    "http://localhost:3000",
    "http://127.0.0.1",
    "http://127.0.0.1:3000",
]


@dataclass(frozen=True)
class Settings:
    app_env: str
    data_dir: Path
    uploads_dir: Path
    sqlite_path: Path
    allowed_origins: list[str]
    chunk_processing_delay_seconds: float

    @classmethod
    def from_env(cls) -> "Settings":
        root_dir = Path(__file__).resolve().parents[1]
        data_dir = Path(os.getenv("DATA_DIR", root_dir / "data")).resolve()
        sqlite_path = Path(os.getenv("SQLITE_PATH", data_dir / "memory_lens.db")).resolve()

        allowed_origins_env = os.getenv("ALLOWED_ORIGINS", "")
        allowed_origins = [
            origin.strip()
            for origin in allowed_origins_env.split(",")
            if origin.strip()
        ]
        if not allowed_origins:
            allowed_origins = DEFAULT_LOCALHOST_ORIGINS

        return cls(
            app_env=os.getenv("APP_ENV", "development"),
            data_dir=data_dir,
            uploads_dir=data_dir / "uploads",
            sqlite_path=sqlite_path,
            allowed_origins=allowed_origins,
            chunk_processing_delay_seconds=float(
                os.getenv("CHUNK_PROCESSING_DELAY_SECONDS", "0.2")
            ),
        )
