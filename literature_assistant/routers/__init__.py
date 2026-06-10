from .paper_router import router as paper_router
from .survey_router import router as survey_router
from .experiment_router import router as experiment_router
from .codegen_router import router as codegen_router
from .chart_router import router as chart_router
from .writing_router import router as writing_router
from .citation_router import router as citation_router
from .dashboard_router import router as dashboard_router
from .auth_router import router as auth_router
from .rag_router import router as rag_router
from .reader_router import router as reader_router
from .token_router import router as token_router
from .support_router import router as support_router
from .admin_router import router as admin_router

__all__ = [
    "paper_router",
    "survey_router",
    "experiment_router",
    "codegen_router",
    "chart_router",
    "writing_router",
    "citation_router",
    "dashboard_router",
    "auth_router",
    "rag_router",
    "reader_router",
    "token_router",
    "support_router",
    "admin_router",
]
