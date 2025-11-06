from typing import Any, Optional, Union

from httpx import Client, Response, codes


from FoldingAtHomeControl.crypto import (
    base64_decode,
    derive_password,
    pkcs8_unwrap,
    salt_text,
)
from FoldingAtHomeControl.exceptions import (
    FoldingAtHomeControlAuthenticationFailed,
    FoldingAtHomeControlAuthenticationRequired,
)
from FoldingAtHomeControl.node_conn import MachNodeConnection


class APIConn:
    def __init__(self, session: Client):
        self.data: Any = {}
        self.session: Client = session
        self.session_id: bytes = b""
        self.account_data: dict[str, Union[str, dict[str, dict]]] = {}
        self.secret: bytes = b""
        self.nodes: dict[str, MachNodeConnection] = {}

    def login_with_passphrase(self, email: str, passphrase: str):
        if not self.session_id:
            [_, hash] = derive_password(passphrase.encode(), salt_text(email.encode()))
            results = self.get("login", {"email": email, "password": hash})
            if results.status_code in (codes.BAD_REQUEST, codes.UNAUTHORIZED):
                response = results.json()
                raise FoldingAtHomeControlAuthenticationFailed(response.get('error', 'Unknown issue'))
            self.cookies = results.cookies
            results_json = results.json()
            if results_json.get("group", {}).get("authenticated", False):
                self.session_id = results_json.get("id", None)
                self.uid = results_json.get("uid", None)

                self.update_account()
                return
            raise FoldingAtHomeControlAuthenticationRequired("Failed to login")

    def retrieve_secret(self, passphrase: str, text_for_salt: str):
        salted = salt_text(text_for_salt.encode())
        [key, hash] = derive_password(passphrase.encode(), salted)
        results = self.get("account/secret", data={"password": hash})
        secret = results.json()
        return pkcs8_unwrap(key, base64_decode(secret["secret"].encode()), salted)

    def get(self, path: str, data: Optional[dict] = None) -> Response:
        results = self.session.get(f"/{path}", params=data)
        return results

    def get_account(self) -> Any:
        if not self.data:
            self.update_account()
        return self.data

    def update_account(self) -> None:
        results = self.get("account")
        self.data = results.json()
        existing_nodes = list(self.nodes.keys())
        for mach in self.get_machines():
            if mach["id"] in existing_nodes:
                machine = self.nodes[mach["id"]]
                machine.name = str(mach["name"])
                machine.host = str(self.data["node"])
                existing_nodes.remove(mach["id"])
            else:
                self.nodes[mach["id"]] = MachNodeConnection(
                    str(mach["name"]), str(mach["id"]), str(self.data["node"])
                )
        for remaining_node in existing_nodes:
            self.nodes.pop(remaining_node)

    def get_machines(self) -> list[dict]:
        machines: list = self.data["machines"]
        return machines
