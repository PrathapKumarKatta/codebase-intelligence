"""Run recorded migrations against the linked project's direct database URL."""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from alembic import command
from alembic.config import Config

root = Path(__file__).resolve().parents[1]
load_dotenv(root / ".env.local")
direct_url = os.environ.get("DATABASE_URL_UNPOOLED")
if not direct_url:
    raise RuntimeError("Pull the linked project's environment before running migrations.")
os.environ["DATABASE_URL"] = direct_url
sys.path.insert(0, str(root / "backend"))
os.chdir(root / "backend")
command.upgrade(Config("alembic.ini"), "head")
