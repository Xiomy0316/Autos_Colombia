"""Pruebas del módulo Administración · Usuarios.

Cubre: catálogo de roles, alta/edición de cuentas con hash de contraseña,
bitácora administrativa, autorización por rol en FastAPI y aislamiento por
`parking_lot_id`.
"""

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.database import engine
from app.models import UserAccount, UserActivity
from app.security import verify_password


def role_ids(client, *codes):
    """Devuelve los ids del catálogo para los códigos indicados."""
    roles = client.get("/api/roles").json()
    return [next(role for role in roles if role["code"] == code)["id"] for code in codes]


def create_employee(client, username, full_name="Persona de prueba", parking_lot_id=1, document="1.000.001"):
    response = client.post("/api/employees", json={
        "parking_lot_id": parking_lot_id,
        "full_name": full_name,
        "document_number": document,
        "username": username,
        "role": "OPERATOR",
    })
    assert response.status_code == 201, response.text
    return response.json()


def create_user(client, employee_id, username, *, parking_lot_id=1, roles=("OPERATOR",),
                password="clave-segura-123", actor=None):
    """Crea una cuenta. `actor` es la cabecera X-Actor-Username (requerida
    cuando el parqueadero ya tiene al menos una cuenta)."""
    headers = {"X-Actor-Username": actor} if actor else {}
    return client.post("/api/users", json={
        "parking_lot_id": parking_lot_id,
        "employee_id": employee_id,
        "username": username,
        "password": password,
        "role_ids": role_ids(client, *roles),
    }, headers=headers)


def test_role_catalog_matches_existing_codes_without_duplicates(client):
    """Los códigos son los que el proyecto ya usa: ADMIN y OPERATOR."""
    roles = client.get("/api/roles")
    assert roles.status_code == 200
    codes = [role["code"] for role in roles.json()]
    assert codes == ["ADMIN", "OPERATOR"], codes
    admin = next(role for role in roles.json() if role["code"] == "ADMIN")
    operator = next(role for role in roles.json() if role["code"] == "OPERATOR")
    assert "MANAGE_ACCOUNTS" in admin["permissions"]
    assert "VIEW_ACTIVITY" in admin["permissions"]
    assert "MANAGE_ACCOUNTS" not in operator["permissions"]
    assert "VIEW_ACTIVITY" not in operator["permissions"]
    assert operator["description"] and admin["description"]


def test_create_user_stores_a_hash_and_never_exposes_it(client):
    employee = create_employee(client, "camila.torres", "Camila Torres")
    response = create_user(client, employee["id"], "camila.torres", roles=("OPERATOR",))
    assert response.status_code == 201, response.text

    payload = response.json()
    assert "password" not in payload and "password_hash" not in payload
    assert payload["username"] == "camila.torres"
    assert payload["active"] is True
    assert payload["role_codes"] == ["OPERATOR"]
    assert payload["employee_name"] == "Camila Torres"

    # El hash vive en la base y no es la contraseña en claro.
    with Session(bind=engine) as db:
        stored = db.scalar(select(UserAccount).where(UserAccount.username == "camila.torres"))
        assert stored is not None
        assert stored.password_hash != "clave-segura-123"
        assert stored.password_hash.startswith("pbkdf2_sha256$")
        assert verify_password("clave-segura-123", stored.password_hash)

    # Ni el listado ni la vista devuelven la contraseña.
    listing = client.get("/api/users")
    assert listing.status_code == 200
    assert "clave-segura-123" not in listing.text
    assert "password_hash" not in listing.text
    with Session(bind=engine) as db:
        columns = {column.name for column in UserAccount.__table__.columns}
        assert "password_hash" in columns
        view_columns = db.execute(
            text("select column_name from information_schema.columns where table_name='v_user_roles'")
        ).scalars().all()
        assert "password_hash" not in view_columns


def test_username_and_password_validation_messages(client):
    employee = create_employee(client, "camila.torres", "Camila Torres")
    short_password = create_user(client, employee["id"], "camila.torres", password="12345678")
    assert short_password.status_code == 422
    assert short_password.json()["detail"] == "No cumple la política propuesta: usa al menos 12 caracteres."

    invalid_username = client.post("/api/users", json={
        "parking_lot_id": 1, "employee_id": employee["id"], "username": "Camila Torres!",
        "password": "clave-segura-123", "role_ids": role_ids(client, "OPERATOR"),
    })
    assert invalid_username.status_code == 422
    assert "Formato inválido" in invalid_username.json()["detail"]

    empty_username = client.post("/api/users", json={
        "parking_lot_id": 1, "employee_id": employee["id"], "username": "",
        "password": "clave-segura-123", "role_ids": role_ids(client, "OPERATOR"),
    })
    assert empty_username.status_code == 422
    assert empty_username.json()["detail"] == "El usuario es obligatorio."

    without_role = client.post("/api/users", json={
        "parking_lot_id": 1, "employee_id": employee["id"], "username": "camila.torres",
        "password": "clave-segura-123", "role_ids": [],
    })
    assert without_role.status_code == 422
    assert without_role.json()["detail"] == "Selecciona Administrador o Empleado."

    unknown_employee = client.post("/api/users", json={
        "parking_lot_id": 1, "employee_id": 999999, "username": "camila.torres",
        "password": "clave-segura-123", "role_ids": role_ids(client, "OPERATOR"),
    })
    assert unknown_employee.status_code == 404


def test_duplicate_username_and_double_account_are_rejected(client):
    diego = create_employee(client, "diego.ramirez", "Diego Ramírez", document="2.000.002")
    camila = create_employee(client, "camila.torres", "Camila Torres", document="3.000.003")

    first = create_user(client, diego["id"], "diego.ramirez", roles=("ADMIN",))
    assert first.status_code == 201, first.text

    duplicate = create_user(client, camila["id"], "diego.ramirez", actor="diego.ramirez")
    assert duplicate.status_code == 409
    assert "Diego Ramírez" in duplicate.json()["detail"]

    twice = create_user(client, diego["id"], "otro.usuario", actor="diego.ramirez")
    assert twice.status_code == 409
    assert "ya tiene una cuenta" in twice.json()["detail"]


def test_update_user_can_change_roles_and_password_without_logging_them(client):
    boss = create_employee(client, "laura.martinez", "Laura Martínez")
    create_user(client, boss["id"], "laura.martinez", roles=("ADMIN",))
    employee = create_employee(client, "diego.ramirez", "Diego Ramírez")
    created = create_user(client, employee["id"], "diego.ramirez", roles=("OPERATOR",),
                          actor="laura.martinez")
    user_id = created.json()["id"]
    admin_actor = {"X-Actor-Username": "laura.martinez"}

    admin_role = role_ids(client, "ADMIN")
    updated = client.patch(f"/api/users/{user_id}", json={
        "role_ids": admin_role, "password": "otra-clave-segura-1",
    }, headers=admin_actor)
    assert updated.status_code == 200, updated.text
    assert updated.json()["role_codes"] == ["ADMIN"]

    with Session(bind=engine) as db:
        user = db.scalar(select(UserAccount).where(UserAccount.id == user_id))
        assert verify_password("otra-clave-segura-1", user.password_hash)
        assert not verify_password("clave-segura-123", user.password_hash)
        actions = [row.action for row in db.scalars(
            select(UserActivity).where(UserActivity.user_id == user_id).order_by(UserActivity.id)
        )]
        assert "USER_UPDATED" in actions
        assert "ROLES_UPDATED" in actions
        assert "PASSWORD_CHANGED" in actions

    # La bitácora nunca conserva la contraseña ni el hash.
    activity = client.get("/api/users/activity", headers=admin_actor)
    assert activity.status_code == 200
    assert "otra-clave-segura-1" not in activity.text
    assert "pbkdf2" not in activity.text


def test_activation_and_deactivation_are_recorded(client):
    # Un administrador distinto actúa: la cuenta desactivada no puede autorizar.
    boss = create_employee(client, "laura.martinez", "Laura Martínez")
    create_user(client, boss["id"], "laura.martinez", roles=("ADMIN",))
    employee = create_employee(client, "oscar.valencia", "Óscar Valencia")
    user_id = create_user(client, employee["id"], "oscar.valencia", roles=("OPERATOR",),
                          actor="laura.martinez").json()["id"]
    actor = {"X-Actor-Username": "laura.martinez"}

    deactivated = client.patch(f"/api/users/{user_id}/status", json={"active": False}, headers=actor)
    assert deactivated.status_code == 200
    assert deactivated.json()["active"] is False

    activated = client.patch(f"/api/users/{user_id}/status", json={"active": True}, headers=actor)
    assert activated.status_code == 200
    assert activated.json()["active"] is True

    activity = client.get("/api/users/activity", headers=actor)
    assert activity.status_code == 200
    actions = [item["action"] for item in activity.json()]
    assert "USER_DEACTIVATED" in actions
    assert "USER_ACTIVATED" in actions
    assert activity.json()[0]["username"] == "oscar.valencia"


def test_writes_require_an_administrator_actor(client):
    """Bootstrap: la primera cuenta no necesita actor. Después, sí."""
    employee = create_employee(client, "laura.martinez", "Laura Martínez")
    first = create_user(client, employee["id"], "laura.martinez", roles=("ADMIN",))
    assert first.status_code == 201

    other = create_employee(client, "diego.ramirez", "Diego Ramírez")
    without_actor = create_user(client, other["id"], "diego.ramirez")
    assert without_actor.status_code == 401

    operator_employee = create_employee(client, "camila.torres", "Camila Torres")
    operator_create = client.post("/api/users", json={
        "parking_lot_id": 1, "employee_id": operator_employee["id"], "username": "camila.torres",
        "password": "clave-segura-123", "role_ids": role_ids(client, "OPERATOR"),
    }, headers={"X-Actor-Username": "laura.martinez"})
    assert operator_create.status_code == 201

    # El operador no puede crear cuentas.
    another = create_employee(client, "otra.persona", "Otra Persona")
    forbidden = client.post("/api/users", json={
        "parking_lot_id": 1, "employee_id": another["id"], "username": "otra.persona",
        "password": "clave-segura-123", "role_ids": role_ids(client, "OPERATOR"),
    }, headers={"X-Actor-Username": "camila.torres"})
    assert forbidden.status_code == 403
    assert "Administrador" in forbidden.json()["detail"]

    # Un actor inexistente en el parqueadero tampoco puede actuar.
    unknown_actor = client.post("/api/users", json={
        "parking_lot_id": 1, "employee_id": another["id"], "username": "otra.persona",
        "password": "clave-segura-123", "role_ids": role_ids(client, "OPERATOR"),
    }, headers={"X-Actor-Username": "intruso"})
    assert unknown_actor.status_code == 403


def test_activity_log_requires_administrator(client):
    employee = create_employee(client, "laura.martinez", "Laura Martínez")
    create_user(client, employee["id"], "laura.martinez", roles=("ADMIN",))
    operator_employee = create_employee(client, "camila.torres", "Camila Torres")
    client.post("/api/users", json={
        "parking_lot_id": 1, "employee_id": operator_employee["id"], "username": "camila.torres",
        "password": "clave-segura-123", "role_ids": role_ids(client, "OPERATOR"),
    }, headers={"X-Actor-Username": "laura.martinez"})

    open_read = client.get("/api/users/activity")
    assert open_read.status_code == 401

    operator_read = client.get("/api/users/activity", headers={"X-Actor-Username": "camila.torres"})
    assert operator_read.status_code == 403

    admin_read = client.get("/api/users/activity", headers={"X-Actor-Username": "laura.martinez"})
    assert admin_read.status_code == 200
    assert any(item["action"] == "USER_CREATED" for item in admin_read.json())

    available = client.get("/api/users/employees-available")
    assert available.status_code == 401


def test_parking_lot_isolation(client):
    """Una cuenta de un parqueadero no ve ni modifica datos de otro."""
    admin = role_ids(client, "ADMIN")
    first = create_employee(client, "laura.martinez", "Laura Martínez")
    create_user(client, first["id"], "laura.martinez", roles=("ADMIN",))

    other_lot = client.post("/api/parking-lots", json={"name": "Sede Norte", "city": "Bogotá"})
    assert other_lot.status_code == 201, other_lot.text
    other_id = other_lot.json()["id"]

    other_employee = create_employee(client, "persona.norte", "Persona Norte", parking_lot_id=other_id)
    north_user = client.post("/api/users", json={
        "parking_lot_id": other_id, "employee_id": other_employee["id"], "username": "persona.norte",
        "password": "clave-segura-123", "role_ids": admin,
    }, headers={"X-Actor-Username": "persona.norte"})
    assert north_user.status_code == 201, north_user.text

    lot_one = {user["username"] for user in client.get("/api/users", params={"parking_lot_id": 1}).json()}
    lot_two = {user["username"] for user in client.get("/api/users", params={"parking_lot_id": other_id}).json()}
    assert lot_one == {"laura.martinez"}
    assert lot_two == {"persona.norte"}

    # Un administrador del lote 2 no puede tocar cuentas del lote 1.
    target = next(user for user in client.get("/api/users", params={"parking_lot_id": 1}).json()
                  if user["username"] == "laura.martinez")
    cross = client.patch(f"/api/users/{target['id']}", params={"parking_lot_id": 1},
                         json={"active": False}, headers={"X-Actor-Username": "persona.norte"})
    assert cross.status_code == 403

    # Los empleados de un lote no aparecen en el alta del otro.
    available_one = client.get("/api/users/employees-available", params={"parking_lot_id": 1},
                               headers={"X-Actor-Username": "laura.martinez"})
    assert available_one.status_code == 200
    assert all(item["parking_lot_id"] == 1 for item in available_one.json())


def test_employees_without_account_are_listed(client):
    laura = create_employee(client, "laura.martinez", "Laura Martínez")
    create_user(client, laura["id"], "laura.martinez", roles=("ADMIN",))
    camila = create_employee(client, "camila.torres", "Camila Torres")

    available = client.get("/api/users/employees-available", headers={"X-Actor-Username": "laura.martinez"})
    assert available.status_code == 200
    usernames = [item["username"] for item in available.json()]
    assert usernames == ["camila.torres"]

    client.post("/api/users", json={
        "parking_lot_id": 1, "employee_id": camila["id"], "username": "camila.torres",
        "password": "clave-segura-123", "role_ids": role_ids(client, "OPERATOR"),
    }, headers={"X-Actor-Username": "laura.martinez"})
    after = client.get("/api/users/employees-available", headers={"X-Actor-Username": "laura.martinez"})
    assert after.json() == []


def test_directory_filters_and_empty_result(client):
    laura = create_employee(client, "laura.martinez", "Laura Martínez")
    create_user(client, laura["id"], "laura.martinez", roles=("ADMIN",))
    diego = create_employee(client, "diego.ramirez", "Diego Ramírez")
    create_user(client, diego["id"], "diego.ramirez", roles=("OPERATOR",), actor="laura.martinez")

    by_role = client.get("/api/users", params={"role": "ADMIN"}).json()
    assert [item["username"] for item in by_role] == ["laura.martinez"]

    by_search = client.get("/api/users", params={"search": "ramirez"}).json()
    assert [item["username"] for item in by_search] == ["diego.ramirez"]

    by_status = client.get("/api/users", params={"status": "INACTIVE"}).json()
    assert by_status == []

    no_match = client.get("/api/users", params={"search": "no.existe"}).json()
    assert no_match == []


def test_access_check_reports_credentials_and_inactive_state(client):
    employee = create_employee(client, "oscar.valencia", "Óscar Valencia")
    create_user(client, employee["id"], "oscar.valencia", roles=("ADMIN",))

    bad = client.post("/api/users/access-check", json={
        "parking_lot_id": 1, "username": "oscar.valencia", "password": "clave-distinta-1",
    })
    assert bad.status_code == 200
    assert bad.json()["status"] == "BAD_CREDENTIALS"

    ok = client.post("/api/users/access-check", json={
        "parking_lot_id": 1, "username": "oscar.valencia", "password": "clave-segura-123",
    })
    assert ok.json()["status"] == "OK"

    inactive = client.patch("/api/users/1/status", json={"active": False},
                            headers={"X-Actor-Username": "oscar.valencia"})
    assert inactive.status_code == 200
    checked = client.post("/api/users/access-check", json={
        "parking_lot_id": 1, "username": "oscar.valencia", "password": "clave-segura-123",
    })
    assert checked.json()["status"] == "INACTIVE"
    assert "No se inició sesión" in checked.json()["message"]
