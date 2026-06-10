"""文献阅读路由。"""
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import Response
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from config.settings import settings
from repositories import annotation_repo, paper_repo, token_repo
from services.llm_service import LLMServiceError
from services.translation_service import translate_text as translate_text_service
from services.writing_assistant import generate_discussion as generate_discussion_service
from utils.auth_utils import require_login

router = APIRouter(tags=["文献阅读"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


class AnnotationCreate(BaseModel):
    paper_id: int
    type: str = "highlight"
    text: str
    note: str = ""
    color: str = "#ffeb3b"
    page_index: int = 0
    char_start: int = 0
    char_end: int = 0
    selector_json: str = ""


class TranslateRequest(BaseModel):
    paper_id: int
    text: str
    target_lang: str = "zh"


class SummaryRequest(BaseModel):
    paper_id: int


@router.get("/reader/{paper_id}")
async def reader_page(request: Request, paper_id: int):
    user = require_login(request)
    paper = paper_repo.get_paper_by_id(paper_id, user["id"])
    if not paper:
        from fastapi.responses import RedirectResponse

        return RedirectResponse(url="/papers", status_code=302)

    return templates.TemplateResponse(
        request=request,
        name="reader.html",
        context={"user": user, "paper": paper, "active_page": "papers"},
    )


@router.get("/api/reader/{paper_id}/file")
async def get_reader_file(request: Request, paper_id: int):
    user = require_login(request)
    paper = paper_repo.get_paper_by_id(paper_id, user["id"])
    if not paper:
        return Response(content=b"document not found", status_code=404, media_type="text/plain")

    file_path = settings.UPLOAD_DIR / paper["stored_name"]
    if not file_path.exists():
        return Response(content=b"file not found", status_code=404, media_type="text/plain")

    return Response(content=file_path.read_bytes(), media_type="application/pdf")


@router.get("/api/reader/{paper_id}/content")
async def get_paper_content(request: Request, paper_id: int):
    user = require_login(request)
    paper = paper_repo.get_paper_by_id(paper_id, user["id"])
    if not paper:
        return {"code": 1, "data": None, "message": "文献不存在"}

    file_path = settings.UPLOAD_DIR / paper["stored_name"]
    if not file_path.exists():
        return {"code": 1, "data": None, "message": "原始文件不存在"}

    import base64
    import fitz

    document = fitz.open(str(file_path))
    total_pages = document.page_count
    pages = [{"index": index} for index in range(total_pages)]
    document.close()

    return {"code": 0, "data": {"pages": pages, "total_pages": total_pages}, "message": "ok"}


@router.get("/api/reader/{paper_id}/page/{page_index}")
async def get_reader_page(request: Request, paper_id: int, page_index: int):
    user = require_login(request)
    paper = paper_repo.get_paper_by_id(paper_id, user["id"])
    if not paper:
        return {"code": 1, "data": None, "message": "文献不存在"}

    file_path = settings.UPLOAD_DIR / paper["stored_name"]
    if not file_path.exists():
        return {"code": 1, "data": None, "message": "原始文件不存在"}

    import fitz

    document = fitz.open(str(file_path))
    if page_index < 0 or page_index >= document.page_count:
        document.close()
        return {"code": 1, "data": None, "message": "页码超出范围"}

    page = document[page_index]
    text = page.get_text()
    document.close()

    return {
        "code": 0,
        "data": {"index": page_index, "text": text},
        "message": "ok",
    }


@router.get("/api/reader/{paper_id}/page/{page_index}/image")
async def get_reader_page_image(request: Request, paper_id: int, page_index: int):
    user = require_login(request)
    paper = paper_repo.get_paper_by_id(paper_id, user["id"])
    if not paper:
        return Response(content=b"document not found", status_code=404, media_type="text/plain")

    file_path = settings.UPLOAD_DIR / paper["stored_name"]
    if not file_path.exists():
        return Response(content=b"file not found", status_code=404, media_type="text/plain")

    import fitz

    document = fitz.open(str(file_path))
    if page_index < 0 or page_index >= document.page_count:
        document.close()
        return Response(content=b"page out of range", status_code=404, media_type="text/plain")

    page = document[page_index]
    pixmap = page.get_pixmap(dpi=110)
    image_bytes = pixmap.tobytes("png")
    document.close()
    return Response(content=image_bytes, media_type="image/png")


@router.get("/api/reader/{paper_id}/annotations")
async def get_annotations(request: Request, paper_id: int):
    user = require_login(request)
    annotations = annotation_repo.get_annotations(user["id"], paper_id)
    return {"code": 0, "data": annotations, "message": "ok"}


@router.post("/api/reader/annotation")
async def add_annotation(request: Request, body: AnnotationCreate):
    user = require_login(request)
    annotation_id = annotation_repo.add_annotation(
        user["id"],
        body.paper_id,
        body.type,
        body.text,
        body.note,
        body.color,
        body.page_index,
        body.char_start,
        body.char_end,
        body.selector_json,
    )
    return {"code": 0, "data": {"id": annotation_id}, "message": "ok"}


@router.delete("/api/reader/annotation/{ann_id}")
async def delete_annotation(request: Request, ann_id: int):
    user = require_login(request)
    deleted = annotation_repo.delete_annotation(ann_id, user["id"])
    return {"code": 0 if deleted else 1, "data": None, "message": "ok" if deleted else "删除失败"}


@router.post("/api/reader/translate")
async def translate_text(request: Request, body: TranslateRequest):
    user = require_login(request)
    paper = paper_repo.get_paper_by_id(body.paper_id, user["id"])
    if not paper:
        return {"code": 1, "data": None, "message": "文献不存在"}

    free_used = annotation_repo.get_free_papers_used(user["id"])
    needs_tokens = free_used >= 1

    if needs_tokens and token_repo.is_token_disabled(user["id"]):
        return {"code": 2, "data": None, "message": "当前账户 API 使用已被管理员停用，请联系客服"}

    try:
        translated = await translate_text_service(body.text, body.target_lang)
    except LLMServiceError as exc:
        return {"code": 1, "data": None, "message": str(exc)}

    if free_used >= 1:
        token_repo.record_api_usage(user["id"], 0, f"翻译请求：{len(body.text)} 字符")
    else:
        annotation_repo.use_free_translate(user["id"])

    return {
        "code": 0,
        "data": {"translated": translated, "target_lang": body.target_lang},
        "message": "ok",
    }


@router.post("/api/reader/summary")
async def summarize_paper(request: Request, body: SummaryRequest):
    user = require_login(request)
    paper = paper_repo.get_paper_by_id(body.paper_id, user["id"])
    if not paper:
        return {"code": 1, "data": None, "message": "文献不存在"}

    summary_source = "\n".join(
        [
            f"标题：{paper.get('title') or paper.get('filename')}",
            f"作者：{paper.get('authors') or '未知'}",
            f"摘要：{paper.get('abstract') or '未提取'}",
            f"方法：{paper.get('methods') or '未提取'}",
            f"结论：{paper.get('conclusions') or '未提取'}",
        ]
    )

    try:
        summary = await generate_discussion_service(
            results=(
                "请对下面这篇论文做结构化总结，包含：研究目标、核心方法、主要结果、局限性、"
                "以及值得关注的启发。不要编造未提供的实验细节。\n\n"
                f"{summary_source}"
            ),
            references="未提供额外参考文献",
        )
    except LLMServiceError as exc:
        return {"code": 1, "data": None, "message": str(exc)}

    return {"code": 0, "data": {"summary": summary}, "message": "ok"}
