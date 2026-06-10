from fastapi import APIRouter, Request
from pydantic import BaseModel

from repositories import experiment_repo, paper_repo
from services.experiment_designer import design_experiment as design_experiment_service
from services.experiment_designer import recommend_goal as recommend_goal_service
from services.experiment_designer import recommend_hypothesis as recommend_hypothesis_service
from services.llm_service import LLMServiceError
from utils.auth_utils import require_login

router = APIRouter(prefix="/api/experiment", tags=["实验设计"])


class DesignRequest(BaseModel):
    goal: str
    hypothesis: str = ""
    paper_id: int | None = None


class RecommendInputRequest(BaseModel):
    field: str
    paper_id: int | None = None
    goal: str = ""


def _build_paper_context(user_id: int, paper_id: int | None) -> str:
    if paper_id is None:
        return ""

    paper = paper_repo.get_paper_by_id(paper_id, user_id)
    if not paper:
        raise ValueError("参考文献不存在")
    if paper.get("parse_status") != "done":
        raise ValueError("参考文献尚未解析完成")

    title = paper.get("title") or paper.get("filename") or f"文献{paper_id}"
    authors = paper.get("authors") or "未知作者"
    year = paper.get("year") or "未知年份"
    keywords = paper.get("keywords") or ""
    abstract = paper.get("abstract") or ""
    methods = paper.get("methods") or ""
    conclusions = paper.get("conclusions") or ""
    innovations = paper.get("innovations") or ""
    return "\n".join(
        [
            f"[参考文献] 标题：{title}",
            f"作者：{authors}",
            f"年份：{year}",
            f"关键词：{keywords}",
            f"摘要：{abstract}",
            f"方法：{methods}",
            f"结论：{conclusions}",
            f"创新点：{innovations}",
        ]
    ).strip()


@router.post("/design")
async def design_experiment(request: Request, body: DesignRequest):
    """生成实验草案。"""
    user = require_login(request)
    try:
        paper_context = _build_paper_context(user["id"], body.paper_id)
    except ValueError as exc:
        return {"code": 1, "data": None, "message": str(exc)}

    try:
        result = await design_experiment_service(body.goal, body.hypothesis, paper_context)
    except LLMServiceError as exc:
        return {"code": 1, "data": None, "message": str(exc)}
    experiment_id = experiment_repo.create_experiment(user["id"], body.goal, body.hypothesis, result)
    result["id"] = experiment_id
    return {"code": 0, "data": result, "message": "ok"}


@router.post("/recommend-input")
async def recommend_experiment_input(request: Request, body: RecommendInputRequest):
    user = require_login(request)
    if body.paper_id is None:
        return {"code": 1, "data": None, "message": "请先选择一篇参考文献"}

    try:
        paper_context = _build_paper_context(user["id"], body.paper_id)
    except ValueError as exc:
        return {"code": 1, "data": None, "message": str(exc)}

    try:
        if body.field == "goal":
            text = await recommend_goal_service(paper_context)
        elif body.field == "hypothesis":
            text = await recommend_hypothesis_service(paper_context, body.goal)
        else:
            return {"code": 1, "data": None, "message": "不支持的生成类型"}
    except LLMServiceError as exc:
        return {"code": 1, "data": None, "message": str(exc)}

    if not text:
        return {"code": 1, "data": None, "message": "模型未返回可用内容"}

    return {"code": 0, "data": {"field": body.field, "text": text}, "message": "ok"}


@router.get("/list")
async def list_experiments(request: Request):
    user = require_login(request)
    experiments = experiment_repo.list_experiments(user["id"])
    data = [
        {
            "id": item["id"],
            "goal": item["goal"],
            "hypothesis": item["hypothesis"],
            "created_at": item["created_at"],
            "content": item.get("content", {}),
        }
        for item in experiments
    ]
    return {"code": 0, "data": data, "message": "ok"}
