"""create misconception_taxonomy and diagnoses tables

Revision ID: f61a2e16bbd5
Revises: 74afda80e038
Create Date: 2026-11-13 17:07:30.852539

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'f61a2e16bbd5'
down_revision: Union[str, None] = '74afda80e038'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'misconception_taxonomy',
        sa.Column('code', sa.String(length=16), nullable=False),
        sa.Column('category', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('pedagogical_remedy', sa.Text(), nullable=False),
        sa.Column('severity', sa.String(length=16), nullable=False),
        sa.Column('is_meta', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('code'),
    )
    op.create_index(
        op.f('ix_misconception_taxonomy_category'),
        'misconception_taxonomy',
        ['category'],
        unique=False,
    )
    op.create_table(
        'diagnoses',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('submission_id', sa.UUID(), nullable=False),
        sa.Column('misconception_code', sa.String(length=16), nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=False),
        sa.Column(
            'detector_type',
            sa.Enum(
                'RULE_AST',
                'PROBE',
                'ML_CLASSIFIER',
                'FUSION',
                'HUMAN_OVERRIDE',
                name='detector_type_enum',
            ),
            nullable=False,
        ),
        sa.Column('is_primary', sa.Boolean(), nullable=False),
        sa.Column('evidence_lines', sa.JSON(), nullable=True),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('metadata_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ['misconception_code'],
            ['misconception_taxonomy.code'],
            ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['submission_id'],
            ['submissions.id'],
            ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_diagnoses_detector_type'),
        'diagnoses',
        ['detector_type'],
        unique=False,
    )
    op.create_index(
        op.f('ix_diagnoses_is_primary'),
        'diagnoses',
        ['is_primary'],
        unique=False,
    )
    op.create_index(
        op.f('ix_diagnoses_misconception_code'),
        'diagnoses',
        ['misconception_code'],
        unique=False,
    )
    op.create_index(
        op.f('ix_diagnoses_submission_id'),
        'diagnoses',
        ['submission_id'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_diagnoses_submission_id'), table_name='diagnoses')
    op.drop_index(op.f('ix_diagnoses_misconception_code'), table_name='diagnoses')
    op.drop_index(op.f('ix_diagnoses_is_primary'), table_name='diagnoses')
    op.drop_index(op.f('ix_diagnoses_detector_type'), table_name='diagnoses')
    op.drop_table('diagnoses')
    op.drop_index(op.f('ix_misconception_taxonomy_category'), table_name='misconception_taxonomy')
    op.drop_table('misconception_taxonomy')
