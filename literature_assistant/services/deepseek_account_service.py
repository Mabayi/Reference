from __future__ import annotations

from typing import Any

import httpx

from config.settings import settings


class DeepSeekAccountError(Exception):
    """DeepSeek 账户校验异常。"""


def _normalize_balance(payload: dict[str, Any]) -> dict[str, Any]:
    balance_infos = payload.get("balance_infos")
    if not isinstance(balance_infos, list):
        raise DeepSeekAccountError("DeepSeek 余额接口返回格式异常")

    normalized_infos: list[dict[str, str]] = []
    for item in balance_infos:
        if not isinstance(item, dict):
            continue
        normalized_infos.append(
            {
                "currency": str(item.get("currency") or ""),
                "total_balance": str(item.get("total_balance") or "0"),
                "granted_balance": str(item.get("granted_balance") or "0"),
                "topped_up_balance": str(item.get("topped_up_balance") or "0"),
            }
        )

    return {
        "is_available": bool(payload.get("is_available")),
        "balance_infos": normalized_infos,
    }


async def fetch_user_balance(api_key: str) -> dict[str, Any]:
    clean_key = api_key.strip()
    if not clean_key:
        raise DeepSeekAccountError("请填写 DeepSeek API Key")
    if not clean_key.startswith("sk-"):
        raise DeepSeekAccountError("API Key 格式不正确，应以 sk- 开头")

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(
                f"{settings.DEEPSEEK_BASE_URL}/user/balance",
                headers={"Authorization": f"Bearer {clean_key}"},
            )
    except httpx.HTTPError as exc:
        raise DeepSeekAccountError(f"无法连接 DeepSeek 余额接口：{exc}") from exc

    if response.status_code in {401, 403}:
        raise DeepSeekAccountError("DeepSeek API Key 无效或没有权限")
    if response.status_code >= 400:
        detail = response.text.strip()
        raise DeepSeekAccountError(f"DeepSeek 余额接口请求失败：HTTP {response.status_code}，{detail}")

    try:
        payload = response.json()
    except ValueError as exc:
        raise DeepSeekAccountError("DeepSeek 余额接口未返回合法 JSON") from exc

    if not isinstance(payload, dict):
        raise DeepSeekAccountError("DeepSeek 余额接口返回格式异常")
    return _normalize_balance(payload)
