"""Get Information on your Folding@Home Clients."""

import asyncio
from contextlib import asynccontextmanager
from cryptography.hazmat.primitives.asymmetric import rsa
import datetime
import json


import httpx
from httpx_ws import AsyncWebSocketSession, aconnect_ws

from FoldingAtHomeControl.api_conn import APIConn
from FoldingAtHomeControl.crypto import (
    base64_decode,
    base64_encode,
    decrypt_rsa_oaep,
    get_pubkey_id,
    get_signature,
    load_public_key,
    verify,
)
from FoldingAtHomeControl.node_conn import MachNodeConnection
from FoldingAtHomeControl.util import get_random_chars, json_dump_payload

import logging
from typing import Callable, Optional
from uuid import uuid4

from .const import (
    COMMAND_PAUSE,
    COMMAND_UNPAUSE,
    PowerLevel,
)
from .exceptions import (
    FoldingAtHomeControlAuthenticationRequired,
    FoldingAtHomeControlConnectionFailed,
    FoldingAtHomeControlNotConnected,
)

from cryptography.hazmat.primitives.serialization import (
    load_der_private_key,
    load_der_public_key,
    load_pem_private_key
    
)


_LOGGER = logging.getLogger(__name__)

RETRY_WAIT_IN_SECONDS = 10
MAX_AUTHENTICATION_MESSAGE_COUNT = 5
CONNECT_TIMEOUT_IN_SECONDS = 5

HTTPS_HOST = "https://api.foldingathome.org"
WSS_HOST = "wss://{host}/{path}"
WS_ORIGIN = "https://v8-4.foldingathome.org"
STD_WS_HEADERS = {
    "Pragma": "no-cache",
    "Cache-Control": "no-cache",
    "Origin": "https://v8-4.foldingathome.org",
    "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br, zstd",
}


class FoldingAtHomeController:
    """Connect to Folding@Home Client."""

    def __init__(
        self,
        email: str,
        passphrase: str,
    ) -> None:
        """Initialize connection data."""

        self.email = email
        self.passphrase = passphrase
        self.private_key: Optional[rsa.RSAPrivateKey] = None
        self.public_key: Optional[rsa.RSAPublicKey] = None
        self.is_connected: bool = False
        self._callbacks: dict = {}
        self.ws_session_id: str = ""
        self.cmd_queue: asyncio.Queue = asyncio.Queue()

        self._api_connection: Optional[APIConn] = None

    @property
    def nodes(self) -> dict[str, MachNodeConnection]:
        return self._api_connection.nodes if self._api_connection else {}

    async def start(self) -> None:
        """Start listening to the socket."""
        with httpx.Client(base_url=HTTPS_HOST) as session:
            self._api_connection = APIConn(session)
            self._api_connection.login_with_passphrase(self.email, self.passphrase)
            if not self._api_connection.session_id:
                raise FoldingAtHomeControlAuthenticationRequired(
                    "Incorrect Login details"
                )
            self.secret: bytes = self._api_connection.retrieve_secret(
                self.passphrase, self.email
            )
            if not self.secret:
                raise FoldingAtHomeControlAuthenticationRequired(
                    "Not able to fetch secret for connection"
                )
            
            private_key = None

            if self.secret.startswith(b"MII"):
              try:
                private_key = load_der_private_key(base64_decode(self.secret), None)
              except ValueError as e:
                print(f"Failed to load secret as private key using DER format. secret starts with {self.secret[0:5]}")    
            elif self.secret.startswith(b"----"):
              try:
                  private_key = load_pem_private_key(self.secret, None)
              except ValueError as e:
                print(f"Failed to load secret as private key using PEM. secret starts with {self.secret[0:5]}")
            
            assert isinstance(private_key, rsa.RSAPrivateKey)
            self.private_key = private_key

            public_key = load_der_public_key(
                base64_decode(self._api_connection.data["pubkey"].encode()), None
            )
            assert isinstance(public_key, rsa.RSAPublicKey)
            self.public_key = public_key

            self.id = get_pubkey_id(self.public_key)
            await self.connect_service()

    async def receiving_loop(self, ws: AsyncWebSocketSession):
        loop = asyncio.get_running_loop()
        try:
            while self.is_connected:
                msg = await ws.receive_json()
                if "type" not in msg:
                    continue
                if msg["type"] == "connect":
                    # Adding a machine
                    loop.create_task(self.handle_connect(ws, msg["client"]))
                elif msg["type"] == "message":
                    # general message
                    loop.create_task(self.handle_message(ws, msg))
                elif msg["type"] == "broadcast":
                    print("broadcast: ", msg.get("payload"))
                else:
                    print("unhandled: ", msg.get("payload"))

        except httpx.StreamClosed:
            # self.on_disconnect() call with func
            pass

    async def sending_loop(self, ws: AsyncWebSocketSession, cmd_queue: asyncio.Queue):
        while self.is_connected:
            instruction = await cmd_queue.get()
            try:
                if instruction["id"] in self.nodes:
                    self.nodes[instruction["id"]].send_cmd(
                        ws, self.private_key, instruction["cmd"], instruction["state"]
                    )
            finally:
                cmd_queue.task_done()

    async def connect_service(self) -> None:
        loop = asyncio.get_running_loop()
        recv_task = None
        sending_task = None
        if not self._api_connection:
            raise FoldingAtHomeControlNotConnected
        try:
            async with self.get_ws_connection(self._api_connection.data["node"]) as ws:
                await self.login_ws(ws)
                recv_task = loop.create_task(self.receiving_loop(ws))
                sending_task = loop.create_task(self.sending_loop(ws, self.cmd_queue))
                await asyncio.gather(recv_task, sending_task)
        finally:
            if recv_task:
                recv_task.cancel()
            if sending_task:
                sending_task.cancel()
            raise FoldingAtHomeControlNotConnected

    def new_session_id(self) -> str:
        return base64_encode(get_random_chars(12).encode(), True).decode()

    async def login_ws(self, ws: AsyncWebSocketSession):
        self.ws_session_id = self.new_session_id()
        if not self._api_connection:
            raise FoldingAtHomeControlNotConnected
        payload = {
            "time": datetime.datetime.now().isoformat(),
            "session": self.ws_session_id,
        }
        logging.info(f"Logging in with session {payload['session']}")
        sig = get_signature(self.private_key, json.dumps(payload).encode())
        ws_send = json.dumps(
            {
                "type": "login",
                "payload": payload,
                "pubkey": self._api_connection.data["pubkey"],
                "signature": sig.decode(),
            }
        )
        return await ws.send_text(ws_send)

    @asynccontextmanager
    async def get_ws_connection(self, host):
        self.is_connected = True
        try:
            async with aconnect_ws(
                "wss://" + host + "/ws/account", headers=STD_WS_HEADERS
            ) as ws:
                yield ws
        except httpx.StreamClosed:
            self.is_connected = False
            raise FoldingAtHomeControlNotConnected(
                "WebSocket Connection Closed"
            ) from None

    async def handle_connect(self, ws: AsyncWebSocketSession, msg: dict):
        """Handles initial connection and subscription to a machine node using websockets"""
        if not self._api_connection:
            raise FoldingAtHomeControlNotConnected("No API Connection")
        if not self.private_key:
            raise FoldingAtHomeControlConnectionFailed("No Private key found")
        async with asyncio.timeout(10):
            signature = msg["signature"].encode()
            mach_pubkey = load_public_key(msg["pubkey"].encode())
            assert isinstance(mach_pubkey, rsa.RSAPublicKey)
            mach_id = get_pubkey_id(mach_pubkey)

            verify(mach_pubkey, signature, json_dump_payload(msg["payload"]).encode())

            account = msg["payload"]["account"]
            if account != self.id:
                print(
                    "ERROR ACCOUNT ID MISMATCH",
                    self._api_connection.session_id,
                    self.ws_session_id,
                    account,
                )

            enc_mach_key = base64_decode(msg["payload"]["key"].encode())
            mach_key = decrypt_rsa_oaep(self.private_key, enc_mach_key)
            node = self.nodes.get(mach_id, None)
            if node is None:
                self._api_connection.update_account()
                node = self.nodes.get(mach_id, None)
            if node is not None:
                logging.info("Adding machine connection")
                return await node.initialize(mach_key, ws, self.ws_session_id)

    async def handle_message(self, ws: AsyncWebSocketSession, msg: dict):
        async with asyncio.timeout(10):
            mach_id = msg["client"]
            machine = self.nodes.get(mach_id, None)
            if machine:
                message = machine.receive_message(msg, self.ws_session_id)
                return await self._call_callbacks_async("message", message)

    def on_disconnect(self, func: Callable) -> None:
        """Register a method to be executed when the connection is disconnected."""
        self._on_disconnect = func

    def register_callback(self, callback: Callable) -> Callable:
        """Register a callback for received data."""
        uuid = uuid4()
        self._callbacks[uuid] = callback
        _LOGGER.debug("Registered callback")

        def remove_callback() -> None:
            """Remove callback."""
            del self._callbacks[uuid]

        return remove_callback

    async def unsubscribe_all_async(self) -> None:
        """Unsubscribe all subscriptions."""
        raise NotImplementedError
        # await self.send_command_async(UNSUBSCRIBE_ALL_COMMAND)

    async def request_work_server_assignment_async(self) -> None:
        """Request work server assignment from the assignmentserver."""
        raise NotImplementedError
        # await self.send_command_async(COMMAND_REQUEST_WORKSERVER_ASSIGNMENT)

    async def set_power_level_async(self, power_level: PowerLevel) -> None:
        """Set the power level."""
        raise NotImplementedError
        # await self.send_command_async(f"{COMMAND_POWER} {power_level.value}")

    async def pause_slot_async(self, machine_id: str) -> None:
        """Pause folding on a machine."""
        await self.send_command_async(machine_id, "state", COMMAND_PAUSE)

    async def pause_all_slots_async(self) -> None:
        """Pause folding on all machines."""
        for id, _ in self.nodes.items():
            await self.send_command_async(id, "state", COMMAND_PAUSE)

    async def unpause_slot_async(self, machine_id: str) -> None:
        """Resume folding on a machine."""
        await self.send_command_async(machine_id, "state", COMMAND_UNPAUSE)

    async def unpause_all_slots_async(self) -> None:
        """Resume folding on all machines."""
        for id, _ in self.nodes.items():
            await self.send_command_async(id, "state", COMMAND_UNPAUSE)

    async def finish_slot_async(self, machine_id: str) -> None:
        """Finish folding on a machine."""
        await self.send_command_async(machine_id, "state", COMMAND_UNPAUSE)

    async def finish_all_slots_async(self) -> None:
        """Finish folding on all machines."""
        for id, _ in self.nodes.items():
            await self.send_command_async(id, "state", COMMAND_UNPAUSE)

    async def shutdown(self) -> None:
        """Shutdown the client."""
        raise NotImplementedError
        # await self.send_command_async(COMMAND_SHUTDOWN)

    async def _call_callbacks_async(self, message_type: str, message: dict) -> None:
        """Pass the message to all callbacks."""
        for callback in self._callbacks.values():
            if asyncio.iscoroutinefunction(callback):
                await callback(message_type, message)
            else:
                callback(message_type, message)

    async def send_command_async(
        self, machine_id: str, command: str, state: str
    ) -> None:
        """Send a command."""
        if not self.is_connected:
            raise FoldingAtHomeControlNotConnected
        if machine_id not in self.nodes:
            raise FoldingAtHomeControlConnectionFailed("Machine ID does not exist")
        await self.cmd_queue.put({"id": machine_id, "cmd": command, "state": state})
