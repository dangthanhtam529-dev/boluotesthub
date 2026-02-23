"""refactor_defect_table

Revision ID: e8f9a0b1c2d3
Revises: d4e5f6a7b8c9
Create Date: 2026-02-21 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = 'e8f9a0b1c2d3'
down_revision = 'd4e5f6a7b8c9'
branch_labels = None
depends_on = None


def column_exists(table_name, column_name):
    conn = op.get_bind()
    inspector = inspect(conn)
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns


def constraint_exists(table_name, constraint_name):
    conn = op.get_bind()
    inspector = inspect(conn)
    try:
        foreign_keys = inspector.get_foreign_keys(table_name)
        for fk in foreign_keys:
            if fk.get('name') == constraint_name:
                return True
    except Exception:
        pass
    return False


def index_exists(table_name, index_name):
    conn = op.get_bind()
    inspector = inspect(conn)
    try:
        indexes = inspector.get_indexes(table_name)
        for idx in indexes:
            if idx.get('name') == index_name:
                return True
    except Exception:
        pass
    return False


def upgrade():
    if not column_exists('defects', 'source'):
        op.add_column('defects', sa.Column('source', sa.String(20), nullable=True, server_default='manual'))
    if not column_exists('defects', 'source_id'):
        op.add_column('defects', sa.Column('source_id', sa.String(100), nullable=True))
    if not column_exists('defects', 'api_method'):
        op.add_column('defects', sa.Column('api_method', sa.String(10), nullable=True))
    if not column_exists('defects', 'error_type'):
        op.add_column('defects', sa.Column('error_type', sa.String(50), nullable=True))
    if not column_exists('defects', 'request_data'):
        op.add_column('defects', sa.Column('request_data', sa.Text(), nullable=True))
    if not column_exists('defects', 'response_data'):
        op.add_column('defects', sa.Column('response_data', sa.Text(), nullable=True))
    if not column_exists('defects', 'error_detail'):
        op.add_column('defects', sa.Column('error_detail', sa.Text(), nullable=True))
    if not column_exists('defects', 'tags'):
        op.add_column('defects', sa.Column('tags', sa.Text(), nullable=True))
    if not column_exists('defects', 'fingerprint'):
        op.add_column('defects', sa.Column('fingerprint', sa.String(32), nullable=True))
    if not column_exists('defects', 'occurrence_count'):
        op.add_column('defects', sa.Column('occurrence_count', sa.Integer(), nullable=True, server_default='1'))
    if not column_exists('defects', 'ai_analysis'):
        op.add_column('defects', sa.Column('ai_analysis', sa.Text(), nullable=True))
    if not column_exists('defects', 'ai_suggestion'):
        op.add_column('defects', sa.Column('ai_suggestion', sa.Text(), nullable=True))
    
    if not index_exists('defects', 'ix_defects_fingerprint'):
        op.create_index('ix_defects_fingerprint', 'defects', ['fingerprint'])
    
    if constraint_exists('defects', 'defects_ibfk_3'):
        try:
            op.drop_constraint('defects_ibfk_3', 'defects', type_='foreignkey')
        except Exception:
            pass
    if constraint_exists('defects', 'defects_ibfk_4'):
        try:
            op.drop_constraint('defects_ibfk_4', 'defects', type_='foreignkey')
        except Exception:
            pass
    
    if column_exists('defects', 'status'):
        try:
            op.drop_column('defects', 'status')
        except Exception:
            pass
    if column_exists('defects', 'priority'):
        try:
            op.drop_column('defects', 'priority')
        except Exception:
            pass
    if column_exists('defects', 'defect_type'):
        try:
            op.drop_column('defects', 'defect_type')
        except Exception:
            pass
    if column_exists('defects', 'sub_module'):
        try:
            op.drop_column('defects', 'sub_module')
        except Exception:
            pass
    if column_exists('defects', 'environment'):
        try:
            op.drop_column('defects', 'environment')
        except Exception:
            pass
    if column_exists('defects', 'version'):
        try:
            op.drop_column('defects', 'version')
        except Exception:
            pass
    if column_exists('defects', 'steps'):
        try:
            op.drop_column('defects', 'steps')
        except Exception:
            pass
    if column_exists('defects', 'expected_result'):
        try:
            op.drop_column('defects', 'expected_result')
        except Exception:
            pass
    if column_exists('defects', 'actual_result'):
        try:
            op.drop_column('defects', 'actual_result')
        except Exception:
            pass
    if column_exists('defects', 'root_cause'):
        try:
            op.drop_column('defects', 'root_cause')
        except Exception:
            pass
    if column_exists('defects', 'solution'):
        try:
            op.drop_column('defects', 'solution')
        except Exception:
            pass
    if column_exists('defects', 'fix_version'):
        try:
            op.drop_column('defects', 'fix_version')
        except Exception:
            pass
    if column_exists('defects', 'reporter_id'):
        try:
            op.drop_column('defects', 'reporter_id')
        except Exception:
            pass
    if column_exists('defects', 'assignee_id'):
        try:
            op.drop_column('defects', 'assignee_id')
        except Exception:
            pass


def downgrade():
    if not column_exists('defects', 'status'):
        op.add_column('defects', sa.Column('status', sa.String(20), nullable=True, server_default='new'))
    if not column_exists('defects', 'priority'):
        op.add_column('defects', sa.Column('priority', sa.String(20), nullable=True, server_default='medium'))
    if not column_exists('defects', 'defect_type'):
        op.add_column('defects', sa.Column('defect_type', sa.String(50), nullable=True))
    if not column_exists('defects', 'sub_module'):
        op.add_column('defects', sa.Column('sub_module', sa.String(100), nullable=True))
    if not column_exists('defects', 'environment'):
        op.add_column('defects', sa.Column('environment', sa.String(50), nullable=True))
    if not column_exists('defects', 'version'):
        op.add_column('defects', sa.Column('version', sa.String(50), nullable=True))
    if not column_exists('defects', 'steps'):
        op.add_column('defects', sa.Column('steps', sa.Text(), nullable=True))
    if not column_exists('defects', 'expected_result'):
        op.add_column('defects', sa.Column('expected_result', sa.Text(), nullable=True))
    if not column_exists('defects', 'actual_result'):
        op.add_column('defects', sa.Column('actual_result', sa.Text(), nullable=True))
    if not column_exists('defects', 'root_cause'):
        op.add_column('defects', sa.Column('root_cause', sa.Text(), nullable=True))
    if not column_exists('defects', 'solution'):
        op.add_column('defects', sa.Column('solution', sa.Text(), nullable=True))
    if not column_exists('defects', 'fix_version'):
        op.add_column('defects', sa.Column('fix_version', sa.String(50), nullable=True))
    if not column_exists('defects', 'reporter_id'):
        op.add_column('defects', sa.Column('reporter_id', sa.String(36), nullable=True))
    if not column_exists('defects', 'assignee_id'):
        op.add_column('defects', sa.Column('assignee_id', sa.String(36), nullable=True))
    
    if index_exists('defects', 'ix_defects_fingerprint'):
        try:
            op.drop_index('ix_defects_fingerprint', 'defects')
        except Exception:
            pass
    
    if column_exists('defects', 'source'):
        try:
            op.drop_column('defects', 'source')
        except Exception:
            pass
    if column_exists('defects', 'source_id'):
        try:
            op.drop_column('defects', 'source_id')
        except Exception:
            pass
    if column_exists('defects', 'api_method'):
        try:
            op.drop_column('defects', 'api_method')
        except Exception:
            pass
    if column_exists('defects', 'error_type'):
        try:
            op.drop_column('defects', 'error_type')
        except Exception:
            pass
    if column_exists('defects', 'request_data'):
        try:
            op.drop_column('defects', 'request_data')
        except Exception:
            pass
    if column_exists('defects', 'response_data'):
        try:
            op.drop_column('defects', 'response_data')
        except Exception:
            pass
    if column_exists('defects', 'error_detail'):
        try:
            op.drop_column('defects', 'error_detail')
        except Exception:
            pass
    if column_exists('defects', 'tags'):
        try:
            op.drop_column('defects', 'tags')
        except Exception:
            pass
    if column_exists('defects', 'fingerprint'):
        try:
            op.drop_column('defects', 'fingerprint')
        except Exception:
            pass
    if column_exists('defects', 'occurrence_count'):
        try:
            op.drop_column('defects', 'occurrence_count')
        except Exception:
            pass
    if column_exists('defects', 'ai_analysis'):
        try:
            op.drop_column('defects', 'ai_analysis')
        except Exception:
            pass
    if column_exists('defects', 'ai_suggestion'):
        try:
            op.drop_column('defects', 'ai_suggestion')
        except Exception:
            pass
