from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from config.settings import settings
from repositories import annotation_repo, experiment_repo, paper_repo, support_repo, token_repo, user_repo
from repositories import survey_repo as survey_repo_mod
from routers import (
    auth_router,
    admin_router,
    chart_router,
    citation_router,
    codegen_router,
    dashboard_router,
    experiment_router,
    paper_router,
    rag_router,
    reader_router,
    survey_router,
    support_router,
    token_router,
    writing_router,
)
from utils.auth_utils import (
    AdminRequiredError,
    LoginRequiredError,
    get_current_user,
    require_admin,
    require_login,
    reset_current_user_id,
    set_current_user_id,
)
from services import auth_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动时初始化数据库表。"""
    user_repo.init_db()
    paper_repo.init_papers_table()
    survey_repo_mod.init_surveys_table()
    annotation_repo.init_annotations_table()
    experiment_repo.init_experiments_table()
    token_repo.init_token_tables()
    support_repo.init_support_tables()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="Reference System",
        description="面向学术研究场景的本地文献与写作工作台",
        version="0.2.0",
        lifespan=lifespan,
    )

    static_dir = Path(__file__).parent / "static"
    static_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
    app.mount("/uploads", StaticFiles(directory=str(settings.UPLOAD_DIR)), name="uploads")

    templates_dir = Path(__file__).parent / "templates"
    templates = Jinja2Templates(directory=str(templates_dir))

    @app.middleware("http")
    async def current_user_context_middleware(request: Request, call_next):
        user = get_current_user(request)
        token = set_current_user_id(int(user["id"]) if user else None)
        try:
            return await call_next(request)
        finally:
            reset_current_user_id(token)

    @app.exception_handler(LoginRequiredError)
    async def login_required_handler(request: Request, exc: LoginRequiredError):
        if request.url.path.startswith("/api/"):
            return JSONResponse(status_code=401, content={"code": 1, "data": None, "message": "请先登录"})
        return RedirectResponse(url="/login", status_code=302)

    @app.exception_handler(AdminRequiredError)
    async def admin_required_handler(request: Request, exc: AdminRequiredError):
        if request.url.path.startswith("/api/"):
            return JSONResponse(status_code=403, content={"code": 1, "data": None, "message": "需要管理员权限"})
        return RedirectResponse(url="/", status_code=302)

    app.include_router(auth_router)
    app.include_router(paper_router)
    app.include_router(survey_router)
    app.include_router(experiment_router)
    app.include_router(codegen_router)
    app.include_router(chart_router)
    app.include_router(writing_router)
    app.include_router(citation_router)
    app.include_router(dashboard_router)
    app.include_router(rag_router)
    app.include_router(reader_router)
    app.include_router(token_router)
    app.include_router(support_router)
    app.include_router(admin_router)

    @app.get("/")
    async def index(request: Request):
        user = require_login(request)
        if auth_service.is_admin_user(user):
            return RedirectResponse(url="/admin", status_code=302)
        return templates.TemplateResponse(request=request, name="index.html", context={"user": user, "active_page": "home"})

    @app.get("/papers")
    async def papers_page(request: Request):
        user = require_login(request)
        if auth_service.is_admin_user(user):
            return RedirectResponse(url="/admin", status_code=302)
        return templates.TemplateResponse(request=request, name="papers.html", context={"user": user, "active_page": "papers"})

    @app.get("/survey")
    async def survey_page(request: Request):
        user = require_login(request)
        if auth_service.is_admin_user(user):
            return RedirectResponse(url="/admin", status_code=302)
        return templates.TemplateResponse(request=request, name="survey.html", context={"user": user, "active_page": "survey"})

    @app.get("/experiment")
    async def experiment_page(request: Request):
        user = require_login(request)
        if auth_service.is_admin_user(user):
            return RedirectResponse(url="/admin", status_code=302)
        return templates.TemplateResponse(request=request, name="experiment.html", context={"user": user, "active_page": "experiment"})

    @app.get("/codegen")
    async def codegen_page(request: Request):
        user = require_login(request)
        if auth_service.is_admin_user(user):
            return RedirectResponse(url="/admin", status_code=302)
        return templates.TemplateResponse(request=request, name="codegen.html", context={"user": user, "active_page": "codegen"})

    @app.get("/writing")
    async def writing_page(request: Request):
        user = require_login(request)
        if auth_service.is_admin_user(user):
            return RedirectResponse(url="/admin", status_code=302)
        return templates.TemplateResponse(request=request, name="writing.html", context={"user": user, "active_page": "writing"})

    @app.get("/citation")
    async def citation_page(request: Request):
        user = require_login(request)
        if auth_service.is_admin_user(user):
            return RedirectResponse(url="/admin", status_code=302)
        return templates.TemplateResponse(request=request, name="citation.html", context={"user": user, "active_page": "citation"})

    @app.get("/dashboard")
    async def dashboard_page(request: Request):
        user = require_login(request)
        if auth_service.is_admin_user(user):
            return RedirectResponse(url="/admin", status_code=302)
        return templates.TemplateResponse(request=request, name="dashboard.html", context={"user": user, "active_page": "dashboard"})

    @app.get("/chart")
    async def chart_page(request: Request):
        user = require_login(request)
        if auth_service.is_admin_user(user):
            return RedirectResponse(url="/admin", status_code=302)
        return templates.TemplateResponse(request=request, name="chart.html", context={"user": user, "active_page": "chart"})

    @app.get("/rag")
    async def rag_page(request: Request):
        user = require_login(request)
        if auth_service.is_admin_user(user):
            return RedirectResponse(url="/admin", status_code=302)
        return templates.TemplateResponse(request=request, name="rag.html", context={"user": user, "active_page": "rag"})

    @app.get("/tokens")
    async def tokens_page(request: Request):
        user = require_login(request)
        if auth_service.is_admin_user(user):
            return RedirectResponse(url="/admin", status_code=302)
        return templates.TemplateResponse(request=request, name="tokens.html", context={"user": user, "active_page": "tokens"})

    @app.get("/support")
    async def support_page(request: Request):
        user = require_login(request)
        if auth_service.is_admin_user(user):
            return RedirectResponse(url="/admin", status_code=302)
        return templates.TemplateResponse(request=request, name="support.html", context={"user": user, "active_page": "support"})

    @app.get("/admin")
    async def admin_page(request: Request):
        user = require_admin(request)
        return templates.TemplateResponse(request=request, name="admin.html", context={"user": user, "active_page": "admin"})

    return app


app = create_app()
