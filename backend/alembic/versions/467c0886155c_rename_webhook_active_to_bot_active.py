"""rename webhook_active to bot_active

Revision ID: 467c0886155c
Revises: b98276f7581b
Create Date: 2026-09-06 16:12:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "467c0886155c"
down_revision: str | Sequence[str] | None = "b98276f7581b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """The bot is driven by polling now, so the flag no longer names a webhook."""
    with op.batch_alter_table("assistants") as batch_op:
        batch_op.alter_column(
            "webhook_active", new_column_name="bot_active", existing_type=sa.Boolean()
        )


def downgrade() -> None:
    with op.batch_alter_table("assistants") as batch_op:
        batch_op.alter_column(
            "bot_active", new_column_name="webhook_active", existing_type=sa.Boolean()
        )
