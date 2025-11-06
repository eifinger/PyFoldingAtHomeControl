import asyncio
import datetime
import json
from typing import Optional

from httpx_ws import AsyncWebSocketSession

from FoldingAtHomeControl.crypto import (
    decompress_payload,
    decrypt_aes,
    encrypt_aes,
    get_signature,
)
from FoldingAtHomeControl.util import json_dump_payload


class MachNodeConnection:

    def __init__(self, name: str, machine_id: str, host: str):
        self.host = host
        self.name = name
        self.machine_id = machine_id
        self.mach_key: Optional[bytes] = None  # AES Secret given on initialize
        self.ivs: dict[bytes, bool] = {}

    async def initialize(
        self, key: bytes, ws: AsyncWebSocketSession, session_id: str
    ) -> None:
        self.mach_key = key
        return await self.open_session(ws, session_id)

    async def open_session(self, ws: AsyncWebSocketSession, session_id: str) -> None:
        return await self.send_ws(ws, {"type": "session-open", "session": session_id})

    async def send_ws(self, ws: AsyncWebSocketSession, msg: dict) -> None:
        msg_bytes = json_dump_payload(msg).encode()
        [enc_payload, iv] = encrypt_aes(self.mach_key, msg_bytes)
        self.ivs[iv] = True
        message = json_dump_payload(
            {
                "type": "message",
                "id": self.machine_id,
                "iv": iv.decode(),
                "payload": enc_payload.decode(),
            }
        )
        await ws.send_text(message)

    def receive_message(self, msg: dict, session_id: str) -> dict:
        return self.extract_message(msg, session_id)

    def extract_message(self, message: dict, session_id: str) -> dict:
        iv = message["iv"]
        if self.ivs.get(iv, None):
            raise Exception("Can't use IV again")
        if 1e6 < len(self.ivs):
            raise Exception("Too many IV's")
        self.ivs[iv] = True

        payload = decrypt_aes(self.mach_key, message["payload"].encode(), iv.encode())

        if message.get("compression", None):
            payload = decompress_payload(payload, message.get("compression", "gzip"))

        payload_json: dict = json.loads(payload.decode())

        if payload_json["session"] != session_id:
            raise Exception(f"Message not for this session, payload sessionid: {payload_json["session"]} with current session_id: {session_id}")

        return payload_json

    @classmethod
    async def _send_cmd(cls, ws: AsyncWebSocketSession, message: str):
        return await ws.send_text(message)

    def send_cmd(self, ws: AsyncWebSocketSession, key, cmd: str, state: str):
        payload = {
            "cmd": cmd,
            "state": state,
            "time": datetime.datetime.now().isoformat(),
        }
        payload_str = json_dump_payload(payload)
        signature = get_signature(key, payload_str.encode())
        message = json.dumps(
            {"payload": payload, "signature": signature.decode(), "type": "broadcast"}
        )
        asyncio.create_task(self._send_cmd(ws, message))
