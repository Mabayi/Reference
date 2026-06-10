from __future__ import annotations

import base64
import mimetypes
from pathlib import Path

from config.settings import settings
from services.llm_service import LLMServiceError, json_completion_from_messages


def _to_data_url(image_path: str) -> str:
    mime_type, _ = mimetypes.guess_type(image_path)
    mime = mime_type or "image/png"
    data = Path(image_path).read_bytes()
    encoded = base64.b64encode(data).decode("utf-8")
    return f"data:{mime};base64,{encoded}"


async def analyze_chart(image_path: str) -> dict:
    data_url = _to_data_url(image_path)
    try:
        result = await json_completion_from_messages(
            messages=[
                {
                    "role": "system",
                    "content": (
                        "你是一名严谨的数据图表分析助手。"
                        "请基于图像内容返回 JSON，字段必须包含："
                        "chart_type, trend, key_findings, statistics, paragraph, significance。"
                        "如果图片内容无法可靠识别，不要编造具体数值，应明确写“无法可靠识别”。"
                        "key_findings 必须是字符串数组，statistics 必须是对象。"
                    ),
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "请分析这张图表，输出中文 JSON。"},
                        {"type": "image_url", "image_url": {"url": data_url}},
                    ],
                },
            ],
            temperature=0.2,
            max_tokens=1500,
            model=settings.VISION_MODEL_NAME or settings.MODEL_NAME,
        )
    except LLMServiceError as exc:
        raise LLMServiceError(
            "图表解析失败。当前 DeepSeek 接口文档未明确列出图像输入能力，"
            f"本次请求返回：{exc}"
        ) from exc

    return {
        "chart_type": str(result.get("chart_type") or "未识别"),
        "trend": str(result.get("trend") or "未识别"),
        "key_findings": [str(item) for item in (result.get("key_findings") or []) if str(item).strip()],
        "statistics": result.get("statistics") if isinstance(result.get("statistics"), dict) else {},
        "paragraph": str(result.get("paragraph") or ""),
        "significance": str(result.get("significance") or ""),
    }
