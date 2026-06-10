from fastapi import APIRouter, Request
from pydantic import BaseModel

from services import rag_service
from utils.auth_utils import require_login

router = APIRouter(prefix="/api/rag", tags=["RAG检索"])


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5


@router.post("/search")
async def rag_search(request: Request, body: SearchRequest):
    """RAG检索调试接口"""
    user = require_login(request)
    results = rag_service.search(user["id"], body.query, body.top_k)
    return {"code": 0, "data": results, "message": "ok"}
