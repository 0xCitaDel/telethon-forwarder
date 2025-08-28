import asyncio
import logging
from typing import Any, Dict, List, Optional, Sequence, Union

from telethon import TelegramClient, errors, events
from telethon.tl.custom.message import Message

from src.models import AccountConfig
from src.router import Router
from src.utils import message_primary_text, normalize_chat_ref
from src.webhook import WebhookClient


class AccountWorker:

    def __init__(self, cfg: AccountConfig, http: WebhookClient):
        self.cfg = cfg
        self.http = http
        self.client: Optional[TelegramClient] = None
        self._log = logging.getLogger(f"Account[{cfg.name}]")
        self._source_entities: List[Any] = []
        self._target_cache: Dict[Union[int, str], Any] = {}

    async def start(self) -> None:
        self.client = TelegramClient(
            self.cfg.session, self.cfg.api_id, self.cfg.api_hash
        )
        await self.client.start()
        self._log.info("Logged in as %s", self.cfg.name)

        self._source_entities = []
        for s in self.cfg.sources:
            ent = await self.client.get_entity(normalize_chat_ref(s))
            self._source_entities.append(ent)
            self._log.info(
                "Listening source: %s",
                getattr(ent, "title", getattr(ent, "username", ent)),
            )

        # handlers
        self.client.add_event_handler(
            self._on_new_message, events.NewMessage(chats=self._source_entities)
        )

    async def run_forever(self) -> None:
        assert self.client is not None
        self._log.info("Ready. Waiting for messages...")
        await self.client.run_until_disconnected()

    async def stop(self) -> None:
        if self.client:
            await self.client.disconnect()

    async def resolve_target(self, target: Union[int, str]) -> Any:
        key = target
        if key in self._target_cache:
            return self._target_cache[key]
        assert self.client is not None
        ent = await self.client.get_entity(normalize_chat_ref(target))
        self._target_cache[key] = ent
        return ent

    async def _resilient_call(self, coro_func, *args, **kwargs):
        """Wrapper with waiting for Flood/SlowMode/RetryAfter."""
        while True:
            try:
                return await coro_func(*args, **kwargs)
            except errors.FloodWaitError as e:
                wait = int(getattr(e, "seconds", 0)) or 1
                self._log.warning("FloodWait %ss — waiting and will retry", wait)
                await asyncio.sleep(wait + 1)
            except errors.SlowModeWaitError as e:
                wait = int(getattr(e, "seconds", 0)) or 1
                self._log.warning("SlowMode %ss — waiting and will retry", wait)
                await asyncio.sleep(wait + 1)
            except errors.RetryAfter as e:
                wait = int(getattr(e, "seconds", 0)) or 1
                self._log.warning("RetryAfter %ss — waiting and will retry", wait)
                await asyncio.sleep(wait + 1)

    async def _send_copy_single(self, dest: Any, msg: Message) -> Optional[Message]:
        """
        Send a copy of a single message (without forward header).
        Media — via send_file, text — via send_message.
        """
        assert self.client is not None
        text = message_primary_text(msg)
        if msg.media:
            return await self._resilient_call(self.client.send_file, dest, msg.media, caption=text)
        elif text:
            return await self._resilient_call(self.client.send_message, dest, text)
        else:
            # Skip service/empty messages
            return None

    async def _send_forward_single(self, dest: Any, msg: Message) -> Any:
        """Forward a single message."""
        assert self.client is not None
        return await self._resilient_call(self.client.forward_messages, dest, msg)

    async def _maybe_webhook(
        self,
        route_name: str,
        text: str,
        matched: bool,
    ) -> None:

        """Send a webhook if settings are provided."""
        if not self.cfg.webhook:
            return

        wh = self.cfg.webhook

        # Filtering by routes
        if matched:
            if wh.routes and route_name not in wh.routes:
                return
        else:
            if not wh.send_unmatched:
                return

        payload = {
            "account_name": self.cfg.name,
            "route_name": route_name,
            "text": text,
        }
        await self.http.post_json(wh, payload)

    async def _on_new_message(self, event: events.NewMessage.Event) -> None:
        try:
            msg: Message = event.message

            if self.cfg.skip_own and getattr(msg, "out", False):
                return

            assert self.client is not None

            text = message_primary_text(msg)
            route, is_default = Router(self.cfg.routes, self.cfg.default_route).pick(text)

            if not is_default and route is not None:
                dest_ref = route.target
                mode = route.mode
                route_name = route.name
                matched = True
            else:
                dest_ref = self.cfg.default_route.default_target
                """
                if dest_ref is None:
                    await self._maybe_webhook(
                        "unmatched", text, msg, matched=False
                    )
                    return
                """
                mode = self.cfg.default_route.default_mode
                route_name = "default"
                matched = False

            dest = await self.resolve_target(dest_ref)

            if mode == "forward":
                await self._send_forward_single(dest, msg)
            else:
                await self._send_copy_single(dest, msg)

            await self._maybe_webhook(route_name, text, matched)

            self._log.info(
                "#%s -> %s [%s]",
                route_name,
                getattr(dest, "title", getattr(dest, "username", dest_ref)),
                mode,
            )

        except Exception as e:
            self._log.exception("Error handling message: %s", e)
