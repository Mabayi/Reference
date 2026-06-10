from pathlib import Path

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from services import auth_service
from utils.auth_utils import COOKIE_NAME, create_session_token, get_current_user

router = APIRouter(tags=["认证"])
templates = Jinja2Templates(directory=str(Path(__file__).resolve().parent.parent / "templates"))


@router.get("/login")
async def login_page(request: Request):
    user = get_current_user(request)
    if user:
        target_url = "/admin" if auth_service.is_admin_user(user) else "/"
        return RedirectResponse(url=target_url, status_code=302)
    return templates.TemplateResponse(request=request, name="login.html", context={"error": None})


@router.post("/login")
async def login(
    request: Request,
    identifier: str | None = Form(None),
    email: str | None = Form(None),
    password: str = Form(...),
):
    login_identifier = (identifier or email or "").strip()
    try:
        user = auth_service.authenticate(login_identifier, password)
    except ValueError as error:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"error": str(error)},
        )
    if not user:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"error": "用户名/邮箱或密码错误"},
        )

    target_url = "/admin" if auth_service.is_admin_user(user) else "/"
    response = RedirectResponse(url=target_url, status_code=302)
    token = create_session_token(user["id"])
    response.set_cookie(COOKIE_NAME, token, max_age=7 * 24 * 3600, httponly=True)
    return response


@router.get("/register")
async def register_page(request: Request):
    user = get_current_user(request)
    if user:
        target_url = "/admin" if auth_service.is_admin_user(user) else "/"
        return RedirectResponse(url=target_url, status_code=302)
    return templates.TemplateResponse(request=request, name="register.html", context={"error": None})


@router.post("/register")
async def register(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
):
    if password != confirm_password:
        return templates.TemplateResponse(
            request=request,
            name="register.html",
            context={"error": "两次输入的密码不一致"},
        )

    if len(password) < 6:
        return templates.TemplateResponse(
            request=request,
            name="register.html",
            context={"error": "密码长度不能少于 6 位"},
        )

    try:
        user = auth_service.create_user(username, email, password)
    except ValueError as error:
        return templates.TemplateResponse(
            request=request,
            name="register.html",
            context={"error": str(error)},
        )

    target_url = "/admin" if auth_service.is_admin_user(user) else "/"
    response = RedirectResponse(url=target_url, status_code=302)
    token = create_session_token(user["id"])
    response.set_cookie(COOKIE_NAME, token, max_age=7 * 24 * 3600, httponly=True)
    return response


@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie(COOKIE_NAME)
    return response


@router.get("/api/me")
async def get_me(request: Request):
    user = get_current_user(request)
    if not user:
        return {"code": 1, "data": None, "message": "未登录"}
    return {
        "code": 0,
        "data": {"id": user["id"], "username": user["username"], "email": user["email"]},
        "message": "ok",
    }
