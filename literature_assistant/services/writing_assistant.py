from __future__ import annotations

from services.llm_service import chat_completion


async def generate_method(content: str, stats_method: str = "") -> str:
    stats_clause = stats_method.strip() or "若输入中未指定统计方法，请明确说明统计设计尚不充分，不要编造。"
    return await chat_completion(
        system_prompt="""
你是一名严谨的学术论文写作助手，负责撰写“方法”部分。
要求：
1. 只能基于用户提供的信息扩写，不要编造数据集规模、参数数量、实验结果或伦理审批信息。
2. 输出中文学术写作风格，结构紧凑，避免套话。
3. 对不充分的信息要直接指出缺口，例如 [CITE NEEDED] 或“此处需补充具体设置”。
4. 如果涉及深度学习训练流程，优先提到随机种子、日志记录、检查点保存和复现设置。
""".strip(),
        user_prompt=f"""
请根据以下研究内容撰写论文方法部分草稿。

研究内容：
{content}

统计方法说明：
{stats_clause}
""".strip(),
        temperature=0.4,
        max_tokens=1600,
    )


async def generate_discussion(results: str, references: str = "") -> str:
    return await chat_completion(
        system_prompt="""
你是一名严谨的学术论文写作助手，负责撰写“讨论”部分。
要求：
1. 先指出局限和不确定性，再总结可能的贡献。
2. 不要捏造对比实验、外部文献结论或统计显著性。
3. 若用户没有提供足够证据，请明确写出证据不足，不要强行拔高结论。
4. 输出中文学术写作风格，允许使用 [CITE NEEDED] 标注缺失引用。
""".strip(),
        user_prompt=f"""
请根据以下结果撰写论文讨论部分草稿。

研究结果：
{results}

参考文献信息（若为空则不要虚构）：
{references or "未提供"}
""".strip(),
        temperature=0.4,
        max_tokens=1600,
    )


async def polish_text(text: str, language: str = "中文") -> str:
    target_language = "英文" if language.lower() in {"english", "en", "英文"} else "中文"
    return await chat_completion(
        system_prompt=f"""
你是一名学术文本润色助手。
要求：
1. 保持原意，不得添加新的实验结果、引用或事实。
2. 提高逻辑性、准确性和学术表达。
3. 输出语言为{target_language}。
4. 如果原文存在明显结论过度、因果跳跃或证据不足，请直接收敛表述。
""".strip(),
        user_prompt=f"请润色以下文本：\n\n{text}",
        temperature=0.2,
        max_tokens=1800,
    )

