"""add cell_status_events

Migración 100% aditiva: solo crea la tabla `cell_status_events` y su índice,
que conserva el motivo, el responsable y la fecha/hora de cada cambio de estado
de una celda (disponible <-> mantenimiento). No toca, renombra ni elimina
ninguna columna ni tabla existente; `cells`, `zones`, `sites` y el resto del
esquema quedan exactamente igual. El `downgrade()` elimina únicamente los
objetos que esta revisión crea.

Revision ID: c3e7a91f5b22
Revises: 9d21f4c7ab05
Create Date: 2026-11-16 15:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c3e7a91f5b22'
down_revision: Union[str, Sequence[str], None] = '9d21f4c7ab05'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Crea la tabla de historial de cambios de estado de celdas."""
    op.create_table(
        'cell_status_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('cell_id', sa.Integer(), nullable=False),
        sa.Column('from_status', sa.String(length=20), nullable=False),
        sa.Column('to_status', sa.String(length=20), nullable=False),
        sa.Column('reason', sa.String(length=240), nullable=False),
        sa.Column('actor', sa.String(length=60), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['cell_id'], ['cells.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_cell_status_events_cell', 'cell_status_events', ['cell_id', 'created_at'])


def downgrade() -> None:
    """Elimina solo lo que creó esta revisión."""
    op.drop_index('ix_cell_status_events_cell', table_name='cell_status_events')
    op.drop_table('cell_status_events')
