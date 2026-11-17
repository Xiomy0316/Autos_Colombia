"""add users, roles, user_roles, user_activity and v_user_roles view

Migración 100% aditiva: solo crea objetos nuevos (4 tablas, 1 vista y la
semilla del catálogo de roles). No toca, renombra ni elimina ninguna columna
de `employees` ni ninguna otra tabla existente. El `downgrade()` elimina
únicamente los objetos que esta revisión crea.

Revision ID: 9d21f4c7ab05
Revises: b7c41d9a2e30
Create Date: 2026-11-16 10:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '9d21f4c7ab05'
down_revision: Union[str, Sequence[str], None] = 'b7c41d9a2e30'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Catálogo de roles. Los códigos coinciden con los que Autos Colombia ya usa
# (`ADMIN` y `OPERATOR`) para no duplicar roles ni alterar permisos actuales.
ROLE_CATALOG = (
    {
        "code": "ADMIN",
        "name": "Administrador",
        "description": (
            "Incluye operación, gestión de usuarios, sedes, zonas, celdas y "
            "consulta de actividad administrativa."
        ),
        "sort": 1,
    },
    {
        "code": "OPERATOR",
        "name": "Empleado",
        "description": (
            "Registrar ingresos, salidas, pagos y novedades; consultar "
            "disponibilidad. No administra usuarios, sedes, zonas ni celdas."
        ),
        "sort": 2,
    },
)


# La vista expone el directorio de cuentas con sus roles ya concatenados y
# **nunca** incluye `password_hash`.
CREATE_VIEW = sa.text(
    """
    CREATE VIEW v_user_roles AS
    SELECT u.id,
           u.parking_lot_id,
           u.employee_id,
           u.username,
           u.active,
           u.created_at,
           u.updated_at,
           u.last_login,
           e.full_name AS employee_name,
           e.document_number AS document_number,
           COALESCE(agg.role_codes, '') AS role_codes,
           COALESCE(agg.role_names, '') AS role_names
    FROM users u
    JOIN employees e ON e.id = u.employee_id
    LEFT JOIN (
        SELECT ur.user_id,
               string_agg(r.code, ',' ORDER BY r.sort, r.id) AS role_codes,
               string_agg(r.name, ',' ORDER BY r.sort, r.id) AS role_names
        FROM user_roles ur
        JOIN roles r ON r.id = ur.role_id
        GROUP BY ur.user_id
    ) agg ON agg.user_id = u.id
    """
)


def upgrade() -> None:
    """Crea las tablas nuevas, siembra el catálogo y crea la vista."""
    op.create_table(
        'roles',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('code', sa.String(length=30), nullable=False),
        sa.Column('name', sa.String(length=60), nullable=False),
        sa.Column('description', sa.String(length=240), nullable=False),
        sa.Column('sort', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code', name='uq_roles_code'),
    )

    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('parking_lot_id', sa.Integer(), nullable=False),
        sa.Column('employee_id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=60), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('last_login', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['parking_lot_id'], ['parking_lots.id']),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('employee_id', name='uq_users_employee_account'),
        sa.UniqueConstraint('parking_lot_id', 'username', name='uq_users_username_per_parking'),
    )

    op.create_table(
        'user_roles',
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('role_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['role_id'], ['roles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('user_id', 'role_id'),
    )

    op.create_table(
        'user_activity',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('parking_lot_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('employee_id', sa.Integer(), nullable=True),
        sa.Column('action', sa.String(length=40), nullable=False),
        sa.Column('detail', sa.String(length=240), nullable=False),
        sa.Column('actor', sa.String(length=60), nullable=False),
        sa.Column('occurred_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['parking_lot_id'], ['parking_lots.id']),
        sa.ForeignKeyConstraint(['employee_id'], ['employees.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_user_activity_parking_lot', 'user_activity', ['parking_lot_id', 'occurred_at'])

    roles = sa.table(
        'roles',
        sa.column('code', sa.String()),
        sa.column('name', sa.String()),
        sa.column('description', sa.String()),
        sa.column('sort', sa.Integer()),
    )
    for role in ROLE_CATALOG:
        op.bulk_insert(roles, [role])

    op.execute(CREATE_VIEW)


def downgrade() -> None:
    """Elimina únicamente los objetos creados por esta revisión."""
    op.drop_index('ix_user_activity_parking_lot', table_name='user_activity')
    op.execute('DROP VIEW IF EXISTS v_user_roles')
    op.drop_table('user_activity')
    op.drop_table('user_roles')
    op.drop_table('users')
    op.drop_table('roles')
