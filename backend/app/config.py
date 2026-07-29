"""Zentrale Konfiguration der PDF-Editor-App (pydantic-settings).

Alle Werte sind über Umgebungsvariablen mit Präfix PDFAPP_ überschreibbar,
z.B. PDFAPP_MAX_FILE_SIZE_MB=50.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PDFAPP_", env_file=".env")

    # Datei-Limits (öffentliche App: bewusst niedriger als intern)
    max_file_size_mb: int = 50
    max_total_size_mb: int = 200

    # Rate-Limiting pro IP (slowapi-Syntax)
    rate_limit_default: str = "30/minute;500/day"
    rate_limit_mail: str = "5/hour"

    # CORS (leer = gleiche Origin über nginx-Proxy, kein CORS nötig)
    cors_origins: str = ""

    # Datenbank + Auth (Konten sind optional — ohne erreichbare DB läuft die
    # App anonym weiter, Auth-Endpoints antworten dann 503)
    database_url: str = "postgresql+psycopg2://pdfapp:pdfapp@db:5432/pdfapp"
    secret_key: str = "dev-only-nicht-fuer-produktion"
    access_token_expire_minutes: int = 720
    admin_email: str = ""
    admin_password: str = ""

    # Limits für angemeldete Nutzer (höher als anonym)
    max_file_size_mb_authed: int = 100
    max_total_size_mb_authed: int = 400
    rate_limit_authed: str = "60/minute;2000/day"

    # Konto-Einstellungen (JSON-Blob)
    preferences_max_bytes: int = 16384

    # Öffentliche Basis-URL für Links in Mails (Verifikation/Passwort-Reset),
    # z.B. https://pdf.flowaudit.de — leer = Flows senden keine Mails
    public_base_url: str = ""

    # Cloudflare Turnstile (optional): beide Keys gesetzt = Registrierung und
    # Mailversand verlangen ein gültiges Turnstile-Token
    turnstile_site_key: str = ""
    turnstile_secret: str = ""

    # CF-Connecting-IP nur verwenden, wenn das Backend ausschließlich hinter
    # Cloudflare erreichbar ist (Tunnel-Deploy) — sonst ist der Header spoofbar
    # und hebelt Rate-Limits und Job-Ownership aus
    trust_cf_header: bool = False

    # Mailversand — nur aktiv, wenn smtp_host gesetzt ist
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@flowaudit.de"
    smtp_starttls: bool = True
    mail_max_attachment_mb: int = 20


settings = Settings()
