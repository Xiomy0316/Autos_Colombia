"""Roles canónicos y cambio de contraseña obligatorio.

No crea tablas nuevas, no elimina datos y no toca columnas heredadas de
`employees`. Solo normaliza los códigos de `roles` (ADMIN -> ADMINISTRADOR,
OPERATOR -> EMPLEADO), conservando los ids y las asignaciones existentes, y
añade una columna booleana a `users`.

Revision ID: a1b2c3d4e5f6
Revises: c3e7a91f5b22
Create Date: 2026-11-17
"""

from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e5f6"
down_revision = "c3e7a91f5b22"
branch_labels = None
depends_on = None

LEGACY = (("ADMIN", "ADMINISTRADOR"), ("OPERATOR", "EMPLEADO"))


def upgrade() -> None:
    # Renombrar en la misma fila mantiene user_roles y el historial intactos.
    for old, new in LEGACY:
        op.execute(
            sa.text(
                "UPDATE roles SET code = :new, "
                "description = CASE WHEN code = :old THEN "
                "'Rol canónico de Autos Colombia: ' || name END "
                "WHERE code = :old AND NOT EXISTS "
                "(SELECT 1 FROM roles r2 WHERE r2.code = :new)"
            ).bindparams(old=old, new=new)
        )
    op.add_column(
        "users",
        sa.Column("must_change_password", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade() -> None:
    op.drop_column("users", "must_change_password")
    for old, new in reversed(LEGACY):
        op.execute(
            sa.text(
                "UPDATE roles SET code = :old WHERE code = :new "
                "AND NOT EXISTS (SELECT 1 FROM roles r2 WHERE r2.code = :old)"
            ).bindparams(old=old, new=new)
        )
