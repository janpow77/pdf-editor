"""Initiales Schema: users-Tabelle inkl. Verifikations-/Reset-Feldern.

Idempotent geschrieben (checkfirst), damit sie auch auf einer bereits per
create_all initialisierten Datenbank sauber durchläuft.

Revision ID: 0001
Revises:
Create Date: 2026-07-29
"""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if "users" not in inspector.get_table_names():
        from app.db import Base
        from app import models  # noqa: F401

        Base.metadata.create_all(bind=bind, checkfirst=True)
        return

    # Bestehende Tabelle (aus create_all vor 0001): fehlende Spalten nachziehen
    existing = {c["name"] for c in inspector.get_columns("users")}
    new_columns = [
        sa.Column("is_verified", sa.Boolean(), nullable=True),
        sa.Column("verify_token_hash", sa.String(64), nullable=True),
        sa.Column("verify_token_expires", sa.DateTime(), nullable=True),
        sa.Column("reset_token_hash", sa.String(64), nullable=True),
        sa.Column("reset_token_expires", sa.DateTime(), nullable=True),
    ]
    for col in new_columns:
        if col.name not in existing:
            op.add_column("users", col)
    if "is_verified" not in existing:
        op.execute("UPDATE users SET is_verified = false WHERE is_verified IS NULL")


def downgrade() -> None:
    for name in (
        "reset_token_expires",
        "reset_token_hash",
        "verify_token_expires",
        "verify_token_hash",
        "is_verified",
    ):
        op.drop_column("users", name)
