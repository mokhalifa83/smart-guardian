"""001 Initial Smart Guardian Schema and TimescaleDB Hypertables

Revision ID: 001_initial_schema
Revises: 
Create Date: 2026-10-26 19:30:00

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import text

revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Wells table
    op.create_table(
        'wells',
        sa.Column('well_code', sa.String(length=50), nullable=False),
        sa.Column('field_name', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='ACTIVE'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('well_code')
    )
    op.create_index('ix_wells_well_code', 'wells', ['well_code'])
    op.create_index('ix_wells_field_name', 'wells', ['field_name'])

    # 2. Well Config table
    op.create_table(
        'well_configs',
        sa.Column('well_code', sa.String(length=50), nullable=False),
        sa.Column('wc_threshold', sa.Float(), nullable=False, server_default='80.0'),
        sa.Column('wc_trend_window_hours', sa.Integer(), nullable=False, server_default='24'),
        sa.Column('alert_cooldown_minutes', sa.Integer(), nullable=False, server_default='60'),
        sa.Column('surveillance_interval_minutes', sa.Integer(), nullable=False, server_default='5'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['well_code'], ['wells.well_code'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('well_code')
    )
    op.create_index('ix_well_configs_well_code', 'well_configs', ['well_code'])

    # 3. Production Readings (TimescaleDB hypertable candidate)
    op.create_table(
        'production_readings',
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('well_code', sa.String(length=50), nullable=False),
        sa.Column('source', sa.String(length=50), nullable=False, server_default='SOFTWARE_API'),
        sa.Column('oil_rate', sa.Float(), nullable=True),
        sa.Column('water_rate', sa.Float(), nullable=True),
        sa.Column('gas_rate', sa.Float(), nullable=True),
        sa.Column('wc_percent', sa.Float(), nullable=True),
        sa.Column('value_type', sa.String(length=50), nullable=False, server_default='MEASURED'),
        sa.Column('quality_status', sa.String(length=50), nullable=False, server_default='VALID'),
        sa.Column('validation_status', sa.String(length=50), nullable=False, server_default='VALID'),
        sa.Column('received_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('source_system', sa.String(length=100), nullable=True),
        sa.Column('source_record_id', sa.String(length=100), nullable=True),
        sa.Column('idempotency_hash', sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(['well_code'], ['wells.well_code'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('timestamp', 'well_code', 'source', name='pk_production_readings')
    )
    op.create_index('ix_production_readings_timestamp', 'production_readings', ['timestamp'])
    op.create_index('ix_production_readings_well_code', 'production_readings', ['well_code'])
    op.create_index('ix_prod_readings_well_time', 'production_readings', ['well_code', 'timestamp'])
    op.create_index('ix_production_readings_idempotency_hash', 'production_readings', ['idempotency_hash'])

    # 4. Separator Readings (TimescaleDB hypertable candidate)
    op.create_table(
        'separator_readings',
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('well_code', sa.String(length=50), nullable=False),
        sa.Column('source', sa.String(length=50), nullable=False, server_default='SOFTWARE_API'),
        sa.Column('pressure', sa.Float(), nullable=True),
        sa.Column('flow_rate', sa.Float(), nullable=True),
        sa.Column('water_cut', sa.Float(), nullable=True),
        sa.Column('original_wc_value', sa.Float(), nullable=True),
        sa.Column('original_wc_unit', sa.String(length=20), nullable=True),
        sa.Column('oil_rate', sa.Float(), nullable=True),
        sa.Column('water_rate', sa.Float(), nullable=True),
        sa.Column('gas_rate', sa.Float(), nullable=True),
        sa.Column('value_type', sa.String(length=50), nullable=False, server_default='MEASURED'),
        sa.Column('quality_status', sa.String(length=50), nullable=False, server_default='VALID'),
        sa.Column('validation_status', sa.String(length=50), nullable=False, server_default='VALID'),
        sa.Column('received_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('source_system', sa.String(length=100), nullable=True),
        sa.Column('source_record_id', sa.String(length=100), nullable=True),
        sa.Column('idempotency_hash', sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(['well_code'], ['wells.well_code'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('timestamp', 'well_code', 'source', name='pk_separator_readings')
    )
    op.create_index('ix_separator_readings_timestamp', 'separator_readings', ['timestamp'])
    op.create_index('ix_separator_readings_well_code', 'separator_readings', ['well_code'])
    op.create_index('ix_sep_readings_well_time', 'separator_readings', ['well_code', 'timestamp'])
    op.create_index('ix_separator_readings_idempotency_hash', 'separator_readings', ['idempotency_hash'])

    # 5. Manual Readings
    op.create_table(
        'manual_readings',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('well_code', sa.String(length=50), nullable=False),
        sa.Column('measurement_type', sa.String(length=50), nullable=False),
        sa.Column('value', sa.Float(), nullable=True),
        sa.Column('unit', sa.String(length=20), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('source', sa.String(length=50), nullable=False, server_default='MANUAL'),
        sa.Column('entered_by', sa.String(length=100), nullable=False),
        sa.Column('validation_status', sa.String(length=50), nullable=False, server_default='VALID'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('idempotency_hash', sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(['well_code'], ['wells.well_code'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_manual_readings_timestamp', 'manual_readings', ['timestamp'])
    op.create_index('ix_manual_readings_well_code', 'manual_readings', ['well_code'])
    op.create_index('ix_manual_readings_well_type_time', 'manual_readings', ['well_code', 'measurement_type', 'timestamp'])

    # 6. Alerts
    op.create_table(
        'alerts',
        sa.Column('alert_id', sa.String(length=36), nullable=False),
        sa.Column('well_code', sa.String(length=50), nullable=False),
        sa.Column('alert_type', sa.String(length=50), nullable=False, server_default='WATER_CUT'),
        sa.Column('severity', sa.String(length=20), nullable=False, server_default='WARNING'),
        sa.Column('message', sa.String(length=500), nullable=False),
        sa.Column('value', sa.Float(), nullable=True),
        sa.Column('threshold', sa.Float(), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='ACTIVE'),
        sa.Column('source', sa.String(length=50), nullable=False, server_default='SURVEILLANCE_ENGINE'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['well_code'], ['wells.well_code'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('alert_id')
    )
    op.create_index('ix_alerts_timestamp', 'alerts', ['timestamp'])
    op.create_index('ix_alerts_well_code', 'alerts', ['well_code'])
    op.create_index('ix_alerts_well_status_type', 'alerts', ['well_code', 'status', 'alert_type'])

    # 7. Analysis Results
    op.create_table(
        'analysis_results',
        sa.Column('analysis_id', sa.String(length=36), nullable=False),
        sa.Column('well_code', sa.String(length=50), nullable=False),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('analysis_type', sa.String(length=50), nullable=False, server_default='WATER_CUT_SURVEILLANCE'),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='NORMAL'),
        sa.Column('observed_value', sa.Float(), nullable=True),
        sa.Column('threshold', sa.Float(), nullable=True),
        sa.Column('data_source', sa.String(length=50), nullable=False, server_default='SOFTWARE_API'),
        sa.Column('data_quality', sa.String(length=50), nullable=False, server_default='VALID'),
        sa.Column('diagnostic_details', sa.String(length=500), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['well_code'], ['wells.well_code'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('analysis_id')
    )
    op.create_index('ix_analysis_results_timestamp', 'analysis_results', ['timestamp'])
    op.create_index('ix_analysis_results_well_code', 'analysis_results', ['well_code'])
    op.create_index('ix_analysis_results_well_type_time', 'analysis_results', ['well_code', 'analysis_type', 'timestamp'])

    # TimescaleDB hypertable creation when running on PostgreSQL
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        try:
            op.execute("SELECT create_hypertable('production_readings', 'timestamp', if_not_exists => TRUE);")
            op.execute("SELECT create_hypertable('separator_readings', 'timestamp', if_not_exists => TRUE);")
        except Exception as e:
            print(f"Notice: TimescaleDB hypertable setup: {e}")


def downgrade() -> None:
    op.drop_table('analysis_results')
    op.drop_table('alerts')
    op.drop_table('manual_readings')
    op.drop_table('separator_readings')
    op.drop_table('production_readings')
    op.drop_table('well_configs')
    op.drop_table('wells')
