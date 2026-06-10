import os
import uuid
from pathlib import Path


def generate_filename(original_name: str) -> str:
    """生成 UUID 文件名，保留原始扩展名"""
    ext = Path(original_name).suffix
    return f"{uuid.uuid4().hex}{ext}"


def ensure_dir(path: Path) -> Path:
    """确保目录存在"""
    path.mkdir(parents=True, exist_ok=True)
    return path
