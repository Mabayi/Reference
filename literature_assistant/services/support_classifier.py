from __future__ import annotations

from typing import Any

from services.llm_service import LLMServiceError, json_completion

SUPPORT_CATEGORIES = {"账户登录", "文献上传解析", "AI生成质量", "Token计费", "页面显示", "功能建议", "其他"}
SENTIMENT_LABELS = {"平静", "中性", "着急", "不满", "愤怒"}
PRIORITIES = {"普通", "较高", "紧急"}
FAQ_CATEGORY_MAP = {
    "upload_parse": "文献上传解析",
    "pdf_display": "页面显示",
    "ai_quality": "AI生成质量",
    "token_billing": "Token计费",
    "account_login": "账户登录",
    "feature_request": "功能建议",
}


def _normalize_choice(value: Any, choices: set[str], default: str) -> str:
    text = str(value or "").strip()
    return text if text in choices else default


def _fallback_classification(subject: str, message: str, faq_key: str = "") -> dict:
    text = f"{subject} {message}"
    category = FAQ_CATEGORY_MAP.get(faq_key, "其他")
    if any(word in text for word in ("Token", "token", "余额", "扣费", "购买", "兑换")):
        category = "Token计费"
    elif any(word in text for word in ("页面", "看不清", "字体", "布局", "深色", "浅色", "显示", "弹窗")):
        category = "页面显示"
    elif any(word in text for word in ("上传", "解析", "PDF", "文献")):
        category = "文献上传解析"
    elif any(word in text for word in ("登录", "注册", "账户", "密码")):
        category = "账户登录"
    elif any(word in text for word in ("AI", "生成", "总结", "综述", "实验")):
        category = "AI生成质量"

    sentiment = "中性"
    sentiment_score = 2
    if any(word in text for word in ("不能用", "失败", "崩", "急", "赶")):
        sentiment = "着急"
        sentiment_score = 3
    if any(word in text for word in ("很差", "生气", "离谱", "坑人", "愤怒")):
        sentiment = "不满"
        sentiment_score = 4

    priority = "较高" if sentiment_score >= 3 else "普通"
    return {
        "category": category,
        "sentiment": sentiment,
        "sentiment_score": sentiment_score,
        "priority": priority,
        "summary": message[:80].strip() or subject[:80].strip(),
    }


async def classify_ticket(subject: str, message: str, faq_key: str = "") -> dict:
    try:
        result = await json_completion(
            system_prompt="""
你是客服工单分类助手。
请只基于用户问题进行分类，不要编造用户没有说过的事实。
返回 JSON，字段必须包含：
category: 只能是 账户登录、文献上传解析、AI生成质量、Token计费、页面显示、功能建议、其他
sentiment: 只能是 平静、中性、着急、不满、愤怒
sentiment_score: 1 到 5 的整数，1 最平静，5 最强烈
priority: 只能是 普通、较高、紧急
summary: 40 字以内的问题摘要
""".strip(),
            user_prompt=f"""
常见问题选项：{faq_key or "未选择"}
标题：{subject}
用户问题：
{message}
""".strip(),
            temperature=0.2,
            max_tokens=500,
        )
    except LLMServiceError:
        return _fallback_classification(subject, message, faq_key)

    score = result.get("sentiment_score", 2)
    try:
        score_int = min(5, max(1, int(score)))
    except (TypeError, ValueError):
        score_int = 2

    category = _normalize_choice(result.get("category"), SUPPORT_CATEGORIES, FAQ_CATEGORY_MAP.get(faq_key, "其他"))
    if faq_key == "pdf_display" and category == "文献上传解析":
        category = "页面显示"

    return {
        "category": category,
        "sentiment": _normalize_choice(result.get("sentiment"), SENTIMENT_LABELS, "中性"),
        "sentiment_score": score_int,
        "priority": _normalize_choice(result.get("priority"), PRIORITIES, "普通"),
        "summary": str(result.get("summary") or message[:80] or subject[:80]).strip()[:80],
    }
