import json
import re
from datetime import datetime

from fastapi import APIRouter, Request

from repositories import experiment_repo, paper_repo, survey_repo
from utils.auth_utils import require_login

router = APIRouter(prefix="/api/dashboard", tags=["趋势大屏"])


def _parse_keywords(raw_keywords) -> list[str]:
    if not raw_keywords:
        return []
    if isinstance(raw_keywords, list):
        candidates = raw_keywords
    elif isinstance(raw_keywords, str):
        text = raw_keywords.strip()
        if not text:
            return []
        try:
            parsed = json.loads(text)
        except (json.JSONDecodeError, TypeError):
            parsed = None
        if isinstance(parsed, list):
            candidates = parsed
        elif isinstance(parsed, str):
            candidates = re.split(r"[,，;；、\n]+", parsed)
        else:
            candidates = re.split(r"[,，;；、\n]+", text.strip("[]"))
    else:
        return []

    keywords: list[str] = []
    for item in candidates:
        word = str(item).strip().strip("\"'“”‘’[]()（）")
        if word:
            keywords.append(word)
    return keywords


def _normalize_year(value) -> str | None:
    if value in (None, ""):
        return None
    match = re.search(r"(19|20)\d{2}", str(value))
    if not match:
        return None
    return match.group(0)


@router.get("/keywords")
async def get_keywords(request: Request):
    """统计关键词频次。"""
    user = require_login(request)
    papers = paper_repo.get_papers_by_user(user["id"])
    word_count: dict[str, int] = {}

    for paper in papers:
        for word in _parse_keywords(paper.get("keywords")):
            word_count[word] = word_count.get(word, 0) + 1

    result = [{"word": key, "count": value} for key, value in sorted(word_count.items(), key=lambda item: -item[1])]
    return {"code": 0, "data": result, "message": "ok"}


@router.get("/yearly-trend")
async def get_yearly_trend(request: Request):
    """统计年度文献数量。"""
    user = require_login(request)
    papers = paper_repo.get_papers_by_user(user["id"])
    year_count: dict[str, int] = {}

    for paper in papers:
        year = _normalize_year(paper.get("year"))
        if year is not None:
            year_count[year] = year_count.get(year, 0) + 1

    result = [{"year": key, "count": value} for key, value in sorted(year_count.items())]
    return {"code": 0, "data": result, "message": "ok"}


@router.get("/top-papers")
async def get_top_papers(request: Request):
    """返回最近 10 篇文献。"""
    user = require_login(request)
    papers = paper_repo.get_papers_by_user(user["id"])[:10]
    result = [{"id": paper["id"], "title": paper["title"], "authors": paper["authors"], "year": paper["year"]} for paper in papers]
    return {"code": 0, "data": result, "message": "ok"}


@router.get("/stats")
async def get_stats(request: Request):
    """返回首页统计卡片数据。"""
    user = require_login(request)
    papers = paper_repo.get_papers_by_user(user["id"])
    surveys = survey_repo.get_surveys_by_user(user["id"])
    experiment_count = experiment_repo.count_experiments(user["id"])
    current_month = datetime.now().strftime("%Y-%m")
    papers_this_month = sum(1 for paper in papers if str(paper.get("created_at", "")).startswith(current_month))
    return {
        "code": 0,
        "data": {
            "total_papers": len(papers),
            "total_surveys": len(surveys),
            "total_experiments": experiment_count,
            "papers_this_month": papers_this_month,
        },
        "message": "ok",
    }
