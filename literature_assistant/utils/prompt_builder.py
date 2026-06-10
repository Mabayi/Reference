"""
Prompt 模板集中管理
所有 AI 调用的提示词统一在此维护，禁止在 service 中硬编码 Prompt 字符串。
"""


def build_metadata_extraction_prompt(text: str) -> str:
    """构建文献元数据提取 Prompt"""
    return f"""请从以下学术论文文本中提取结构化信息，以 JSON 格式返回：
- title: 论文标题
- authors: 作者列表
- abstract: 摘要
- keywords: 关键词列表
- methods: 研究方法
- conclusions: 主要结论
- innovations: 创新点

论文文本：
{text}
"""


def build_survey_prompt(context: str, topic: str) -> str:
    """构建文献综述生成 Prompt"""
    return f"""基于以下文献内容，围绕"{topic}"主题生成一篇结构化的文献综述。
要求：
1. 包含引言、主体（按主题/时间线组织）、总结与展望
2. 对比不同研究的方法和结论
3. 指出研究空白和未来方向

参考文献内容：
{context}
"""


def build_experiment_design_prompt(research_question: str) -> str:
    """构建实验方案设计 Prompt"""
    return f"""请针对以下研究问题，逐步推理并设计一个完整的实验方案：

研究问题：{research_question}

请包含以下内容：
1. 实验目的
2. 自变量与因变量
3. 控制变量
4. 样本量与抽样方法
5. 实验流程（步骤）
6. 统计分析方法
7. 预期结果
"""


def build_writing_polish_prompt(text: str) -> str:
    """构建学术润色 Prompt"""
    return f"""请对以下学术文本进行润色，提升其学术性和流畅度，保持原意不变：

{text}
"""


def build_code_generation_prompt(task: str, language: str = "Python") -> str:
    """构建代码生成 Prompt"""
    return f"""请生成用于以下数据分析任务的 {language} 代码：

任务描述：{task}

要求：
1. 代码完整可运行
2. 包含必要的注释
3. 使用常用科研库（如 pandas、numpy、scipy、matplotlib）
"""
