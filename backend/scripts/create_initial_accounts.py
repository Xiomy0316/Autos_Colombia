"""Alta idempotente de las dos cuentas iniciales de Autos Colombia.

Uso (documentos obligatorios, NO se inventan):
    python scripts/create_initial_accounts.py \
        --laura-document <documento> --oscar-document <documento> \
        --laura-password '<temporal>' --oscar-password '<temporal>'

Solo lectura si las cuentas ya existen: no duplica empleados, usuarios ni
roles. No elimina ni modifica registros ajenos. Usa las tablas existentes.
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select  # noqa: E402
from sqlalchemy.exc import IntegrityError  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.database import SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    Employee, ParkingLot, Role, UserAccount, UserActivity, UserRole,
)
from app.rbac import ROLE_ADMIN, ROLE_EMPLOYEE  # noqa: E402
from app.security import hash_password  # noqa: E402

ACCOUNTS = (
    {
        "key": "laura",
        "full_name": "Laura Martínez",
        "username": "laura.martinez",
        "role": ROLE_ADMIN,
    },
    {
        "key": "oscar",
        "full_name": "Oscar Valencia",
        "username": "oscar.valencia",
        "role": ROLE_EMPLOYEE,
    },
)


def find_or_create_employee(db: Session, lot_id: int, spec: dict, document: str) -> tuple[Employee, bool]:
    """Reutiliza un empleado por nombre o usuario; nunca inventa documentos."""
    existing = db.scalar(
        select(Employee).where(
            Employee.parking_lot_id == lot_id,
            Employee.full_name.ilike(spec["full_name"]),
        )
    )
    if existing:
        return existing, False
    existing = db.scalar(
        select(Employee).where(
            Employee.parking_lot_id == lot_id,
            Employee.username == spec["username"],
        )
    )
    if existing:
        return existing, False
    clash = db.scalar(
        select(Employee).where(
            Employee.parking_lot_id == lot_id,
            Employee.document_number == document,
        )
    )
    if clash:
        raise RuntimeError(
            f"El documento {document} ya pertenece a {clash.full_name}; "
            "no se creó el empleado para evitar duplicados."
        )
    employee = Employee(
        parking_lot_id=lot_id,
        document_number=document,
        full_name=spec["full_name"],
        username=spec["username"],
        password_hash=None,
        role=spec["role"],
        active=True,
    )
    db.add(employee)
    db.flush()
    return employee, True


def ensure_account(db: Session, lot_id: int, spec: dict, password: str) -> tuple[UserAccount, bool, bool]:
    """Devuelve (cuenta, creada, contraseña_actualizada)."""
    role = db.scalar(select(Role).where(Role.code == spec["role"]))
    if not role:
        raise RuntimeError(f"No existe el rol {spec['role']}; ejecuta primero las migraciones.")

    user = db.scalar(
        select(UserAccount).where(
            UserAccount.parking_lot_id == lot_id,
            UserAccount.username == spec["username"],
        )
    )
    created = False
    password_updated = False
    if not user:
        employee, _ = find_or_create_employee(db, lot_id, spec, _DOCUMENTS[spec["key"]])
        if db.scalar(select(UserAccount).where(UserAccount.employee_id == employee.id)):
            raise RuntimeError(f"El empleado {employee.full_name} ya tiene otra cuenta de acceso.")
        user = UserAccount(
            parking_lot_id=lot_id,
            employee_id=employee.id,
            username=spec["username"],
            password_hash=hash_password(password),
            active=True,
            must_change_password=True,
        )
        db.add(user)
        db.flush()
        created = True
    else:
        employee = db.get(Employee, user.employee_id)
        if not employee or employee.parking_lot_id != lot_id:
            raise RuntimeError(f"La cuenta {user.username} no está vinculada a un empleado de este parqueadero.")

    assigned = set(db.scalars(select(UserRole.role_id).where(UserRole.user_id == user.id)))
    if assigned != {role.id}:
        for row in db.scalars(select(UserRole).where(UserRole.user_id == user.id)).all():
            db.delete(row)
        db.add(UserRole(user_id=user.id, role_id=role.id))

    if not user.active:
        user.active = True
        user.updated_at = datetime.now()
    if created:
        db.add(UserActivity(
            parking_lot_id=lot_id,
            user_id=user.id,
            employee_id=employee.id,
            action="USER_CREATED",
            detail=f"Cuenta inicial · {role.name}",
            actor="Sistema · alta inicial",
        ))
    return user, created, password_updated


_DOCUMENTS: dict[str, str] = {}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for spec in ACCOUNTS:
        key = spec["key"]
        parser.add_argument(f"--{key}-document", required=True, help=f"Documento real de {spec['full_name']}")
        parser.add_argument(f"--{key}-password", required=True, help=f"Contraseña temporal de {spec['username']}")
    parser.add_argument("--parking-lot-id", type=int, default=None, help="Parqueadero (por defecto, el primero)")
    args = parser.parse_args()

    for spec in ACCOUNTS:
        key = spec["key"]
        document = getattr(args, f"{key}_document").strip()
        password = getattr(args, f"{key}_password")
        if not document:
            parser.error(f"El documento de {spec['full_name']} no puede estar vacío.")
        if len(password) < 12:
            parser.error(f"La contraseña de {spec['username']} debe tener al menos 12 caracteres.")
        _DOCUMENTS[key] = document

    db: Session = SessionLocal()
    try:
        lot_id = args.parking_lot_id or db.scalar(select(ParkingLot.id).order_by(ParkingLot.id).limit(1))
        if not lot_id:
            raise RuntimeError("No hay parqueaderos registrados.")
        for spec in ACCOUNTS:
            user, created, _ = ensure_account(db, lot_id, spec, getattr(args, f"{spec['key']}_password"))
            print(
                f"{'CREADA' if created else 'YA EXISTE'}: {user.username} "
                f"({spec['full_name']}) · rol {spec['role']} · activa={user.active}"
            )
        db.commit()
        print(f"Parqueadero usado: {lot_id}. No se crearon roles ni tablas duplicadas.")
        return 0
    except (RuntimeError, IntegrityError) as exc:
        db.rollback()
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
