"""Härtung auf HTTP-Ebene: Sicherheitskopfzeilen und Größenschranke.

Beide Bausteine sitzen bewusst im Backend und **zusätzlich** in nginx
(`frontend/nginx.conf`). Doppelt, weil beide Wege vorkommen: In der
Standardaufstellung liefert nginx die Oberfläche aus und reicht `/api/`
weiter — dort greifen die nginx-Kopfzeilen. Wird das Backend direkt
angesprochen (anderes Deployment, Port-Weiterleitung, lokaler Betrieb),
greift diese Middleware. Ein Schutz, der nur im Reverse-Proxy steht, fällt
genau dann aus, wenn jemand die Aufstellung ändert.
"""

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

# Cloudflare Turnstile lädt sein Widget von einer festen Fremd-Domain. Die
# Ausnahme steht hier explizit und nicht als pauschales Schlupfloch.
_TURNSTILE = "https://challenges.cloudflare.com"

#: Inhaltsrichtlinie (CSP) — die wichtigste Einzelmaßnahme.
#:
#: Das Anmeldetoken liegt im localStorage; eine Cross-Site-Scripting-Lücke
#: wäre damit eine Kontoübernahme. Die CSP ist die Schranke, die das
#: verhindert: Fremdskripte können weder geladen noch inline ausgeführt
#: werden, und Daten können nicht an fremde Ziele abfließen.
#:
#: Warum die Ausnahmen nötig sind:
#: - ``style-src 'unsafe-inline'``: Vue schreibt gebundene Stile (``:style``)
#:   als Inline-Attribut — der Live-Editor und die Rolodex-Karten setzen ihre
#:   Position so. Ohne die Ausnahme bliebe die Oberfläche unbedienbar.
#:   Inline-*Styles* sind kein Skriptausführungspfad; ``script-src`` bleibt
#:   strikt.
#: - ``worker-src blob:``: pdf.js startet seinen Renderer-Worker.
#: - ``img-src blob: data:``: gerenderte Seiten und Vorschaubilder entstehen
#:   im Browser als Blob bzw. als eingebettete Daten-URL.
CSP = "; ".join(
    [
        "default-src 'self'",
        f"script-src 'self' {_TURNSTILE}",
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data: blob:",
        "font-src 'self' data:",
        "connect-src 'self'",
        "worker-src 'self' blob:",
        "child-src 'self' blob:",
        f"frame-src {_TURNSTILE}",
        # Kein Flash, kein <object>, keine Plugins.
        "object-src 'none'",
        # Verhindert, dass eingeschleustes Markup den Basis-Pfad verbiegt.
        "base-uri 'self'",
        # Formulare dürfen nur an die eigene Herkunft senden.
        "form-action 'self'",
        # Clickjacking: die Anwendung darf in keinem fremden Rahmen laufen.
        "frame-ancestors 'none'",
        # Erzwingt HTTPS für Unterressourcen, wenn die Seite über HTTPS kommt.
        "upgrade-insecure-requests",
    ]
)

_STATIC_HEADERS: tuple[tuple[str, str], ...] = (
    ("Content-Security-Policy", CSP),
    # Kein MIME-Raten: ein hochgeladenes PDF darf nicht als HTML interpretiert
    # und damit im Browser-Kontext ausgeführt werden.
    ("X-Content-Type-Options", "nosniff"),
    # Doppelt zu frame-ancestors, für ältere Browser.
    ("X-Frame-Options", "DENY"),
    # Keine Pfade oder Parameter an fremde Ziele weitergeben.
    ("Referrer-Policy", "strict-origin-when-cross-origin"),
    # Gerätezugriffe, die diese Anwendung nie braucht.
    (
        "Permissions-Policy",
        "camera=(), microphone=(), geolocation=(), payment=(), usb=(), "
        "interest-cohort=()",
    ),
    # Trennt den Browsing-Kontext von fremden Fenstern (Spectre-Klasse).
    ("Cross-Origin-Opener-Policy", "same-origin"),
    ("Cross-Origin-Resource-Policy", "same-origin"),
)


class SecurityHeadersMiddleware:
    """Setzt die Sicherheitskopfzeilen an jede HTTP-Antwort.

    ``hsts_seconds`` nur setzen, wenn der Dienst wirklich ausschließlich über
    HTTPS erreichbar ist — sonst sperrt man sich Testaufrufe über HTTP aus.
    """

    def __init__(self, app: ASGIApp, hsts_seconds: int = 0) -> None:
        self.app = app
        self.hsts = (
            f"max-age={hsts_seconds}; includeSubDomains" if hsts_seconds > 0 else ""
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(raw=message["headers"])
                for name, value in _STATIC_HEADERS:
                    # Vorhandene Werte nicht überschreiben: ein vorgelagerter
                    # Proxy darf strenger sein als wir.
                    if name not in headers:
                        headers[name] = value
                if self.hsts and "Strict-Transport-Security" not in headers:
                    headers["Strict-Transport-Security"] = self.hsts
            await send(message)

        await self.app(scope, receive, send_with_headers)


class BodySizeLimitMiddleware:
    """Weist zu große Anfragen ab, **bevor** der Körper eingelesen wird.

    Die Endpunkte prüfen die Dateigröße erst nach ``await file.read()`` — bis
    dahin liegt die vollständige Datei im Arbeitsspeicher. Bei 400 MB
    Obergrenze und mehreren gleichzeitigen Uploads ist das ein
    Erschöpfungsangriff mit einer einzigen curl-Zeile: Der Speicher ist voll,
    bevor die erste Prüfung greift.

    Diese Middleware liest ``Content-Length`` aus dem Kopf und antwortet
    sofort mit 413. Sie ersetzt die fachlichen Prüfungen nicht (die
    unterscheiden zwischen Einzeldatei und Gesamtmenge und kennen die Stufe
    angemeldet/anonym), sondern zieht eine harte Obergrenze davor.

    Ohne ``Content-Length`` — also bei ``Transfer-Encoding: chunked`` — zählt
    die Middleware die tatsächlich gelesenen Bytes mit und bricht ab, sobald
    die Grenze überschritten ist. Sonst wäre die Schranke mit einem
    weggelassenen Kopf zu umgehen.
    """

    def __init__(self, app: ASGIApp, max_bytes: int) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("method") in ("GET", "HEAD", "OPTIONS"):
            await self.app(scope, receive, send)
            return

        declared = Headers(scope=scope).get("content-length")
        if declared is not None:
            try:
                if int(declared) > self.max_bytes:
                    await self._reject(send)
                    return
            except ValueError:
                await self._reject(send, status=400, detail="Ungültige Längenangabe")
                return

        received = 0
        exceeded = False

        async def counting_receive() -> Message:
            nonlocal received, exceeded
            message = await receive()
            if message["type"] == "http.request":
                received += len(message.get("body", b""))
                if received > self.max_bytes:
                    exceeded = True
                    # Verbindung nicht weiterfüttern: der Endpunkt sieht das
                    # Ende des Körpers und bricht seinerseits ab.
                    return {"type": "http.disconnect"}
            return message

        await self.app(scope, counting_receive, send)
        if exceeded:  # pragma: no cover — Abbruch bereits signalisiert
            return

    async def _reject(
        self, send: Send, status: int = 413, detail: str | None = None
    ) -> None:
        import json

        mb = self.max_bytes // (1024 * 1024)
        body = json.dumps(
            {"detail": detail or f"Anfrage zu groß — Obergrenze {mb} MB"}
        ).encode()
        await send(
            {
                "type": "http.response.start",
                "status": status,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode()),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})
