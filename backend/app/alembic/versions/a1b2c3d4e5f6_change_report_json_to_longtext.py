"""change report_json to LONGTEXT

Revision ID: a1b2c3d4e5f6
Revises: f9a0b1c2d3e4
Create Date: 2026-02-24 15:35:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'f9a0b1c2d3e4'
branch_labels = None
depends_on = None


def upgrade():
    # 修改 report_json 字段为 LONGTEXT 类型以支持大报告
    op.alter_column('testexecution', 'report_json',
                    existing_type=sa.Text(),
                    type_=mysql.LONGTEXT(),
                    existing_nullable=True)


def downgrade():
    # 回滚为 TEXT 类型
    op.alter_column('testexecution', 'report_json',
                    existing_type=mysql.LONGTEXT(),
                    type_=sa.Text(),
                    existing_nullable=True)
