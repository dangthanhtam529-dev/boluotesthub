"""create_defect_import_records_table

Revision ID: f9a0b1c2d3e4
Revises: e8f9a0b1c2d3
Create Date: 2026-02-21 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = 'f9a0b1c2d3e4'
down_revision = 'e8f9a0b1c2d3'
branch_labels = None
depends_on = None


def table_exists(table_name):
    conn = op.get_bind()
    inspector = inspect(conn)
    return table_name in inspector.get_table_names()


def upgrade():
    if not table_exists('defect_import_records'):
        op.create_table(
            'defect_import_records',
            sa.Column('id', sa.String(36), primary_key=True),
            sa.Column('project_id', sa.String(36), sa.ForeignKey('projects.id'), nullable=False),
            sa.Column('platform', sa.String(20), nullable=False),
            sa.Column('file_name', sa.String(255), nullable=False),
            sa.Column('file_size', sa.Integer(), nullable=True, server_default='0'),
            sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
            sa.Column('total_count', sa.Integer(), nullable=True, server_default='0'),
            sa.Column('new_count', sa.Integer(), nullable=True, server_default='0'),
            sa.Column('duplicate_count', sa.Integer(), nullable=True, server_default='0'),
            sa.Column('error_count', sa.Integer(), nullable=True, server_default='0'),
            sa.Column('parsed_data', sa.Text(), nullable=True),
            sa.Column('field_mapping', sa.Text(), nullable=True),
            sa.Column('error_detail', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=True),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
            sa.Column('completed_at', sa.DateTime(), nullable=True),
        )
        op.create_index('ix_defect_import_records_project_id', 'defect_import_records', ['project_id'])
        op.create_index('ix_defect_import_records_status', 'defect_import_records', ['status'])


def downgrade():
    if table_exists('defect_import_records'):
        op.drop_index('ix_defect_import_records_status', 'defect_import_records')
        op.drop_index('ix_defect_import_records_project_id', 'defect_import_records')
        op.drop_table('defect_import_records')
