"""Selektive gzip-Kompression für Textantworten.

Starlettes ``GZipMiddleware`` komprimiert jede Antwort oberhalb einer
Mindestgröße. Für diese Anwendung ist das falsch: der weit überwiegende Teil
des ausgehenden Volumens sind PDFs, PNGs, DOCX und XLSX — allesamt intern
bereits komprimiert. Sie erneut durch gzip zu schicken kostet spürbar CPU und
bringt typisch unter 2 % Ersparnis; bei einer 100-MB-Datei sind das mehrere
Sekunden Rechenzeit pro Download.

Diese Middleware komprimiert deshalb nur Antworten mit textartigem
Content-Type (JSON, Text, CSV, XML, SVG, JavaScript). Dort ist der Gewinn
groß: extrahierter PDF-Text und Qualitätsberichte schrumpfen auf etwa ein
Fünftel.
"""

import gzip
import io

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

_TEXTUAL_PREFIXES = (
    "application/json",
    "application/problem+json",
    "application/xml",
    "application/javascript",
    "text/",
    "image/svg+xml",
)


def _is_textual(content_type: str) -> bool:
    ct = content_type.split(";", 1)[0].strip().lower()
    return ct.startswith(_TEXTUAL_PREFIXES)


class JsonGZipMiddleware:
    """gzip nur für Textantworten, nur bei passendem Accept-Encoding."""

    def __init__(self, app: ASGIApp, minimum_size: int = 1024) -> None:
        self.app = app
        self.minimum_size = minimum_size

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        accept = Headers(scope=scope).get("accept-encoding", "")
        if "gzip" not in accept.lower():
            await self.app(scope, receive, send)
            return

        responder = _GZipResponder(send, self.minimum_size)
        await self.app(scope, receive, responder)


class _GZipResponder:
    """Puffert die Antwort nur, solange unklar ist, ob gzip sinnvoll ist.

    Sobald feststeht, dass nicht komprimiert wird (falscher Content-Type,
    bereits kodiert, zu klein, Streaming), werden die Nachrichten unverändert
    durchgereicht — große PDF-Downloads laufen damit weiter als Stream und
    landen nie vollständig im Speicher.
    """

    def __init__(self, send: Send, minimum_size: int) -> None:
        self.send = send
        self.minimum_size = minimum_size
        self.start: Message | None = None
        self.buffer = bytearray()
        self.passthrough = False

    async def __call__(self, message: Message) -> None:
        if message["type"] == "http.response.start":
            headers = Headers(raw=message["headers"])
            if headers.get("content-encoding") or not _is_textual(
                headers.get("content-type", "")
            ):
                self.passthrough = True
                await self.send(message)
                return
            self.start = message
            return

        if message["type"] != "http.response.body":
            await self.send(message)
            return

        if self.passthrough:
            await self.send(message)
            return

        self.buffer.extend(message.get("body", b""))
        if message.get("more_body", False):
            return

        assert self.start is not None
        if len(self.buffer) < self.minimum_size:
            await self.send(self.start)
            await self.send({"type": "http.response.body", "body": bytes(self.buffer)})
            return

        out = io.BytesIO()
        with gzip.GzipFile(mode="wb", fileobj=out, compresslevel=6, mtime=0) as gz:
            gz.write(self.buffer)
        body = out.getvalue()

        headers = MutableHeaders(raw=self.start["headers"])
        headers["Content-Encoding"] = "gzip"
        headers["Content-Length"] = str(len(body))
        headers.add_vary_header("Accept-Encoding")
        await self.send(self.start)
        await self.send({"type": "http.response.body", "body": body})
