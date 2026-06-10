from fastapi import APIRouter, Request
from pydantic import BaseModel

from repositories import support_repo
from services.support_assistant import generate_support_reply
from services.support_classifier import classify_ticket
from utils.auth_utils import require_login

router = APIRouter(prefix="/api/support", tags=["客服工单"])

FAQ_ITEMS = [
    {
        "key": "upload_parse",
        "title": "文献上传或解析失败",
        "answer": "请确认文件为 PDF，文件名不要包含过长特殊字符。上传后如长时间停留在解析中，可刷新文献库查看状态；仍失败时请重新上传或提交工单。",
    },
    {
        "key": "pdf_display",
        "title": "PDF、翻译或总结显示不清楚",
        "answer": "请先切换浅色/深色模式并刷新页面，再尝试调整阅读页缩放比例。如果仍看不清，请说明所在页面、浏览器缩放比例和具体区域。",
    },
    {
        "key": "ai_quality",
        "title": "AI 生成内容不准确或太长",
        "answer": "请缩小研究主题范围，并优先选择相关参考文献。生成内容过长时可使用页面内展开/收起和复制功能；如内容明显跑题，请提交问题并附上主题。",
    },
    {
        "key": "token_billing",
        "title": "DeepSeek API Key、余额或扣费问题",
        "answer": "请先进入 Token 管理页绑定真实 DeepSeek API Key，并通过 DeepSeek 官方平台充值。系统只同步官方余额和记录本系统 API 用量；若 API 使用被管理员停用，需要联系管理员恢复。",
    },
    {
        "key": "account_login",
        "title": "账号登录、注册或权限问题",
        "answer": "请确认邮箱和密码输入正确，密码至少 6 位。管理员后台只对 admin 用户显示，普通用户无法访问管理页面和管理员接口。",
    },
    {
        "key": "feature_request",
        "title": "功能建议或页面优化",
        "answer": "请描述你希望优化的页面、当前痛点和期望结果。建议越具体，管理员越容易判断优先级并安排处理。",
    },
]


class TicketCreateRequest(BaseModel):
    subject: str
    message: str
    faq_key: str = ""


class SupportAIRequest(BaseModel):
    subject: str
    message: str
    faq_key: str = ""


class TicketFeedbackRequest(BaseModel):
    helpful: bool
    note: str = ""


def _get_faq_item(faq_key: str) -> dict:
    return next((item for item in FAQ_ITEMS if item["key"] == faq_key), {})


@router.get("/faqs")
async def list_faqs(request: Request):
    require_login(request)
    return {"code": 0, "data": FAQ_ITEMS, "message": "ok"}


@router.post("/tickets")
async def create_ticket(request: Request, body: TicketCreateRequest):
    user = require_login(request)
    subject = body.subject.strip()
    message = body.message.strip()
    if not subject:
        return {"code": 1, "data": None, "message": "请填写问题标题"}
    if len(message) < 8:
        return {"code": 1, "data": None, "message": "请补充更具体的问题描述"}

    classification = await classify_ticket(subject, message, body.faq_key)
    ticket = support_repo.create_ticket(
        user_id=user["id"],
        subject=subject,
        message=message,
        faq_key=body.faq_key.strip(),
        category=classification["category"],
        sentiment=classification["sentiment"],
        sentiment_score=classification["sentiment_score"],
        priority=classification["priority"],
        ai_summary=classification["summary"],
        faq_answer=_get_faq_item(body.faq_key.strip()).get("answer", ""),
        source="manual",
    )
    return {"code": 0, "data": ticket, "message": "工单已提交"}


@router.post("/ai")
async def ask_support_ai(request: Request, body: SupportAIRequest):
    user = require_login(request)
    subject = body.subject.strip()
    message = body.message.strip()
    faq_key = body.faq_key.strip()
    if not subject:
        return {"code": 1, "data": None, "message": "请填写问题标题"}
    if len(message) < 8:
        return {"code": 1, "data": None, "message": "请补充更具体的问题描述"}

    faq_item = _get_faq_item(faq_key)
    faq_answer = faq_item.get("answer", "")
    classification = await classify_ticket(subject, message, faq_key)
    ai_reply = await generate_support_reply(
        subject=subject,
        message=message,
        faq_title=faq_item.get("title", ""),
        faq_answer=faq_answer,
    )
    ticket = support_repo.create_ticket(
        user_id=user["id"],
        subject=subject,
        message=message,
        faq_key=faq_key,
        category=classification["category"],
        sentiment=classification["sentiment"],
        sentiment_score=classification["sentiment_score"],
        priority=classification["priority"],
        ai_summary=classification["summary"],
        faq_answer=faq_answer,
        ai_reply=ai_reply,
        source="ai",
    )
    return {
        "code": 0,
        "data": {
            "ticket": ticket,
            "faq_answer": faq_answer,
            "ai_reply": ai_reply,
        },
        "message": "AI 已回复并创建工单",
    }


@router.get("/tickets")
async def list_my_tickets(request: Request):
    user = require_login(request)
    tickets = support_repo.list_user_tickets(user["id"])
    return {"code": 0, "data": tickets, "message": "ok"}


@router.post("/tickets/{ticket_id}/feedback")
async def update_feedback(request: Request, ticket_id: int, body: TicketFeedbackRequest):
    user = require_login(request)
    note = body.note.strip()[:300]
    ticket = support_repo.update_ticket_feedback(ticket_id, user["id"], body.helpful, note)
    if not ticket:
        return {"code": 1, "data": None, "message": "工单不存在"}
    return {"code": 0, "data": ticket, "message": "反馈已记录"}
