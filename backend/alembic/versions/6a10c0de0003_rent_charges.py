"""Add monthly rent status foundation."""
from alembic import op
import sqlalchemy as sa

revision = "6a10c0de0003"
down_revision = "6a10c0de0002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "rent_charges",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("tenant_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("apartment_id", sa.Integer(), sa.ForeignKey("apartments.id"), nullable=False),
        sa.Column("period", sa.String(7), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("amount_minor", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("paid_amount_minor", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("tenant_id", "period", name="uq_rent_tenant_period"),
        sa.CheckConstraint("amount_minor > 0", name="ck_rent_amount"),
        sa.CheckConstraint("paid_amount_minor >= 0 AND paid_amount_minor <= amount_minor", name="ck_rent_paid"),
    )
    op.create_index("ix_rent_charges_tenant_id", "rent_charges", ["tenant_id"])
    op.create_index("ix_rent_charges_apartment_id", "rent_charges", ["apartment_id"])


def downgrade():
    op.drop_table("rent_charges")
