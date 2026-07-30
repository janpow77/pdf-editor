"""Einstellungstabelle für die Werkzeug-Freigabe (idempotent).

Revision ID: 0002
Revises: 0001
"""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "app_settings" in inspector.get_table_names():
        return
    json_type = (
        sa.dialects.postgresql.JSONB()
        if bind.dialect.name == "postgresql"
        else sa.JSON()
    )
    op.create_table(
        "app_settings",
        sa.Column("key", sa.String(length=64), primary_key=True),
        sa.Column("value", json_type, nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    bind = op.get_bind()
    if "app_settings" in sa.inspect(bind).get_table_names():
        op.drop_table("app_settings")
