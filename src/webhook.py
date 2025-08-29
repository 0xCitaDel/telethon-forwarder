from __future__ import annotations
import logging
from typing import Any, Dict
from aiohttp import ClientSession
from src.models import WebhookConfig

class WebhookClient:

    def __init__(self, session: ClientSession):
        self._session = session
        self._log = logging.getLogger("Webhook")

    async def post_json(self, cfg: WebhookConfig, payload: Dict[str, Any]) -> None:
        headers = {
            "Authorization": f"Bearer {cfg.token}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        try:
            async with self._session.post(cfg.url, json=payload, headers=headers, timeout=cfg.timeout) as resp:
                if resp.status >= 400:
                    text = await resp.text()
                    self._log.warning("Webhook HTTP %s: %s", resp.status, text[:500])
                else:
                    self._log.info("Webhook sent: %s", payload.get("route_name"))
        except Exception as e:
            self._log.error("Webhook error: %s", e)

