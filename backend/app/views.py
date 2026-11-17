"""Vistas de lectura del esquema `public`.

Las vistas no viven en `Base.metadata`, así que `create_all()` (arranque del
servicio y pruebas) no las crea ni las elimina. Este módulo centraliza su SQL
para que la migración de Alembic y los flujos basados en `create_all()` usen
la misma definición.
"""

from sqlalchemy import text

#: Vistas que puede crear y eliminar esta aplicación.
REPORT_VIEWS = ("v_user_roles",)

CREATE_V_USER_ROLES = text(
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


def ensure_reporting_views(connection) -> None:
    """Crea las vistas que falten sobre una conexión. Idempotente.

    Se pasa siempre una conexión (`engine.begin()`), no el engine.
    """
    for view in REPORT_VIEWS:
        exists = connection.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.views "
                "WHERE table_schema = 'public' AND table_name = :name"
            ),
            {"name": view},
        ).scalar()
        if exists:
            continue
        if view == "v_user_roles":
            connection.execute(CREATE_V_USER_ROLES)


def drop_reporting_views(connection) -> None:
    """Retira las vistas propias; se usa antes de `drop_all()` en las pruebas."""
    for view in reversed(REPORT_VIEWS):
        connection.execute(text(f"DROP VIEW IF EXISTS {view}"))  # nombre fijo de REPORT_VIEWS
