"""FAISS 索引持久化读写（当前使用 JSON 文件 Mock）"""
import json
from pathlib import Path
from config.settings import settings


def index_exists(user_id: int) -> bool:
    """检查用户索引是否存在"""
    meta_path = Path(settings.VECTOR_STORE_DIR) / f"{user_id}_meta.json"
    return meta_path.exists()


def delete_index(user_id: int):
    """删除用户索引"""
    meta_path = Path(settings.VECTOR_STORE_DIR) / f"{user_id}_meta.json"
    if meta_path.exists():
        meta_path.unlink()
