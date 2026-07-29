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

    # Mailversand — nur aktiv, wenn smtp_host gesetzt ist
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@flowaudit.de"
    smtp_starttls: bool = True
    mail_max_attachment_mb: int = 20


settings = Settings()
