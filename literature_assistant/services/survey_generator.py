from __future__ import annotations

import re
from typing import AsyncGenerator

from services.llm_service import chat_completion, stream_chat_completion


SURVEY_SYSTEM_PROMPT = """
你是一名严谨的学术综述写作助手。
要求：
1. 只能基于用户提供的主题和参考上下文写作，不要捏造论文、作者、年份、指标或实验结论。
2. 如果上下文不足，明确指出证据不足，不要编造。
3. 涉及需要引用支撑的判断时，优先保留上下文中的 [文献ID] 标记；如果无法确认来源，用 [CITE NEEDED] 标记。
4. 输出使用中文纯文本，不要使用 Markdown 标记，不要使用星号、井号标题、反引号、横线列表符号或加粗符号。
5. 结构清晰，包含：研究背景、方法脉络、代表性进展、问题与空白、结论与展望。
6. 先批判不足，再总结亮点，语气克制，不要套话。
"""

TOPIC_RECOMMENDATION_PROMPT = """
你是一名严谨的学术选题助手。
任务：根据用户选择的参考文献，为综述生成页面推荐一个中文研究主题关键词或短语。
要求：
1. 只能基于给定文献信息概括，不要引入文献中没有的研究对象、数据集、模型或结论。
2. 输出一个主题即可，不要输出多个选项。
3. 主题应适合作为综述题目或检索关键词，长度控制在 6 到 24 个中文字符之间。
4. 不要使用 Markdown，不要使用星号、引号、冒号、编号、项目符号或解释性文字。
"""


def _clean_recommended_topic(value: str) -> str:
    text = value.strip()
    for marker in ("**", "*", "`", "#", "“", "”", "\"", "'", "：", ":"):
        text = text.replace(marker, "")
    text = re.sub(r"^\s*\d+[.)、]\s*", "", text)
    lines = [line.strip(" -•●▪◆·\t\r\n") for line in text.splitlines() if line.strip()]
    topic = lines[0] if lines else ""
    for prefix in ("推荐主题为", "推荐主题是", "推荐主题", "建议主题为", "建议主题是", "建议主题", "关键词为", "关键词是", "关键词"):
        if topic.startswith(prefix):
            topic = topic[len(prefix):].strip()
    return topic[:40].strip(" ，。；;、")


def _build_user_prompt(topic: str, context: str) -> str:
    safe_context = context.strip() or "当前没有检索到可用文献上下文。请只输出一个诚实的综述框架，并明确说明证据不足。"
    return f"""
研究主题：{topic}

参考上下文：
{safe_context}

请生成一篇结构化综述草稿。请使用纯文本小标题和自然段，不要使用 Markdown 符号、星号、项目符号或加粗标记。
"""


async def generate_survey_stream(
    topic: str,
    context: str,
    api_key: str | None = None,
    usage_user_id: int | None = None,
) -> AsyncGenerator[str, None]:
    async for chunk in stream_chat_completion(
        system_prompt=SURVEY_SYSTEM_PROMPT,
        user_prompt=_build_user_prompt(topic, context),
        temperature=0.4,
        max_tokens=3200,
        api_key=api_key,
        usage_user_id=usage_user_id,
    ):
        yield chunk


async def generate_survey(topic: str, context: str) -> str:
    parts: list[str] = []
    async for chunk in generate_survey_stream(topic, context):
        parts.append(chunk)
    return "".join(parts).strip()


async def recommend_survey_topic(context: str) -> str:
    safe_context = context.strip()
    if not safe_context:
        return ""

    content = await chat_completion(
        system_prompt=TOPIC_RECOMMENDATION_PROMPT,
        user_prompt=f"参考文献信息：\n{safe_context}\n\n请推荐一个最适合的中文研究主题关键词或短语。",
        temperature=0.2,
        max_tokens=80,
    )
    return _clean_recommended_topic(content)
