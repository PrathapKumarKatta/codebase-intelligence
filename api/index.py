"""Vercel entry point; persistent data lives in Postgres, extraction in /tmp."""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
for key, value in {
    "APP_ENV": "production",
    "DEBUG": "false",
    "STORAGE_DIR": "/tmp/codebase-intelligence",
    "INGESTION_MODE": "inline",
    "EMBEDDING_PROVIDER": "fastembed",
    "HF_HOME": "/tmp/fastembed/huggingface",
    "HF_HUB_CACHE": "/tmp/fastembed/huggingface/hub",
    "HF_XET_CACHE": "/tmp/fastembed/huggingface/xet",
    "HF_HUB_DISABLE_XET": "1",
    "XDG_CACHE_HOME": "/tmp/fastembed/cache",
    "MAX_UPLOAD_SIZE_MB": "4",
    "MAX_EXTRACTED_SIZE_MB": "10",
    "MAX_PROJECT_FILES": "100",
    "MAX_PROJECT_CHUNKS": "300",
    "LLM_PROVIDER": "groq",
}.items():
    os.environ.setdefault(key, value)

if not os.environ.get("DATABASE_URL") or not os.environ.get("SECRET_KEY"):
    raise RuntimeError("Configure DATABASE_URL and SECRET_KEY before deploying the API.")

from app.main import app
