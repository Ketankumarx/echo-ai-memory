import os
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv
from pydantic import BaseModel

# Project directory structure
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
PROJECT_ROOT = BACKEND_DIR.parent

# Load environment variables from backend/.env or root .env with override=True
load_dotenv(BACKEND_DIR / ".env", override=True)
load_dotenv(PROJECT_ROOT / ".env", override=True)

def _get_clean_env(name: str) -> Optional[str]:
    val = os.getenv(name)
    if val:
        val = val.strip().strip("'\"").strip()
        return val if val else None
    return None

# Resolve DB and upload paths
env_db_path = os.getenv("DATABASE_PATH", "echo_memory.db")
if not os.path.isabs(env_db_path):
    resolved_db_path = str(PROJECT_ROOT / env_db_path)
else:
    resolved_db_path = env_db_path

env_upload_dir = os.getenv("AUDIO_UPLOAD_DIR", "uploads/audio")
if not os.path.isabs(env_upload_dir):
    resolved_upload_dir = str(PROJECT_ROOT / env_upload_dir)
else:
    resolved_upload_dir = env_upload_dir

# Ensure audio upload dir exists
os.makedirs(resolved_upload_dir, exist_ok=True)

class Settings(BaseModel):
    PROJECT_NAME: str = "ECHO AI Personal Memory Assistant"
    API_V1_PREFIX: str = "/api"
    
    # Environment API Keys (cleaned of accidental whitespace/quotes)
    OPENAI_API_KEY: Optional[str] = _get_clean_env("OPENAI_API_KEY")
    GEMINI_API_KEY: Optional[str] = _get_clean_env("GEMINI_API_KEY")
    GROQ_API_KEY: Optional[str] = _get_clean_env("GROQ_API_KEY")
    SERPAPI_API_KEY: Optional[str] = _get_clean_env("SERPAPI_API_KEY")
    
    # Storage & DB
    DATABASE_PATH: str = resolved_db_path
    AUDIO_UPLOAD_DIR: str = resolved_upload_dir
    
    # Model preferences
    PRIMARY_LLM_PROVIDER: str = os.getenv("PRIMARY_LLM_PROVIDER", "auto")
    DEFAULT_SIMILARITY_THRESHOLD: float = 0.40
    TOP_K_MEMORIES: int = 5
    
    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "*"
    ]

settings = Settings()
