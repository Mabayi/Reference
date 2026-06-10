from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from repositories import paper_repo
from services.citation_formatter import format_all, format_bibliography
from utils.auth_utils import require_login

router = APIRouter(prefix="/api/citation", tags=["引用管理"])


class FormatRequest(BaseModel):
    paper_ids: list[int]
    style: str = "gbt"


@router.get("/papers")
async def get_citation_papers(request: Request):
    user = require_login(request)
    papers = paper_repo.get_papers_by_user(user["id"])
    result = [paper for paper in papers if paper["parse_status"] == "done"]
    return {"code": 0, "data": result, "message": "ok"}


@router.post("/format")
async def format_citation(request: Request, body: FormatRequest):
    user = require_login(request)
    papers = []
    for paper_id in body.paper_ids:
        paper = paper_repo.get_paper_by_id(paper_id, user["id"])
        if paper:
            papers.append(paper)

    if not papers:
        return {"code": 1, "data": None, "message": "未找到可格式化的文献"}

    results = [{"paper_id": paper["id"], "title": paper["title"], "formats": format_all(paper)} for paper in papers]
    bibliography = format_bibliography(papers, body.style)
    return {"code": 0, "data": {"items": results, "bibliography": bibliography}, "message": "ok"}


@router.post("/export")
async def export_citation(request: Request, body: FormatRequest):
    user = require_login(request)
    papers = []
    for paper_id in body.paper_ids:
        paper = paper_repo.get_paper_by_id(paper_id, user["id"])
        if paper:
            papers.append(paper)

    bibliography = format_bibliography(papers, body.style)
    return PlainTextResponse(
        content=bibliography,
        headers={"Content-Disposition": f"attachment; filename=references_{body.style}.txt"},
    )
