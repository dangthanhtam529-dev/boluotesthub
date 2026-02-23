"""add_retry_timeout_fields_to_scheduled_tasks

Revision ID: d4e5f6a7b8c9
Revises: c0f74d4a30db
Create Date: 2026-02-20 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'd4e5f6a7b8c9'
down_revision = '40b4b8762289'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        'scheduled_tasks',
        sa.Column('max_retries', sa.Integer(), nullable=True, server_default='3')
    )
    op.add_column(
        'scheduled_tasks',
        sa.Column('retry_interval', sa.Integer(), nullable=True, server_default='60')
    )
    op.add_column(
        'scheduled_tasks',
        sa.Column('timeout_seconds', sa.Integer(), nullable=True, server_default='300')
    )
    
    op.add_column(
        'task_execution_logs',
        sa.Column('retry_count', sa.Integer(), nullable=True, server_default='0')
    )
    op.add_column(
        'task_execution_logs',
        sa.Column('attempt_number', sa.Integer(), nullable=True, server_default='1')
    )


def downgrade():
    op.drop_column('scheduled_tasks', 'max_retries')
    op.drop_column('scheduled_tasks', 'retry_interval')
    op.drop_column('scheduled_tasks', 'timeout_seconds')
    op.drop_column('task_execution_logs', 'retry_count')
    op.drop_column('task_execution_logs', 'attempt_number')
