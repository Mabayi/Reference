from __future__ import annotations

import json
from typing import Any, AsyncGenerator

import httpx

from config.settings import settings
from repositories import token_repo
from utils.auth_utils import get_current_user_id


class LLMServiceError(Exception):
    """统一的模型服务异常。"""


class LLMConfigurationError(LLMServiceError):
    """模型配置缺失。"""


def _get_bound_api_key(user_id: int | None = None) -> str:
    resolved_user_id = user_id if user_id is not None else get_current_user_id()
    if resolved_user_id is None:
        return ""
    account = token_repo.get_deepseek_api_key(resolved_user_id, include_secret=True)
    if not account:
        return ""
    return str(account.get("api_key") or "").strip()


def _resolve_api_key(api_key: str | None = None, user_id: int | None = None) -> str:
    resolved_user_id = user_id if user_id is not None else get_current_user_id()
    if resolved_user_id is not None:
        ok, message = token_repo.validate_api_access(resolved_user_id)
        if not ok:
            raise LLMConfigurationError(message)

    resolved = (api_key or "").strip() or _get_bound_api_key(resolved_user_id) or settings.DEEPSEEK_API_KEY
    if not resolved:
        raise LLMConfigurationError("系统 API Key 未配置，请联系管理员处理。")
    return resolved


def ensure_llm_configured(api_key: str | None = None) -> None:
    _resolve_api_key(api_key)


def _build_headers(api_key: str | None = None, user_id: int | None = None) -> dict[str, str]:
    resolved_api_key = _resolve_api_key(api_key, user_id)
    return {
        "Authorization": f"Bearer {resolved_api_key}",
        "Content-Type": "application/json",
    }


def _record_usage(payload: dict[str, Any], description: str, user_id: int | None = None) -> None:
    resolved_user_id = user_id if user_id is not None else get_current_user_id()
    if resolved_user_id is None:
        return
    usage = payload.get("usage") or {}
    try:
        total_tokens = int(usage.get("total_tokens") or 0)
    except (TypeError, ValueError):
        total_tokens = 0
    if total_tokens > 0:
        if token_repo.get_deepseek_api_key(resolved_user_id):
            return
        token_repo.record_api_usage(resolved_user_id, total_tokens, description)


def _extract_text_from_response(payload: dict[str, Any]) -> str:
    choices = payload.get("choices") or []
    if not choices:
        raise LLMServiceError("模型未返回可用内容。")

    message = choices[0].get("message") or {}
    content = message.get("content", "")
    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text", "")))
        return "\n".join(part for part in parts if part).strip()

    raise LLMServiceError("模型返回内容格式异常。")


async def chat_completion(
    *,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.3,
    max_tokens: int = 2048,
    model: str | None = None,
    response_format: dict[str, Any] | None = None,
    api_key: str | None = None,
    usage_user_id: int | None = None,
) -> str:
    return await chat_completion_from_messages(
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
        model=model,
        response_format=response_format,
        api_key=api_key,
        usage_user_id=usage_user_id,
    )


async def chat_completion_from_messages(
    *,
    messages: list[dict[str, Any]],
    temperature: float = 0.3,
    max_tokens: int = 2048,
    model: str | None = None,
    response_format: dict[str, Any] | None = None,
    api_key: str | None = None,
    usage_user_id: int | None = None,
) -> str:
    payload = {
        "model": model or settings.MODEL_NAME,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if response_format is not None:
        payload["response_format"] = response_format

    try:
        async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT) as client:
            response = await client.post(
                f"{settings.DEEPSEEK_BASE_URL}/chat/completions",
                headers=_build_headers(api_key, usage_user_id),
                json=payload,
            )
            response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        detail = exc.response.text.strip()
        raise LLMServiceError(f"DeepSeek API 请求失败：HTTP {exc.response.status_code}，{detail}") from exc
    except httpx.HTTPError as exc:
        raise LLMServiceError(f"DeepSeek API 网络请求失败：{exc}") from exc

    data = response.json()
    _record_usage(data, "DeepSeek API 调用", usage_user_id)
    return _extract_text_from_response(data)


async def json_completion(
    *,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.2,
    max_tokens: int = 2048,
    model: str | None = None,
    api_key: str | None = None,
    usage_user_id: int | None = None,
) -> dict[str, Any]:
    content = await chat_completion(
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        temperature=temperature,
        max_tokens=max_tokens,
        model=model,
        response_format={"type": "json_object"},
        api_key=api_key,
        usage_user_id=usage_user_id,
    )
    normalized = content.strip()

    if normalized.startswith("```"):
        normalized = normalized.strip("`")
        if normalized.startswith("json"):
            normalized = normalized[4:].strip()

    try:
        return json.loads(normalized)
    except json.JSONDecodeError as exc:
        raise LLMServiceError(f"模型未返回合法 JSON：{content[:300]}") from exc


async def json_completion_from_messages(
    *,
    messages: list[dict[str, Any]],
    temperature: float = 0.2,
    max_tokens: int = 2048,
    model: str | None = None,
    api_key: str | None = None,
    usage_user_id: int | None = None,
) -> dict[str, Any]:
    content = await chat_completion_from_messages(
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        model=model,
        response_format={"type": "json_object"},
        api_key=api_key,
        usage_user_id=usage_user_id,
    )
    normalized = content.strip()
    if normalized.startswith("```"):
        normalized = normalized.strip("`")
        if normalized.startswith("json"):
            normalized = normalized[4:].strip()

    try:
        return json.loads(normalized)
    except json.JSONDecodeError as exc:
        raise LLMServiceError(f"模型未返回合法 JSON：{content[:300]}") from exc


async def stream_chat_completion(
    *,
    system_prompt: str,
    user_prompt: str,
    temperature: float = 0.3,
    max_tokens: int = 2048,
    model: str | None = None,
    api_key: str | None = None,
    usage_user_id: int | None = None,
) -> AsyncGenerator[str, None]:
    payload = {
        "model": model or settings.MODEL_NAME,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": True,
        "stream_options": {"include_usage": True},
    }

    try:
        async with httpx.AsyncClient(timeout=settings.REQUEST_TIMEOUT) as client:
            async with client.stream(
                "POST",
                f"{settings.DEEPSEEK_BASE_URL}/chat/completions",
                headers=_build_headers(api_key, usage_user_id),
                json=payload,
            ) as response:
                if response.status_code >= 400:
                    detail = await response.aread()
                    raise LLMServiceError(
                        f"DeepSeek API 请求失败：HTTP {response.status_code}，{detail.decode('utf-8', errors='ignore')}"
                    )

                async for line in response.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue

                    data = line[5:].strip()
                    if not data or data == "[DONE]":
                        continue

                    try:
                        event = json.loads(data)
                    except json.JSONDecodeError:
                        continue

                    if event.get("usage"):
                        _record_usage(event, "DeepSeek API 流式调用", usage_user_id)

                    choices = event.get("choices") or []
                    if not choices:
                        continue

                    delta = choices[0].get("delta") or {}
                    content = delta.get("content")
                    if isinstance(content, str) and content:
                        yield content
                    elif isinstance(content, list):
                        for item in content:
                            if isinstance(item, dict) and item.get("type") == "text":
                                text = str(item.get("text", ""))
                                if text:
                                    yield text
    except httpx.HTTPError as exc:
        raise LLMServiceError(f"DeepSeek API 网络请求失败：{exc}") from exc
