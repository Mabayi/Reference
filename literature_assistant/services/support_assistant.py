from __future__ import annotations

from services.llm_service import LLMServiceError, chat_completion


async def generate_support_reply(
    *,
    subject: str,
    message: str,
    faq_title: str = "",
    faq_answer: str = "",
) -> str:
    fallback = _fallback_reply(faq_answer)
    try:
        reply = await chat_completion(
            system_prompt="""
你是 Reference System 的客服助手。
请基于用户问题和系统给出的固定答案回复，不要编造不存在的功能、账号状态、修复进度或后台处理结果。
回复要求：
1. 先给出可执行处理建议。
2. 如果问题需要人工介入，说明系统已记录为工单。
3. 语气清楚、简洁，不要使用 Markdown 星号或复杂格式。
4. 控制在 180 字以内。
""".strip(),
            user_prompt=f"""
常见问题：{faq_title or "未选择"}
固定答案：{faq_answer or "无"}
用户标题：{subject}
用户描述：
{message}
""".strip(),
            temperature=0.25,
            max_tokens=420,
        )
    except LLMServiceError:
        return fallback

    normalized = " ".join(line.strip() for line in reply.splitlines() if line.strip())
    return normalized[:360] or fallback


def _fallback_reply(faq_answer: str) -> str:
    if faq_answer.strip():
        return f"{faq_answer.strip()} 如果按上述方式仍无法解决，系统已为你记录工单，管理员可以在后台继续处理。"
    return "系统已记录你的问题。请补充出现问题的页面、操作步骤和期望结果，管理员可以在后台继续处理。"
