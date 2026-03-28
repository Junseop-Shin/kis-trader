"""
Fire-and-forget event tracking to devops-monitor ingestor.
All sends are background tasks — never blocks the request.
"""
import asyncio
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

SERVICE_ID = "kis-trader"
_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _client
    if _client is None:
        _client = httpx.AsyncClient(timeout=3.0)
    return _client


async def _send(ingestor_url: str, event_type: str, user_id: int | None, metadata: dict[str, Any]) -> None:
    if not ingestor_url:
        return
    try:
        await _get_client().post(
            f"{ingestor_url}/v1/events",
            json={"event_type": event_type, "service_id": SERVICE_ID, "user_id": user_id, "metadata": metadata},
        )
    except Exception as e:
        logger.debug("Analytics send failed (non-critical): %s", e)


def track(ingestor_url: str, event_type: str, user_id: int | None = None, **metadata: Any) -> None:
    """Schedule a fire-and-forget analytics event. Never raises."""
    asyncio.create_task(_send(ingestor_url, event_type, user_id, metadata))
