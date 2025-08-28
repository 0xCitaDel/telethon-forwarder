from __future__ import annotations

from typing import Union

from telethon.tl.custom.message import Message


def normalize_chat_ref(ref: Union[int, str]) -> Union[int, str]:
    if isinstance(ref, str):
        ref = ref.strip()
        if ref.startswith("https://t.me/"):
            ref = ref[len("https://t.me/") :]
        if ref.startswith("@"):
            ref = ref[1:]
    return ref


def message_primary_text(msg: Message) -> str:
    return (msg.message or "").strip()
