from __future__ import annotations

from services.llm_service import chat_completion


async def generate_code(experiment_summary: str, language: str = "python", stats_method: str = "") -> str:
    target_language = "R" if language.lower() == "r" else "Python"
    extra_constraints = """
1. Python 代码必须使用类型提示和 4 个空格缩进。
2. 若涉及深度学习，默认使用 PyTorch，不要使用 TensorFlow。
3. 若是训练脚本骨架，必须包含随机种子、损失日志记录、检查点保存和可复现设置。
4. 如果输入信息不足，不要编造真实数据；可以保留 TODO 注释或参数占位。
5. 只输出代码，不要添加解释性文字或 Markdown 代码块。
""".strip()
    if target_language == "R":
        extra_constraints = """
1. 代码应可直接作为分析脚本骨架使用。
2. 如果输入信息不足，不要编造真实数据；可以保留 TODO 注释或参数占位。
3. 只输出代码，不要添加解释性文字或 Markdown 代码块。
""".strip()

    stats_clause = stats_method.strip() or "未指定"
    return await chat_completion(
        system_prompt=f"""
你是一名科研代码助手，负责生成 {target_language} 分析或实验脚本。
要求：
{extra_constraints}
""".strip(),
        user_prompt=f"""
任务说明：
{experiment_summary}

统计方法：
{stats_clause}
""".strip(),
        temperature=0.2,
        max_tokens=2200,
    )

