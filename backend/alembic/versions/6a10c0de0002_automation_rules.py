"""Add deterministic apartment automation rules."""
from alembic import op
import sqlalchemy as sa

revision = "6a10c0de0002"
down_revision = "6a10c0de0001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "automation_rules",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("apartment_id", sa.Integer(), sa.ForeignKey("apartments.id"), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("source_device_id", sa.Integer(), sa.ForeignKey("devices.id"), nullable=False),
        sa.Column("source_power", sa.String(3), nullable=False),
        sa.Column("target_device_id", sa.Integer(), sa.ForeignKey("devices.id"), nullable=False),
        sa.Column("target_power", sa.String(3), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), nullable=False),
        sa.CheckConstraint("source_power IN ('on', 'off')", name="ck_rule_source_power"),
        sa.CheckConstraint("target_power IN ('on', 'off')", name="ck_rule_target_power"),
        sa.CheckConstraint("source_device_id != target_device_id", name="ck_rule_distinct_devices"),
    )
    op.create_index("ix_automation_rules_apartment_id", "automation_rules", ["apartment_id"])


def downgrade():
    op.drop_table("automation_rules")
