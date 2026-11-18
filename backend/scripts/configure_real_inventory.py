"""Configuración idempotente del inventario real de celdas de Autos Colombia.

Uso:
    python scripts/configure_real_inventory.py --carros 80 --motos 10

Reglas:
    * Crea SOLO las celdas que falten; nunca borra ni modifica las existentes.
    * Celdas de carro/camioneta -> código C-001.. y compatibilidad Carro + Camioneta.
    * Celdas de moto            -> código M-001.. y compatibilidad Moto.
    * Reutiliza parqueadero, sede y zona ya existentes (no crea tablas nuevas).
    * Deja un resumen en `user_activity` con la acción INVENTORY_CONFIGURED.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import func, select  # noqa: E402
from sqlalchemy.exc import IntegrityError  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.database import SessionLocal  # noqa: E402
from app.models import (  # noqa: E402
    Cell, ParkingLot, Site, UserActivity, VehicleType, Zone, cell_vehicle_types,
)

#: (prefijo de código, tipos compatibles)
GROUPS = (
    ("C", ("Carro", "Camioneta")),
    ("M", ("Moto",)),
)


def ensure_cell(db: Session, zone_id: int, code: str) -> tuple[Cell, bool]:
    """Devuelve (celda, creada). Si ya existe, la reutiliza tal cual."""
    existing = db.scalar(select(Cell).where(Cell.zone_id == zone_id, Cell.code == code))
    if existing:
        return existing, False
    cell = Cell(zone_id=zone_id, code=code, operational_status="ACTIVE", description="")
    db.add(cell)
    db.flush()
    return cell, True


def ensure_compatibility(db: Session, cell: Cell, vehicle_type_ids: set[int]) -> int:
    """Agrega solo las compatibilidades que falten. No elimina las existentes."""
    current = {row.vehicle_type_id for row in db.execute(
        select(cell_vehicle_types.c.vehicle_type_id).where(cell_vehicle_types.c.cell_id == cell.id)
    )}
    added = 0
    for vehicle_type_id in sorted(vehicle_type_ids - current):
        db.execute(cell_vehicle_types.insert().values(cell_id=cell.id, vehicle_type_id=vehicle_type_id))
        added += 1
    return added


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--carros", type=int, default=80,
                        help="Celdas compatibles con carro/camioneta (por defecto 80)")
    parser.add_argument("--motos", type=int, default=10,
                        help="Celdas compatibles con moto (por defecto 10)")
    parser.add_argument("--parking-lot-id", type=int, default=None,
                        help="Parqueadero (por defecto, el primero)")
    parser.add_argument("--zone-id", type=int, default=None,
                        help="Zona (por defecto, la primera de la sede)")
    args = parser.parse_args()

    if args.carros < 0 or args.motos < 0:
        parser.error("Las cantidades no pueden ser negativas.")

    db: Session = SessionLocal()
    try:
        lot_id = args.parking_lot_id or db.scalar(
            select(ParkingLot.id).order_by(ParkingLot.id).limit(1)
        )
        if not lot_id:
            raise RuntimeError("No hay parqueaderos registrados.")

        site = db.scalar(
            select(Site).where(Site.parking_lot_id == lot_id).order_by(Site.id).limit(1)
        )
        if not site:
            raise RuntimeError("El parqueadero no tiene sedes; créala desde la aplicación.")

        zone = (
            db.get(Zone, args.zone_id)
            if args.zone_id
            else db.scalar(select(Zone).where(Zone.site_id == site.id).order_by(Zone.id).limit(1))
        )
        if not zone:
            raise RuntimeError("La sede no tiene zonas; créala desde la aplicación.")
        if zone.site_id != site.id:
            raise RuntimeError(f"La zona {zone.id} no pertenece a la sede {site.id}.")

        types = {t.name: t for t in db.scalars(select(VehicleType)).all()}
        missing = [name for _, names in GROUPS for name in names if name not in types]
        if missing:
            raise RuntimeError(f"Faltan tipos de vehículo: {', '.join(sorted(set(missing)))}.")

        created = reused = compat_added = 0
        for prefix, names in GROUPS:
            count = args.carros if prefix == "C" else args.motos
            wanted_ids = {types[name].id for name in names}
            for number in range(1, count + 1):
                cell, was_created = ensure_cell(db, zone.id, f"{prefix}-{number:03d}")
                created += int(was_created)
                reused += int(not was_created)
                compat_added += ensure_compatibility(db, cell, wanted_ids)

        total = db.scalar(select(func.count()).select_from(Cell).where(Cell.zone_id == zone.id))
        db.add(UserActivity(
            parking_lot_id=lot_id,
            action="INVENTORY_CONFIGURED",
            detail=(f"{args.carros} carro/camioneta + {args.motos} moto = "
                    f"{args.carros + args.motos} celdas · zona {zone.name}"),
            actor="Sistema · inventario real",
        ))
        db.commit()

        print(f"Zona usada: {zone.name} (sede {site.name}, parqueadero {lot_id}).")
        print(f"CREADAS: {created} · YA EXISTIAN: {reused} · compatibilidades agregadas: {compat_added}")
        print(f"Total de celdas en la zona: {total} "
              f"(esperado {args.carros + args.motos}).")
        print("No se borró ni modificó ninguna celda existente.")
        return 0
    except (RuntimeError, IntegrityError) as exc:
        db.rollback()
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
