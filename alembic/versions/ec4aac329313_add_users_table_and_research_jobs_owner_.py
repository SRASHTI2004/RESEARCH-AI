"""add users table and research_jobs.owner_id

Revision ID: ec4aac329313
Revises: 424a4cec1118
Create Date: 2026-10-02 10:44:08.630423

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ec4aac329313'
down_revision: Union[str, None] = '424a4cec1118'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('users',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('email', sa.String(length=255), nullable=False),
    sa.Column('hashed_password', sa.String(length=255), nullable=False),
    sa.Column('role', sa.String(length=20), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)

    # batch_alter_table (not plain add_column/create_foreign_key) is required
    # for SQLite to add a named FK via ALTER TABLE; it's a no-op wrapper on
    # Postgres. The explicit name also makes downgrade() actually work —
    # autogenerate's unnamed `drop_constraint(None, ...)` doesn't.
    with op.batch_alter_table('research_jobs', schema=None) as batch_op:
        batch_op.add_column(sa.Column('owner_id', sa.String(length=36), nullable=True))
        batch_op.create_foreign_key(
            'fk_research_jobs_owner_id_users', 'users', ['owner_id'], ['id'], ondelete='SET NULL'
        )


def downgrade() -> None:
    with op.batch_alter_table('research_jobs', schema=None) as batch_op:
        batch_op.drop_constraint('fk_research_jobs_owner_id_users', type_='foreignkey')
        batch_op.drop_column('owner_id')

    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
