"""Mermaid 流程图语法生成工具"""


def generate_flowchart(steps: list[str]) -> str:
    """根据步骤列表生成 Mermaid 流程图语法"""
    lines = ["graph TD"]
    for i, step in enumerate(steps):
        node_id = f"S{i}"
        lines.append(f"    {node_id}[{step}]")
        if i > 0:
            prev_id = f"S{i-1}"
            lines.append(f"    {prev_id} --> {node_id}")
    return "\n".join(lines)
