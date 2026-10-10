"""Minimal async client for verified Bale Bot API operations."""
from dataclasses import dataclass
import httpx

BALE_API_BASE = "https://tapi.bale.ai/bot"

@dataclass
class BaleAPIError(Exception):
    code: str
    message: str
    retryable: bool = False

class BaleClient:
    def __init__(self, token: str, timeout_seconds: float = 10.0):
        if not token or len(token) < 10:
            raise ValueError("A Bale bot token is required")
        self._token = token
        self._timeout = timeout_seconds

    async def _post(self, method: str, payload: dict | None = None, timeout_seconds: float | None = None) -> dict:
        url = f"{BALE_API_BASE}{self._token}/{method}"
        try:
            async with httpx.AsyncClient(timeout=timeout_seconds or self._timeout) as client:
                response = await client.post(url, json=payload or {})
        except httpx.TimeoutException as exc:
            raise BaleAPIError("TIMEOUT", "Bale API request timed out", True) from exc
        except httpx.HTTPError as exc:
            raise BaleAPIError("NETWORK_ERROR", "Bale API is unavailable", True) from exc
        try:
            data = response.json()
        except ValueError as exc:
            raise BaleAPIError("INVALID_RESPONSE", "Bale returned a non-JSON response", False) from exc
        if response.status_code >= 500:
            raise BaleAPIError("PROVIDER_ERROR", "Bale service error", True)
        if not response.is_success or not isinstance(data, dict) or data.get("ok") is not True:
            code = str(data.get("error_code", "REQUEST_REJECTED")) if isinstance(data, dict) else "REQUEST_REJECTED"
            raise BaleAPIError(code, "Bale rejected the request", False)
        return data.get("result") or {}

    async def get_me(self) -> dict:
        return await self._post("getMe")

    async def send_text(self, chat_id: str | int, text: str, reply_markup: dict | None = None) -> dict:
        if not text or len(text) > 4096:
            raise ValueError("Message text must contain 1 to 4096 characters")
        if not str(chat_id).strip():
            raise ValueError("A verified Bale chat ID is required")
        payload = {"chat_id": chat_id, "text": text}
        if reply_markup is not None:
            payload["reply_markup"] = reply_markup
        return await self._post("sendMessage", payload)

    async def get_updates(self, offset: int | None = None, timeout_seconds: int = 20) -> list[dict]:
        # Long polling is used for local/desktop deployments where a public HTTPS webhook is unavailable.
        payload = {"timeout": max(0, min(int(timeout_seconds), 25))}
        if offset is not None:
            payload["offset"] = offset
        result = await self._post("getUpdates", payload, timeout_seconds=max(self._timeout, payload["timeout"] + 5))
        return result if isinstance(result, list) else []
