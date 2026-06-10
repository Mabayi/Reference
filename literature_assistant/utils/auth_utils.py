from contextvars import ContextVar

from fastapi import Request
from fastapi.responses import RedirectResponse
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired

from config.settings import settings
from repositories import user_repo

_serializer = URLSafeTimedSerializer(settings.SECRET_KEY)
COOKIE_NAME = "session_token"
MAX_AGE = 7 * 24 * 3600  # 7天
_current_user_id: ContextVar[int | None] = ContextVar("current_user_id", default=None)


def create_session_token(user_id: int) -> str:
    """生成签名 session token"""
    return _serializer.dumps({"user_id": user_id})


def get_current_user(request: Request) -> dict | None:
    """从 cookie 中解析当前用户，未登录返回 None"""
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None
    try:
        data = _serializer.loads(token, max_age=MAX_AGE)
    except (BadSignature, SignatureExpired):
        return None
    return user_repo.get_user_by_id(data["user_id"])


def require_login(request: Request) -> dict:
    """要求登录，未登录则抛出重定向异常"""
    user = get_current_user(request)
    if not user:
        raise LoginRequiredError()
    return user


def get_current_user_id() -> int | None:
    """返回当前请求上下文中的用户 ID。"""
    return _current_user_id.get()


def set_current_user_id(user_id: int | None):
    """设置当前请求上下文用户 ID，并返回可用于 reset 的 token。"""
    return _current_user_id.set(user_id)


def reset_current_user_id(token) -> None:
    """恢复当前请求上下文用户 ID。"""
    _current_user_id.reset(token)


def require_admin(request: Request) -> dict:
    """要求管理员权限。"""
    user = require_login(request)
    if not user_repo.is_admin_username(user.get("username")):
        raise AdminRequiredError()
    return user


class LoginRequiredError(Exception):
    """未登录异常，由全局异常处理器捕获并重定向"""
    pass


class AdminRequiredError(Exception):
    """非管理员异常。"""
    pass
