from pydantic_settings import BaseSettings
from pathlib import Path
from dotenv import load_dotenv
import os

# Resolve paths relative to this file
CONFIG_DIR = Path(__file__).resolve().parent
BASE_DIR = CONFIG_DIR.parent

# Load .env file explicitly from the project root
load_dotenv(BASE_DIR / ".env")

class Settings(BaseSettings):
    project_name: str = "Job Application Agent"
    version: str = "0.1.0"

    chroma_persist_directory: Path = BASE_DIR / "knowledge_base" / "chroma_db"

    embedding_model: str = "text-embedding-3-small"
    embedding_dimensions: int = 1536

    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")

    # Email Notification Settings
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    sender_email: str = ""
    sender_password: str = ""

    data_directory: Path = BASE_DIR / "data"
    resumes_directory: Path = data_directory / "resumes"
    jobs_directory: Path = data_directory / "jobs"

    chunk_size: int = 512
    chunk_overlap: int = 50

    max_tokens_per_request: int = 4000

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings()
