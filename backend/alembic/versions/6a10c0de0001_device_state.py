"""Add device power state without changing existing device flags."""
from alembic import op
import sqlalchemy as sa

revision = "6a10c0de0001"
down_revision = "4fb37f1d0a7f"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("devices") as batch:
        batch.add_column(sa.Column("power", sa.String(3), nullable=False, server_default="off"))
        batch.add_column(sa.Column("state_updated_at", sa.DateTime(timezone=True), nullable=True))
        batch.create_check_constraint("ck_device_power", "power IN ('on', 'off')")


def downgrade():
    with op.batch_alter_table("devices") as batch:
        batch.drop_constraint("ck_device_power", type_="check")
        batch.drop_column("state_updated_at")
        batch.drop_column("power")
