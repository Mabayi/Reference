import uuid
from pathlib import Path

from fastapi import APIRouter, Request, UploadFile, File

from config.settings import settings
from services.chart_analyzer import analyze_chart as analyze_chart_service
from services.llm_service import LLMServiceError
from utils.auth_utils import require_login

router = APIRouter(prefix="/api/chart", tags=["图表解析"])

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


@router.post("/analyze")
async def analyze_chart(request: Request, file: UploadFile = File(...)):
    """上传图片并解析"""
    require_login(request)

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return {"code": 1, "data": None, "message": "仅支持 jpg/jpeg/png/gif/webp 格式"}

    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        return {"code": 1, "data": None, "message": "文件大小不能超过10MB"}

    # 保存图片
    charts_dir = settings.UPLOAD_DIR / "charts"
    charts_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4().hex}{ext}"
    save_path = charts_dir / stored_name
    save_path.write_bytes(content)

    try:
        result = await analyze_chart_service(str(save_path))
    except LLMServiceError as exc:
        return {"code": 1, "data": None, "message": str(exc)}

    result["image_url"] = f"/uploads/charts/{stored_name}"
    return {"code": 0, "data": result, "message": "ok"}
