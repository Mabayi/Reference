"""Token 管理路由。"""
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

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
    account = token_repo.get_deepseek_api_key(user["id"])
    if not account:
        return {"code": 0, "data": {"is_bound": False}, "message": "未绑定 DeepSeek API Key"}
    return {"code": 0, "data": account, "message": "ok"}


@router.post("/deepseek/bind")
async def bind_deepseek_key(request: Request, body: BindDeepSeekKeyRequest):
    user = require_login(request)
    balance = token_repo.get_balance(user["id"])
    if int(balance.get("is_disabled") or 0):
        return {"code": 1, "data": None, "message": "当前账户 API 使用已被停用，请联系客服"}

    try:
        remote_balance = await deepseek_account_service.fetch_user_balance(body.api_key)
    except deepseek_account_service.DeepSeekAccountError as exc:
        return {"code": 1, "data": None, "message": str(exc)}

    account = token_repo.save_deepseek_api_key(user["id"], body.api_key, remote_balance)
    return {"code": 0, "data": account, "message": "DeepSeek API Key 已绑定，并已同步真实余额"}


@router.post("/deepseek/refresh")
async def refresh_deepseek_balance(request: Request):
    user = require_login(request)
    account = token_repo.get_deepseek_api_key(user["id"], include_secret=True)
    if not account:
        return {"code": 1, "data": None, "message": "请先绑定 DeepSeek API Key"}

    try:
        remote_balance = await deepseek_account_service.fetch_user_balance(account["api_key"])
    except deepseek_account_service.DeepSeekAccountError as exc:
        return {"code": 1, "data": None, "message": str(exc)}

    updated = token_repo.update_deepseek_balance(user["id"], remote_balance)
    return {"code": 0, "data": updated, "message": "DeepSeek 真实余额已刷新"}


@router.delete("/deepseek/key")
async def remove_deepseek_key(request: Request):
    user = require_login(request)
    ok = token_repo.delete_deepseek_api_key(user["id"])
    if not ok:
        return {"code": 1, "data": None, "message": "当前没有已绑定的 DeepSeek API Key"}
    return {"code": 0, "data": {"is_bound": False}, "message": "已移除 DeepSeek API Key"}


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
        "message": "本地虚拟套餐已关闭，请前往 DeepSeek 官方平台购买或充值",
    }


@router.post("/redeem")
async def redeem(request: Request, body: RedeemRequest):
    require_login(request)
    return {
        "code": 1,
        "data": None,
        "message": "本地兑换码已关闭。请绑定真实 DeepSeek API Key，并在 DeepSeek 官方平台充值。",
    }


@router.post("/purchase")
async def purchase(request: Request, body: PurchaseRequest):
    require_login(request)
    return {
        "code": 1,
        "data": {
            "top_up_url": "https://platform.deepseek.com/top_up",
            "platform_url": "https://platform.deepseek.com",
        },
        "message": "本地虚拟购买已关闭。请前往 DeepSeek 官方平台充值，充值后回到本页刷新真实余额。",
    }
