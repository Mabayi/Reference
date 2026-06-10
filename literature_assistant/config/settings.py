import os
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 文件
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


class Settings:
    """应用配置，从环境变量读取"""

    DEEPSEEK_API_KEY: str = os.getenv("DEEPSEEK_API_KEY", "").strip()
    DEEPSEEK_BASE_URL: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com").strip().rstrip("/")
    MODEL_NAME: str = os.getenv("MODEL_NAME", "deepseek-chat").strip()
    VISION_MODEL_NAME: str = os.getenv("VISION_MODEL_NAME", "").strip()
    REQUEST_TIMEOUT: float = float(os.getenv("REQUEST_TIMEOUT", "120"))
    SECRET_KEY: str = os.getenv("SECRET_KEY", "change-me-in-production-123456")
    UPLOAD_DIR: Path = BASE_DIR / os.getenv("UPLOAD_DIR", "uploads")
    EXPORT_DIR: Path = BASE_DIR / os.getenv("EXPORT_DIR", "exports")
    VECTOR_STORE_DIR: Path = BASE_DIR / os.getenv("VECTOR_STORE_DIR", "vector_store")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///instance/literature.db")

    def __init__(self) -> None:
        # 确保必要目录存在
        self.UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
        self.EXPORT_DIR.mkdir(parents=True, exist_ok=True)
        self.VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)
        (BASE_DIR / "instance").mkdir(parents=True, exist_ok=True)


settings = Settings()
