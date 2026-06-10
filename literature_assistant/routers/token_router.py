"""Token 管理路由。"""
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from config.settings import settings
from repositories import token_repo
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
    api_key = settings.DEEPSEEK_API_KEY
    return {
        "code": 0,
        "data": {
            "is_bound": bool(api_key),
            "key_mask": token_repo.mask_api_key(api_key) if api_key else "",
            "balance": balance,
            "billing_cents_per_1000_tokens": str(settings.API_BILLING_CENTS_PER_1000_TOKENS),
        },
        "message": "ok" if api_key else "系统 API Key 未配置，请联系管理员",
    }


@router.post("/deepseek/bind")
async def bind_deepseek_key(request: Request, body: BindDeepSeekKeyRequest):
    require_login(request)
    return {"code": 1, "data": None, "message": "系统已启用统一 API Key，无需用户绑定个人密钥。"}


@router.post("/deepseek/refresh")
async def refresh_deepseek_balance(request: Request):
    require_login(request)
    return {"code": 1, "data": None, "message": "系统统一密钥由管理员维护，用户侧无需刷新密钥余额。"}


@router.delete("/deepseek/key")
async def remove_deepseek_key(request: Request):
    require_login(request)
    return {"code": 1, "data": None, "message": "系统已启用统一 API Key，用户侧不能移除密钥。"}


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
            "top_up_url": "https://platform.deepseek.com/top_up",
            "pricing_url": "https://api-docs.deepseek.com/quick_start/pricing",
        },
        "message": "系统使用本地额度计费，如需充值请联系客服",
    }


@router.post("/redeem")
async def redeem(request: Request, body: RedeemRequest):
    require_login(request)
    return {
        "code": 1,
        "data": None,
        "message": "本地兑换码已关闭。如需充值请在 Token 页面联系客服。",
    }


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
