import json

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from repositories import paper_repo, survey_repo, token_repo
from services import rag_service, survey_generator
from services.llm_service import LLMServiceError
from utils.auth_utils import require_login

router = APIRouter(prefix="/api/survey", tags=["综述生成"])


class GenerateRequest(BaseModel):
    topic: str
    paper_ids: list[int] = []


class RecommendTopicRequest(BaseModel):
    paper_ids: list[int] = []


def _build_context_from_selected_papers(user_id: int, paper_ids: list[int]) -> str:
    parts: list[str] = []
    for paper_id in paper_ids:
        paper = paper_repo.get_paper_by_id(paper_id, user_id)
        if not paper or paper.get("parse_status") != "done":
            continue

        title = paper.get("title") or paper.get("filename") or f"文献{paper_id}"
        authors = paper.get("authors") or "未知作者"
        year = paper.get("year") or "未知年份"
        abstract = paper.get("abstract") or ""
        methods = paper.get("methods") or ""
        conclusions = paper.get("conclusions") or ""
        keywords = paper.get("keywords") or ""
        parts.append(
            "\n".join(
                [
                    f"[文献{paper_id}] 标题：{title}",
                    f"作者：{authors}",
                    f"年份：{year}",
                    f"关键词：{keywords}",
                    f"摘要：{abstract}",
                    f"方法：{methods}",
                    f"结论：{conclusions}",
                ]
            ).strip()
        )

    return "\n\n".join(part for part in parts if part).strip()


@router.post("/generate")
async def generate_survey(request: Request, body: GenerateRequest):
    user = require_login(request)
    context = _build_context_from_selected_papers(user["id"], body.paper_ids)
    if not context:
        context = rag_service.get_context_for_query(user["id"], body.topic)
    account = token_repo.get_deepseek_api_key(user["id"], include_secret=True)
    api_key = str(account.get("api_key") or "").strip() if account else None

    async def event_stream():
        full_content = ""
        try:
            async for chunk in survey_generator.generate_survey_stream(
                body.topic,
                context,
                api_key=api_key,
                usage_user_id=user["id"],
            ):
                full_content += chunk
                yield f"data: {json.dumps({'chunk': chunk}, ensure_ascii=False)}\n\n"

            survey_id = survey_repo.create_survey(user["id"], body.topic, body.paper_ids, full_content)
            yield f"data: {json.dumps({'done': True, 'survey_id': survey_id}, ensure_ascii=False)}\n\n"
        except LLMServiceError as exc:
            yield f"data: {json.dumps({'error': str(exc)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.post("/recommend-topic")
async def recommend_topic(request: Request, body: RecommendTopicRequest):
    user = require_login(request)
    if not body.paper_ids:
        return {"code": 1, "data": None, "message": "请先选择参考文献"}

    context = _build_context_from_selected_papers(user["id"], body.paper_ids)
    if not context:
        return {"code": 1, "data": None, "message": "所选文献尚未解析完成，无法推荐主题"}

    try:
        topic = await survey_generator.recommend_survey_topic(context)
    except LLMServiceError as exc:
        return {"code": 1, "data": None, "message": str(exc)}

    if not topic:
        return {"code": 1, "data": None, "message": "模型未返回可用主题"}

    return {"code": 0, "data": {"topic": topic}, "message": "ok"}


@router.get("/list")
async def list_surveys(request: Request):
    user = require_login(request)
    surveys = survey_repo.get_surveys_by_user(user["id"])
    return {"code": 0, "data": surveys, "message": "ok"}


@router.get("/{survey_id}")
async def get_survey(request: Request, survey_id: int):
    user = require_login(request)
    survey = survey_repo.get_survey_by_id(survey_id, user["id"])
    if not survey:
        return {"code": 1, "data": None, "message": "综述记录不存在"}
    return {"code": 0, "data": survey, "message": "ok"}
