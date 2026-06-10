from fastapi import APIRouter, Request
from pydantic import BaseModel

from services.code_generator import generate_code as generate_code_service
from services.llm_service import LLMServiceError
from utils.auth_utils import require_login

router = APIRouter(prefix="/api/codegen", tags=["代码生成"])


class CodegenRequest(BaseModel):
    experiment_summary: str = ""
    language: str = "python"
    stats_method: str = ""


@router.post("/generate")
async def generate_code(request: Request, body: CodegenRequest):
    """生成分析脚本草稿。"""
    require_login(request)
    try:
        code = await generate_code_service(body.experiment_summary, body.language, body.stats_method)
    except LLMServiceError as exc:
        return {"code": 1, "data": None, "message": str(exc)}
    return {"code": 0, "data": {"code": code, "language": body.language}, "message": "ok"}
