from fastapi import APIRouter, Request
from pydantic import BaseModel

from services.llm_service import LLMServiceError
from services.writing_assistant import (
    generate_discussion as generate_discussion_service,
    generate_method as generate_method_service,
    polish_text as polish_text_service,
)
from utils.auth_utils import require_login

router = APIRouter(prefix="/api/writing", tags=["写作辅助"])


class MethodRequest(BaseModel):
    content: str
    stats_method: str = ""


class DiscussionRequest(BaseModel):
    results: str
    references: str = ""


class PolishRequest(BaseModel):
    text: str
    language: str = "中文"


@router.post("/method")
async def generate_method(request: Request, body: MethodRequest):
    require_login(request)
    try:
        result = await generate_method_service(body.content, body.stats_method)
    except LLMServiceError as exc:
        return {"code": 1, "data": None, "message": str(exc)}
    return {"code": 0, "data": {"content": result}, "message": "ok"}


@router.post("/discussion")
async def generate_discussion(request: Request, body: DiscussionRequest):
    require_login(request)
    try:
        result = await generate_discussion_service(body.results, body.references)
    except LLMServiceError as exc:
        return {"code": 1, "data": None, "message": str(exc)}
    return {"code": 0, "data": {"content": result}, "message": "ok"}


@router.post("/polish")
async def polish_text(request: Request, body: PolishRequest):
    require_login(request)
    try:
        result = await polish_text_service(body.text, body.language)
    except LLMServiceError as exc:
        return {"code": 1, "data": None, "message": str(exc)}
    return {"code": 0, "data": {"content": result}, "message": "ok"}
