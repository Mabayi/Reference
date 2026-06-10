from __future__ import annotations

from services.llm_service import chat_completion


LANGUAGE_MAP = {
    "zh": "中文",
    "en": "英文",
    "ja": "日文",
}


async def translate_text(text: str, target_lang: str = "zh") -> str:
    target = LANGUAGE_MAP.get(target_lang, "中文")
    return await chat_completion(
        system_prompt=f"""
你是一名学术翻译助手。
要求：
1. 忠实翻译，不要添加原文中没有的实验结果、引用或解释。
2. 保留术语准确性，优先采用学术语境下常用译法。
3. 输出目标语言为{target}。
4. 只输出译文，不要附加说明。
""".strip(),
        user_prompt=f"请翻译以下文本：\n\n{text}",
        temperature=0.1,
        max_tokens=1800,
    )

