"""Token 管理路由。"""
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from config.settings import settings
from repositories import token_repo
from services import deepseek_account_service
from utils.auth_utils import require_login

router = APIRouter(prefix="/api/tokens", tags=["Token 管理"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


class RedeemRequest(BaseModel):
    key: str


class PurchaseRequest(BaseModel):
    package_id: int


class BindDeepSeekKeyRequest(BaseModel):
    api_key: str


@router.get("/balance")
async def get_balance(request: Request):
    user = require_login(request)
    balance = token_repo.get_balance(user["id"])
    return {"code": 0, "data": balance, "message": "ok"}


@router.get("/deepseek/status")
async def deepseek_status(request: Request):
    user = require_login(request)
    balance = token_repo.get_balance(user["id"])
    user_account = token_repo.get_deepseek_api_key(user["id"])
    system_api_key = settings.DEEPSEEK_API_KEY
    is_user_bound = bool(user_account)
    active_key_mask = user_account.get("key_mask") if user_account else (
        token_repo.mask_api_key(system_api_key) if system_api_key else ""
    )
    return {
        "code": 0,
        "data": {
            "is_bound": is_user_bound or bool(system_api_key),
            "is_user_bound": is_user_bound,
            "key_source": "user" if is_user_bound else ("system" if system_api_key else "none"),
            "key_mask": active_key_mask,
            "user_account": user_account,
            "balance": balance,
            "billing_cents_per_1000_tokens": str(settings.API_BILLING_CENTS_PER_1000_TOKENS),
        },
        "message": "ok" if (is_user_bound or system_api_key) else "系统 API Key 未配置，请联系管理员",
    }


@router.post("/deepseek/bind")
async def bind_deepseek_key(request: Request, body: BindDeepSeekKeyRequest):
    user = require_login(request)
    existing_owner = token_repo.find_deepseek_key_owner(body.api_key)
    if existing_owner and existing_owner != int(user["id"]):
        return {"code": 1, "data": None, "message": "该 DeepSeek API Key 已被其他账户兑换绑定。"}

    try:
        remote_balance = await deepseek_account_service.fetch_user_balance(body.api_key)
    except deepseek_account_service.DeepSeekAccountError as exc:
        return {"code": 1, "data": None, "message": str(exc)}

    account = token_repo.save_deepseek_api_key(user["id"], body.api_key, remote_balance)
    return {"code": 0, "data": account, "message": "DeepSeek API Key 已验证并绑定，后续 AI 调用将优先使用该密钥。"}


@router.post("/deepseek/refresh")
async def refresh_deepseek_balance(request: Request):
    user = require_login(request)
    account = token_repo.get_deepseek_api_key(user["id"], include_secret=True)
    if not account:
        return {"code": 1, "data": None, "message": "请先兑换或绑定 DeepSeek API Key"}

    try:
        remote_balance = await deepseek_account_service.fetch_user_balance(account["api_key"])
    except deepseek_account_service.DeepSeekAccountError as exc:
        return {"code": 1, "data": None, "message": str(exc)}

    updated = token_repo.update_deepseek_balance(user["id"], remote_balance)
    return {"code": 0, "data": updated, "message": "DeepSeek 密钥余额已刷新"}


@router.delete("/deepseek/key")
async def remove_deepseek_key(request: Request):
    user = require_login(request)
    ok = token_repo.delete_deepseek_api_key(user["id"])
    if not ok:
        return {"code": 1, "data": None, "message": "当前没有已绑定的 DeepSeek API Key"}
    return {"code": 0, "data": {"is_bound": False}, "message": "已移除已绑定的 DeepSeek API Key"}


@router.get("/stats")
async def get_stats(request: Request):
    user = require_login(request)
    return {
        "code": 0,
        "data": {
            "today": token_repo.get_today_consumption(user["id"]),
            "week": token_repo.get_week_consumption(user["id"]),
        },
        "message": "ok",
    }


@router.get("/logs")
async def get_logs(request: Request):
    user = require_login(request)
    logs = token_repo.get_logs(user["id"], days=7)
    return {"code": 0, "data": logs, "message": "ok"}


@router.get("/packages")
async def get_packages(request: Request):
    require_login(request)
    return {
        "code": 0,
        "data": {
            "platform_url": "https://platform.deepseek.com",
            "api_keys_url": "https://platform.deepseek.com/api_keys",
            "top_up_url": "https://platform.deepseek.com/top_up",
            "pricing_url": "https://api-docs.deepseek.com/quick_start/pricing",
        },
        "message": "可在本页兑换并绑定 DeepSeek API Key，系统会校验密钥有效性",
    }


@router.post("/redeem")
async def redeem(request: Request, body: RedeemRequest):
    user = require_login(request)
    existing_owner = token_repo.find_deepseek_key_owner(body.key)
    if existing_owner and existing_owner != int(user["id"]):
        return {"code": 1, "data": None, "message": "该 DeepSeek API Key 已被其他账户兑换绑定。"}

    try:
        remote_balance = await deepseek_account_service.fetch_user_balance(body.key)
    except deepseek_account_service.DeepSeekAccountError as exc:
        return {"code": 1, "data": None, "message": str(exc)}

    account = token_repo.save_deepseek_api_key(user["id"], body.key, remote_balance)
    return {"code": 0, "data": account, "message": "密钥兑换成功，DeepSeek API Key 已绑定到当前账户。"}


@router.post("/purchase")
async def purchase(request: Request, body: PurchaseRequest):
    require_login(request)
    return {
        "code": 1,
        "data": {
            "contact": "wechat",
        },
        "message": "线上自动支付暂未开通。如需充值请添加客服微信。",
    }
