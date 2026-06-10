"""
RAG 向量检索服务
当前使用简单文本匹配实现 Mock RAG，接口与 FAISS 版本一致。
当 sentence-transformers + faiss-cpu 可用时可无缝替换。
"""
import json
import re
from pathlib import Path
from config.settings import settings
from repositories import paper_repo
from services import pdf_parser


def _chunk_text(text: str, chunk_size: int = 512, overlap: int = 64) -> list[str]:
    """将文本按固定大小分块"""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks


def _load_meta(user_id: int) -> list[dict]:
    """加载用户的分块元数据"""
    meta_path = Path(settings.VECTOR_STORE_DIR) / f"{user_id}_meta.json"
    if meta_path.exists():
        return json.loads(meta_path.read_text(encoding="utf-8"))
    return []


def _save_meta(user_id: int, meta: list[dict]):
    """保存分块元数据"""
    meta_path = Path(settings.VECTOR_STORE_DIR) / f"{user_id}_meta.json"
    meta_path.write_text(json.dumps(meta, ensure_ascii=False), encoding="utf-8")


def build_index(user_id: int) -> None:
    """为用户所有已解析文献构建索引（全量重建）"""
    papers = paper_repo.get_papers_by_user(user_id)
    meta = []
    for p in papers:
        if p["parse_status"] != "done":
            continue
        file_path = settings.UPLOAD_DIR / p["stored_name"]
        if not file_path.exists():
            continue
        text = pdf_parser.extract_text(str(file_path))
        chunks = _chunk_text(text)
        for i, chunk in enumerate(chunks):
            meta.append({"paper_id": p["id"], "chunk_index": i, "text": chunk})
    _save_meta(user_id, meta)


def add_paper_to_index(user_id: int, paper_id: int, text: str) -> None:
    """将单篇文献追加到索引"""
    meta = _load_meta(user_id)
    meta = [item for item in meta if item.get("paper_id") != paper_id]
    chunks = _chunk_text(text)
    for i, chunk in enumerate(chunks):
        meta.append({"paper_id": paper_id, "chunk_index": i, "text": chunk})
    _save_meta(user_id, meta)


def remove_paper_from_index(user_id: int, paper_id: int) -> None:
    meta = _load_meta(user_id)
    meta = [item for item in meta if item.get("paper_id") != paper_id]
    _save_meta(user_id, meta)


def _tokenize_query(query: str) -> list[str]:
    english_terms = re.findall(r"[a-zA-Z0-9_+-]+", query.lower())
    chinese_terms = re.findall(r"[\u4e00-\u9fff]{1,6}", query)
    tokens = set(term for term in english_terms + chinese_terms if term.strip())
    return sorted(tokens)


def search(user_id: int, query: str, top_k: int = 5) -> list[dict]:
    """简单关键词匹配检索（Mock RAG）"""
    meta = _load_meta(user_id)
    if not meta:
        return []

    query_terms = _tokenize_query(query)
    if not query_terms:
        return []

    scored = []
    for item in meta:
        text_lower = item["text"].lower()
        score = sum(text_lower.count(term.lower()) for term in query_terms if term.lower() in text_lower)
        if score > 0:
            scored.append({**item, "score": score})

    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:top_k]


def get_context_for_query(user_id: int, query: str, top_k: int = 5) -> str:
    """检索并拼接 context 字符串，供综述生成使用"""
    results = search(user_id, query, top_k)
    if not results:
        return ""
    parts = []
    for r in results:
        parts.append(f"[文献{r['paper_id']}] {r['text']}")
    return "\n\n".join(parts)
