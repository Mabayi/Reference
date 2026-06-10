from __future__ import annotations

import re
from typing import Any

from services.llm_service import chat_completion, json_completion


def _normalize_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _clean_recommended_text(value: str) -> str:
    text = value.strip()
    for marker in ("**", "*", "`", "#", "“", "”", "\"", "'", "：", ":"):
        text = text.replace(marker, "")
    text = re.sub(r"^\s*\d+[.)、]\s*", "", text)
    lines = [line.strip(" -•●▪◆·\t\r\n") for line in text.splitlines() if line.strip()]
    cleaned = lines[0] if lines else ""
    for prefix in ("研究目标为", "研究目标是", "研究目标", "目标为", "目标是", "目标", "研究假设为", "研究假设是", "研究假设", "假设为", "假设是", "假设"):
        if cleaned.startswith(prefix):
            cleaned = cleaned[len(prefix):].strip()
    return cleaned.strip(" ，。；;、")


async def recommend_goal(paper_context: str) -> str:
    safe_context = paper_context.strip()
    if not safe_context:
        return ""

    content = await chat_completion(
        system_prompt="""
你是一名严谨的研究方法导师，负责从单篇参考文献中提炼可实验化研究目标。
要求：
1. 只能基于给定参考文献信息，不要编造数据集、模型、指标或结论。
2. 输出一句中文研究目标，适合直接填入实验设计页面。
3. 目标应包含研究对象和可比较/可验证的实验方向。
4. 不要使用 Markdown、编号、星号、引号、冒号或解释性文字。
""".strip(),
        user_prompt=f"参考文献上下文：\n{safe_context}\n\n请生成一个研究目标。",
        temperature=0.25,
        max_tokens=120,
    )
    return _clean_recommended_text(content)


async def recommend_hypothesis(paper_context: str, goal: str = "") -> str:
    safe_context = paper_context.strip()
    if not safe_context:
        return ""

    goal_clause = goal.strip() or "用户尚未提供研究目标，请基于参考文献生成一个保守、可检验的假设。"
    content = await chat_completion(
        system_prompt="""
你是一名严谨的研究方法导师，负责从单篇参考文献和研究目标中提出可检验研究假设。
要求：
1. 只能基于给定参考文献信息和研究目标，不要编造实验结果、准确率、数据集规模或统计显著性。
2. 输出一句中文研究假设，适合直接填入实验设计页面。
3. 假设必须可被实验比较或统计检验。
4. 不要使用 Markdown、编号、星号、引号、冒号或解释性文字。
""".strip(),
        user_prompt=f"""
研究目标：
{goal_clause}

参考文献上下文：
{safe_context}

请生成一个研究假设。
""".strip(),
        temperature=0.25,
        max_tokens=120,
    )
    return _clean_recommended_text(content)


async def design_experiment(goal: str, hypothesis: str, paper_context: str = "") -> dict[str, Any]:
    context_clause = paper_context.strip() or "未选择参考文献。请只基于用户输入设计实验，不要补造文献依据。"
    result = await json_completion(
        system_prompt="""
你是一名严谨的研究方法导师，负责设计实验草案。
要求：
1. 不要捏造具体实验结果。
2. 如果样本量无法从输入推断，不要给出伪精确数字，可写“待通过功效分析估算”。
3. 如果提供了参考文献上下文，只能把它作为研究对象、方法线索和风险控制依据，不要编造文献中没有的实验数据。
4. 输出 JSON，包含：
   goal, hypothesis,
   variables.independent, variables.dependent, variables.controlled,
   sample.size, sample.calculation_basis, sample.groups, sample.randomization,
   statistics.primary_method, statistics.software, statistics.significance_level,
   flow_steps,
   risks
5. flow_steps 和 risks 必须是字符串数组。
6. 先强调潜在漏洞和控制点，再给方案。
""".strip(),
        user_prompt=f"""
研究目标：
{goal}

研究假设：
{hypothesis or "未提供"}

参考文献上下文：
{context_clause}
""".strip(),
        temperature=0.3,
        max_tokens=1800,
    )

    variables = result.get("variables") if isinstance(result.get("variables"), dict) else {}
    sample = result.get("sample") if isinstance(result.get("sample"), dict) else {}
    statistics = result.get("statistics") if isinstance(result.get("statistics"), dict) else {}

    return {
        "goal": str(result.get("goal") or goal).strip(),
        "hypothesis": str(result.get("hypothesis") or hypothesis).strip(),
        "variables": {
            "independent": _normalize_list(variables.get("independent")),
            "dependent": _normalize_list(variables.get("dependent")),
            "controlled": _normalize_list(variables.get("controlled")),
        },
        "sample": {
            "size": str(sample.get("size") or "待根据效应量和功效分析估算"),
            "calculation_basis": str(sample.get("calculation_basis") or "输入信息不足，尚不能给出可信的样本量估算。"),
            "groups": _normalize_list(sample.get("groups")),
            "randomization": str(sample.get("randomization") or "建议固定随机种子并记录划分策略。"),
        },
        "statistics": {
            "primary_method": str(statistics.get("primary_method") or "需根据任务类型和评价指标进一步确定。"),
            "software": str(statistics.get("software") or "Python（NumPy / SciPy / Pandas）"),
            "significance_level": str(statistics.get("significance_level") or "0.05（如适用）"),
        },
        "flow_steps": _normalize_list(result.get("flow_steps")),
        "risks": _normalize_list(result.get("risks")),
    }
