"""Passive allowlisted capture. Never redirects, replays, unlocks, or alters the game."""

from collections import OrderedDict
from hashlib import sha256
from urllib.parse import urlsplit

from exporter import save_snapshot
from protocol import envelope, unpack_stream, expand

API_HOST = "lb-api.wds-stellarium.com"


class AccountCapture:
    def __init__(self, output, report=print):
        self.output, self.report = output, report
        self.bridges = OrderedDict()
        self.saved = set()

    def response(self, flow):
        # Do not trust a client-supplied Host header to identify the remote server.
        if flow.request.host.lower() != API_HOST or not flow.response:
            return
        path = urlsplit(flow.request.url).path
        if path not in ("/api/Account/Authenticate", "/api/data/user"):
            return
        if flow.response.status_code != 200:
            self.report(
                "Game account request failed. No successful snapshot saved from this response."
            )
            return
        try:
            body = flow.response.content
            if path == "/api/Account/Authenticate" and flow.request.method == "POST":
                payload = [expand(v) for v in unpack_stream(flow.request.content)][0]
                token = envelope(body)[1][0]
                login = payload[0]
                if (
                    not isinstance(token, str)
                    or not isinstance(login, str)
                    or not login
                ):
                    raise ValueError("Missing authentication fields")
                # Only hashes stay in memory; raw requests, headers and tokens are never written.
                self.bridges[sha256(token.encode()).hexdigest()] = sha256(
                    login.encode()
                ).hexdigest()
                if len(self.bridges) > 32:
                    self.bridges.popitem(last=False)
                self.report(
                    "Game login observed. Waiting for the full account snapshot..."
                )
            elif path == "/api/data/user" and flow.request.method == "GET":
                auth = flow.request.headers.get("Authorization", "")
                token = auth[7:] if auth.lower().startswith("bearer ") else ""
                bridge = (
                    self.bridges.get(sha256(token.encode()).hexdigest())
                    if token
                    else None
                )
                identity = (sha256(body).hexdigest(), bridge)
                if identity in self.saved:
                    return
                dest, manifest = save_snapshot(
                    self.output,
                    body,
                    bridge,
                    flow.request.headers.get("X-Client-Version"),
                )
                self.saved.add(identity)
                counts = manifest["summary"]
                self.report(
                    f"ACCOUNT SAVED: {counts['Character']} actors, {counts['Poster']} posters; {manifest['entries']} records.\n{dest}"
                )
                if not bridge:
                    self.report(
                        "Inventory backup is valid. For automatic login matching, fully close and reopen the game once while capture is running."
                    )
                self.report(
                    "Keep this ZIP private and copy it somewhere safe. Stop capture after the game reaches home."
                )
        except Exception as exc:
            # Exception strings may contain private input; only report the class.
            self.report(
                f"Account export could not be validated ({type(exc).__name__}). No success claimed. Keep the game open and consult troubleshooting."
            )
