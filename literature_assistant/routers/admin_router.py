from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import APIRouter, Request
from pydantic import BaseModel

from repositories import support_repo, token_repo, user_repo
from utils.auth_utils import require_admin

router = APIRouter(prefix="/api/admin", tags=["管理员"])


class TicketReplyRequest(BaseModel):
    reply: str
    status: str = "resolved"


class TicketStatusRequest(BaseModel):
    status: str


class TokenDisableRequest(BaseModel):
    disabled: bool


def _date_key(value: str | None) -> str:
    if not value:
        return ""
    return str(value)[:10]


def _recent_day_items(days: int = 7) -> list[dict]:
    today = datetime.now().date()
    return [
        {"date": (today - timedelta(days=offset)).strftime("%Y-%m-%d"), "value": 0}
        for offset in range(days - 1, -1, -1)
    ]


@router.get("/overview")
async def overview(request: Request):
    require_admin(request)
    users = user_repo.list_users()
    ticket_stats = support_repo.get_ticket_stats()
    balances = token_repo.list_all_balances()
    disabled_count = sum(1 for item in balances if int(item.get("is_disabled") or 0))
    return {
        "code": 0,
        "data": {
            "total_users": len(users),
            "disabled_tokens": disabled_count,
            "tickets": ticket_stats,
            "feedback": support_repo.get_feedback_stats(),
        },
        "message": "ok",
    }


@router.get("/usage")
async def usage_stats(request: Request):
    require_admin(request)
    users = token_repo.list_all_balances()
    logs = token_repo.get_all_logs(limit=1000)
    tickets = support_repo.list_all_tickets(status="all", limit=1000)
    ticket_stats = support_repo.get_ticket_stats()
    feedback_stats = support_repo.get_feedback_stats()

    consumed_by_user: dict[int, int] = defaultdict(int)
    activity_by_user: dict[int, int] = defaultdict(int)
    token_action_counts: dict[str, int] = defaultdict(int)
    token_action_amounts: dict[str, int] = defaultdict(int)

    token_consumption_daily = _recent_day_items(days=7)
    new_users_daily = _recent_day_items(days=7)
    token_daily_lookup = {item["date"]: item for item in token_consumption_daily}
    user_daily_lookup = {item["date"]: item for item in new_users_daily}

    for user in users:
        created_date = _date_key(user.get("created_at"))
        if created_date in user_daily_lookup:
            user_daily_lookup[created_date]["value"] += 1

    for log in logs:
        user_id = int(log.get("user_id") or 0)
        action = str(log.get("action") or "unknown")
        amount = int(log.get("amount") or 0)
        activity_by_user[user_id] += 1
        token_action_counts[action] += 1
        token_action_amounts[action] += abs(amount)
        if action == "consume":
            consumed_by_user[user_id] += abs(amount)
            log_date = _date_key(log.get("created_at"))
            if log_date in token_daily_lookup:
                token_daily_lookup[log_date]["value"] += abs(amount)

    action_labels = {
        "gift": "旧版赠送",
        "consume": "API 用量",
        "purchase": "旧版购买",
        "redeem": "旧版兑换",
        "bind_api_key": "绑定密钥",
        "sync_balance": "同步余额",
        "remove_api_key": "移除密钥",
        "disable": "停用 API",
        "enable": "恢复 API",
        "admin": "管理员调整",
        "unknown": "其他",
    }
    token_actions = [
        {
            "action": action,
            "label": action_labels.get(action, action),
            "count": token_action_counts[action],
            "amount": token_action_amounts[action],
        }
        for action in sorted(token_action_counts, key=lambda key: token_action_counts[key], reverse=True)
    ]

    users_by_id = {int(user.get("user_id") or 0): user for user in users}
    top_users = []
    for user_id, user in users_by_id.items():
        top_users.append(
            {
                "user_id": user_id,
                "username": user.get("username") or "-",
                "email": user.get("email") or "-",
                "deepseek_is_bound": bool(user.get("deepseek_is_bound")),
                "deepseek_is_available": int(user.get("deepseek_is_available") or 0),
                "deepseek_balance_text": user.get("deepseek_balance_text") or "未同步",
                "consumed": consumed_by_user[user_id],
                "activity_count": activity_by_user[user_id],
                "is_disabled": int(user.get("is_disabled") or 0),
            }
        )
    top_users.sort(key=lambda item: (item["consumed"], item["activity_count"]), reverse=True)

    ticket_sentiments: dict[str, int] = defaultdict(int)
    ticket_categories: dict[str, int] = defaultdict(int)
    for ticket in tickets:
        ticket_sentiments[str(ticket.get("sentiment") or "中性")] += 1
        ticket_categories[str(ticket.get("category") or "其他")] += 1

    ticket_status_items = [
        {"label": "待处理", "value": int(ticket_stats.get("open") or 0), "status": "open"},
        {"label": "处理中", "value": int(ticket_stats.get("in_progress") or 0), "status": "in_progress"},
        {"label": "已解决", "value": int(ticket_stats.get("resolved") or 0), "status": "resolved"},
        {"label": "已关闭", "value": int(ticket_stats.get("closed") or 0), "status": "closed"},
    ]

    total_consumed = sum(item["value"] for item in token_consumption_daily)
    bound_key_count = sum(1 for user in users if user.get("deepseek_is_bound"))
    available_key_count = sum(1 for user in users if int(user.get("deepseek_is_available") or 0))
    disabled_count = sum(1 for user in users if int(user.get("is_disabled") or 0))
    active_user_count = len([user_id for user_id, count in activity_by_user.items() if count > 0])

    return {
        "code": 0,
        "data": {
            "summary": {
                "total_users": len(users),
                "active_users": active_user_count,
                "bound_key_count": bound_key_count,
                "available_key_count": available_key_count,
                "disabled_count": disabled_count,
                "recent_consumed": total_consumed,
                "token_log_count": len(logs),
                "ticket_count": len(tickets),
                "feedback_helpful": int(feedback_stats.get("helpful") or 0),
                "feedback_not_helpful": int(feedback_stats.get("not_helpful") or 0),
            },
            "token_consumption_daily": token_consumption_daily,
            "new_users_daily": new_users_daily,
            "token_actions": token_actions,
            "top_users": top_users[:8],
            "ticket_status": ticket_status_items,
            "ticket_sentiments": [
                {"label": label, "value": value}
                for label, value in sorted(ticket_sentiments.items(), key=lambda item: item[1], reverse=True)
            ],
            "ticket_categories": [
                {"label": label, "value": value}
                for label, value in sorted(ticket_categories.items(), key=lambda item: item[1], reverse=True)[:8]
            ],
        },
        "message": "ok",
    }


@router.get("/tickets")
async def list_tickets(request: Request, status: str = "all"):
    require_admin(request)
    return {"code": 0, "data": support_repo.list_all_tickets(status=status), "message": "ok"}


@router.post("/tickets/{ticket_id}/reply")
async def reply_ticket(request: Request, ticket_id: int, body: TicketReplyRequest):
    admin = require_admin(request)
    reply = body.reply.strip()
    if not reply:
        return {"code": 1, "data": None, "message": "请填写回复内容"}
    status = body.status if body.status in {"open", "in_progress", "resolved", "closed"} else "resolved"
    ok = support_repo.update_ticket_reply(ticket_id, admin["id"], reply, status)
    if not ok:
        return {"code": 1, "data": None, "message": "工单不存在"}
    return {"code": 0, "data": support_repo.get_ticket_by_id(ticket_id), "message": "已回复工单"}


@router.patch("/tickets/{ticket_id}/status")
async def update_ticket_status(request: Request, ticket_id: int, body: TicketStatusRequest):
    admin = require_admin(request)
    if body.status not in {"open", "in_progress", "resolved", "closed"}:
        return {"code": 1, "data": None, "message": "状态不合法"}
    ok = support_repo.update_ticket_status(ticket_id, body.status, admin["id"])
    if not ok:
        return {"code": 1, "data": None, "message": "工单不存在"}
    return {"code": 0, "data": support_repo.get_ticket_by_id(ticket_id), "message": "状态已更新"}


@router.get("/tokens/users")
async def list_token_users(request: Request):
    require_admin(request)
    return {"code": 0, "data": token_repo.list_all_balances(), "message": "ok"}


@router.get("/tokens/logs")
async def list_token_logs(request: Request):
    require_admin(request)
    return {"code": 0, "data": token_repo.get_all_logs(limit=160), "message": "ok"}


@router.patch("/tokens/users/{user_id}/disabled")
async def set_token_disabled(request: Request, user_id: int, body: TokenDisableRequest):
    admin = require_admin(request)
    if user_id == admin["id"] and body.disabled:
        return {"code": 1, "data": None, "message": "不能停用自己的 Token"}
    target = user_repo.get_user_by_id(user_id)
    if not target:
        return {"code": 1, "data": None, "message": "用户不存在"}
    token_repo.set_token_disabled(user_id, body.disabled, admin["id"])
    return {"code": 0, "data": {"user_id": user_id, "disabled": body.disabled}, "message": "Token 状态已更新"}
