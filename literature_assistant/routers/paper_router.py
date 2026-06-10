import hashlib
import uuid
from pathlib import PurePath

from fastapi import APIRouter, BackgroundTasks, File, Form, Request, UploadFile
from pydantic import BaseModel

from config.settings import settings
from repositories import paper_repo
from services import pdf_parser, rag_service
from utils.auth_utils import require_login

router = APIRouter(prefix="/api/papers", tags=["文献管理"])


class FolderCreateRequest(BaseModel):
    name: str
    parent_id: int | None = None


class UpdatePaperRequest(BaseModel):
    filename: str | None = None
    paper_tier: str | None = None
    folder_id: int | None = None


def _compute_md5(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


def _clean_name(value: str) -> str:
    cleaned = value.strip().replace("\\", "/")
    cleaned = cleaned.split("/")[-1].strip()
    if not cleaned:
        raise ValueError("名称不能为空")
    if cleaned in {".", ".."}:
        raise ValueError("名称不合法")
    return cleaned[:180]


def _parse_folder_id(folder_id: str | int | None) -> int | None:
    if folder_id in (None, "", "null", "undefined"):
        return None
    return int(folder_id)


def _ensure_relative_folders(user_id: int, relative_path: str) -> int | None:
    parts = [part for part in PurePath(relative_path.replace("\\", "/")).parts if part not in {".", ""}]
    if len(parts) <= 1:
        return None

    parent_id = None
    for folder_name in parts[:-1]:
        parent_id = paper_repo.get_or_create_folder(user_id, _clean_name(folder_name), parent_id)
    return parent_id


def _parse_paper_task(user_id: int, paper_id: int, file_path: str):
    paper_repo.update_paper_metadata(paper_id, parse_status="processing")
    try:
        metadata = pdf_parser.extract_metadata(file_path)
        paper_repo.update_paper_metadata(
            paper_id,
            parse_status="done",
            title=metadata["title"],
            authors=metadata["authors"],
            abstract=metadata["abstract"],
            keywords=metadata["keywords"],
            year=metadata["year"],
            methods=metadata["methods"],
            conclusions=metadata["conclusions"],
            innovations=metadata["innovations"],
        )
        text = pdf_parser.extract_text(file_path)
        if text.strip():
            rag_service.add_paper_to_index(user_id, paper_id, text)
    except Exception:
        paper_repo.update_paper_metadata(paper_id, parse_status="failed")


async def _save_pdf_upload(
    *,
    user_id: int,
    file: UploadFile,
    background_tasks: BackgroundTasks,
    folder_id: int | None,
) -> tuple[int | None, str | None]:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        return None, "当前只支持上传 PDF 文件"

    content = await file.read()
    if len(content) > 50 * 1024 * 1024:
        return None, f"{file.filename} 超过 50MB"

    file_md5 = _compute_md5(content)
    if paper_repo.check_md5_exists(user_id, file_md5):
        return None, f"{file.filename} 已存在"

    stored_name = f"{uuid.uuid4().hex}.pdf"
    save_path = settings.UPLOAD_DIR / stored_name
    save_path.write_bytes(content)

    paper_id = paper_repo.create_paper(user_id, file.filename, stored_name, file_md5, folder_id)
    background_tasks.add_task(_parse_paper_task, user_id, paper_id, str(save_path))
    return paper_id, None


def _serialize_paper(paper: dict) -> dict:
    return {
        "id": paper["id"],
        "filename": paper["filename"],
        "title": paper["title"],
        "authors": paper["authors"],
        "year": paper["year"],
        "keywords": paper["keywords"],
        "parse_status": paper["parse_status"],
        "folder_id": paper.get("folder_id"),
        "folder_name": paper.get("folder_name"),
        "paper_tier": paper.get("paper_tier") or "A",
        "created_at": paper["created_at"],
    }


@router.get("/folders")
async def list_folders(request: Request):
    user = require_login(request)
    return {"code": 0, "data": paper_repo.get_folders_by_user(user["id"]), "message": "ok"}


@router.post("/folders")
async def create_folder(request: Request, body: FolderCreateRequest):
    user = require_login(request)
    try:
        folder = paper_repo.create_folder(user["id"], _clean_name(body.name), body.parent_id)
    except ValueError as exc:
        return {"code": 1, "data": None, "message": str(exc)}
    return {"code": 0, "data": folder, "message": "文件夹已创建"}


@router.post("/upload")
async def upload_paper(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    folder_id: str | None = Form(default=None),
):
    user = require_login(request)
    parsed_folder_id = _parse_folder_id(folder_id)
    if parsed_folder_id is not None and not paper_repo.get_folder_by_id(parsed_folder_id, user["id"]):
        return {"code": 1, "data": None, "message": "目标文件夹不存在"}

    paper_id, error = await _save_pdf_upload(
        user_id=user["id"],
        file=file,
        background_tasks=background_tasks,
        folder_id=parsed_folder_id,
    )
    if error:
        return {"code": 1, "data": None, "message": error}

    return {"code": 0, "data": {"paper_id": paper_id}, "message": "上传成功，后台正在解析"}


@router.post("/upload-folder")
async def upload_folder(
    request: Request,
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    paths: list[str] | None = Form(default=None),
):
    user = require_login(request)
    uploaded: list[int] = []
    skipped: list[str] = []

    for index, file in enumerate(files):
        relative_path = paths[index] if paths and index < len(paths) else (file.filename or "")
        folder_id = _ensure_relative_folders(user["id"], relative_path)
        paper_id, error = await _save_pdf_upload(
            user_id=user["id"],
            file=file,
            background_tasks=background_tasks,
            folder_id=folder_id,
        )
        if paper_id:
            uploaded.append(paper_id)
        elif error:
            skipped.append(error)

    return {
        "code": 0,
        "data": {"uploaded": len(uploaded), "skipped": skipped[:20]},
        "message": f"已上传 {len(uploaded)} 篇文献，跳过 {len(skipped)} 个文件",
    }


@router.get("")
async def list_papers(
    request: Request,
    q: str = "",
    scope: str = "all",
    folder_id: int | None = None,
):
    user = require_login(request)
    papers = paper_repo.get_papers_by_user(user["id"], scope=scope, folder_id=folder_id, query=q)
    return {"code": 0, "data": [_serialize_paper(paper) for paper in papers], "message": "ok"}


@router.get("/{paper_id}")
async def get_paper(request: Request, paper_id: int):
    user = require_login(request)
    paper = paper_repo.get_paper_by_id(paper_id, user["id"])
    if not paper:
        return {"code": 1, "data": None, "message": "文献不存在"}
    return {"code": 0, "data": paper, "message": "ok"}


@router.patch("/{paper_id}")
async def update_paper(request: Request, paper_id: int, body: UpdatePaperRequest):
    user = require_login(request)
    filename = None
    if body.filename is not None:
        try:
            filename = _clean_name(body.filename)
        except ValueError as exc:
            return {"code": 1, "data": None, "message": str(exc)}
        if not filename.lower().endswith(".pdf"):
            filename = f"{filename}.pdf"

    paper_tier = None
    if body.paper_tier is not None:
        paper_tier = body.paper_tier.strip().upper()
        if paper_tier not in {"A", "B", "C"}:
            return {"code": 1, "data": None, "message": "分档只能选择 A、B 或 C"}

    update_folder = "folder_id" in body.model_fields_set
    if update_folder and body.folder_id is not None and not paper_repo.get_folder_by_id(body.folder_id, user["id"]):
        return {"code": 1, "data": None, "message": "目标文件夹不存在"}

    updated = paper_repo.update_paper_record(
        paper_id,
        user["id"],
        filename=filename,
        paper_tier=paper_tier,
        folder_id=body.folder_id,
        update_folder=update_folder,
    )
    return {"code": 0 if updated else 1, "data": None, "message": "更新成功" if updated else "文献不存在"}


@router.delete("/{paper_id}")
async def delete_paper(request: Request, paper_id: int):
    user = require_login(request)
    paper = paper_repo.get_paper_by_id(paper_id, user["id"])
    if not paper:
        return {"code": 1, "data": None, "message": "文献不存在"}

    file_path = settings.UPLOAD_DIR / paper["stored_name"]
    if file_path.exists():
        file_path.unlink()

    rag_service.remove_paper_from_index(user["id"], paper_id)
    paper_repo.delete_paper(paper_id, user["id"])
    return {"code": 0, "data": None, "message": "删除成功"}


@router.post("/{paper_id}/index")
async def index_paper(request: Request, paper_id: int):
    user = require_login(request)
    paper = paper_repo.get_paper_by_id(paper_id, user["id"])
    if not paper:
        return {"code": 1, "data": None, "message": "文献不存在"}
    if paper["parse_status"] != "done":
        return {"code": 1, "data": None, "message": "文献尚未解析完成"}

    file_path = settings.UPLOAD_DIR / paper["stored_name"]
    text = pdf_parser.extract_text(str(file_path))
    rag_service.add_paper_to_index(user["id"], paper_id, text)
    return {"code": 0, "data": None, "message": "索引构建成功"}
