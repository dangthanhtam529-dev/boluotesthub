"""add audit log table

Revision ID: 6a8c2e77d9d1
Revises: 7881fb1235b0
Create Date: 2026-02-13 11:40:00.000000

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


revision = "6a8c2e77d9d1"
down_revision = "7881fb1235b0"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "auditlog",
        sa.Column("request_id", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=True),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("actor_email", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
        sa.Column("actor_ip", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column("action", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column("resource_type", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=False),
        sa.Column("resource_id", sqlmodel.sql.sqltypes.AutoString(length=128), nullable=True),
        sa.Column("resource_name", sqlmodel.sql.sqltypes.AutoString(length=255), nullable=True),
        sa.Column("before", sa.JSON(), nullable=True),
        sa.Column("after", sa.JSON(), nullable=True),
        sa.Column("diff_summary", sqlmodel.sql.sqltypes.AutoString(length=1000), nullable=True),
        sa.Column("status", sqlmodel.sql.sqltypes.AutoString(length=16), nullable=False),
        sa.Column("error_code", sqlmodel.sql.sqltypes.AutoString(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_auditlog_action"), "auditlog", ["action"], unique=False)
    op.create_index(op.f("ix_auditlog_actor_user_id"), "auditlog", ["actor_user_id"], unique=False)
    op.create_index(op.f("ix_auditlog_created_at"), "auditlog", ["created_at"], unique=False)
    op.create_index(op.f("ix_auditlog_request_id"), "auditlog", ["request_id"], unique=False)
    op.create_index(op.f("ix_auditlog_resource_id"), "auditlog", ["resource_id"], unique=False)
    op.create_index(op.f("ix_auditlog_resource_type"), "auditlog", ["resource_type"], unique=False)
    op.create_index(op.f("ix_auditlog_status"), "auditlog", ["status"], unique=False)


def downgrade():
    op.drop_index(op.f("ix_auditlog_status"), table_name="auditlog")
    op.drop_index(op.f("ix_auditlog_resource_type"), table_name="auditlog")
    op.drop_index(op.f("ix_auditlog_resource_id"), table_name="auditlog")
    op.drop_index(op.f("ix_auditlog_request_id"), table_name="auditlog")
    op.drop_index(op.f("ix_auditlog_created_at"), table_name="auditlog")
    op.drop_index(op.f("ix_auditlog_actor_user_id"), table_name="auditlog")
    op.drop_index(op.f("ix_auditlog_action"), table_name="auditlog")
    op.drop_table("auditlog")

