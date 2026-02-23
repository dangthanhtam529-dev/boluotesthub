"""add_scheduled_task_tables

Revision ID: c0f74d4a30db
Revises: e634d2aec366
Create Date: 2026-02-19 17:33:08.116116

"""
from alembic import op
import sqlalchemy as sa
import sqlmodel.sql.sqltypes


# revision identifiers, used by Alembic.
revision = 'c0f74d4a30db'
down_revision = 'e634d2aec366'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'scheduled_tasks',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('description', sa.String(500), nullable=True),
        sa.Column('project_id', sa.String(36), sa.ForeignKey('projects.id'), nullable=True),
        sa.Column('collection_id', sa.String(100), nullable=False),
        sa.Column('collection_type', sa.String(50), nullable=False, server_default='test-suite'),
        sa.Column('environment', sa.String(100), nullable=True),
        sa.Column('trigger_type', sa.String(20), nullable=False),
        sa.Column('trigger_config', sa.Text(), nullable=False),
        sa.Column('is_enabled', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('notification_rule_id', sa.String(36), sa.ForeignKey('notification_rules.id'), nullable=True),
        sa.Column('last_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('next_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    
    op.create_table(
        'task_execution_logs',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('task_id', sa.String(36), sa.ForeignKey('scheduled_tasks.id'), nullable=False),
        sa.Column('execution_id', sa.String(36), sa.ForeignKey('testexecution.id'), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade():
    op.drop_table('task_execution_logs')
    op.drop_table('scheduled_tasks')
