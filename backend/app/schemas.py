from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class CustomerCreate(BaseModel):
    parking_lot_id: int
    document_type: str = "CC"
    document_number: str = Field(min_length=3, max_length=40)
    full_name: str = Field(min_length=2, max_length=160)
    phone: str = ""
    email: str = ""


class VehicleCreate(BaseModel):
    parking_lot_id: int
    customer_id: int
    vehicle_type_id: int
    plate: str = Field(min_length=4, max_length=12)
    brand: str
    color: str


class CellCreate(BaseModel):
    zone_id: int
    code: str = Field(min_length=1, max_length=30)
    compatible_type_ids: list[int] = Field(min_length=1)
    description: str = ""


class CellUpdate(BaseModel):
    """Edición de una celda: solo los campos enviados se modifican."""

    zone_id: int | None = None
    code: str | None = Field(default=None, min_length=1, max_length=30)
    compatible_type_ids: list[int] | None = Field(default=None, min_length=1)
    description: str | None = Field(default=None, max_length=200)


class CellStatusUpdate(BaseModel):
    operational_status: str
    #: Motivo del cambio. La UI lo exige; la API lo recibe opcional para no
    #: romper llamadas existentes y lo guarda en `cell_status_events`.
    reason: str = Field(default="", max_length=240)


class SiteCreate(BaseModel):
    parking_lot_id: int
    name: str
    address: str = ""


class ZoneCreate(BaseModel):
    site_id: int
    name: str
    code: str = ""


class EntryCreate(BaseModel):
    vehicle_id: int
    cell_id: int
    notes: str = ""


class PaymentCreate(BaseModel):
    vehicle_id: int
    months: int = Field(default=1, ge=1, le=24)
    method: str = "CASH"
    paid_at: datetime | None = None
    notes: str = ""


class NoveltyCreate(BaseModel):
    vehicle_id: int
    category: str = "GENERAL"
    description: str = Field(min_length=3, max_length=500)


class ParkingLotCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    tax_id: str | None = None
    city: str = ""
    address: str = ""


class ParkingLotUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=120)
    tax_id: str | None = None
    city: str | None = None
    address: str | None = None
    active: bool | None = None


class EmployeeCreate(BaseModel):
    parking_lot_id: int
    document_number: str = ""
    full_name: str = Field(min_length=2, max_length=160)
    username: str = Field(min_length=3, max_length=60)
    role: str = "OPERATOR"
    shift_id: int | None = None


class EmployeeUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=2, max_length=160)
    username: str | None = Field(default=None, min_length=3, max_length=60)
    role: str | None = None
    shift_id: int | None = None
    active: bool | None = None


class ShiftCreate(BaseModel):
    parking_lot_id: int
    name: str = Field(min_length=2, max_length=80)
    starts_at: str = Field(pattern=r"^\d{2}:\d{2}$")
    ends_at: str = Field(pattern=r"^\d{2}:\d{2}$")
    notes: str = ""


class ShiftUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=80)
    starts_at: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    ends_at: str | None = Field(default=None, pattern=r"^\d{2}:\d{2}$")
    notes: str | None = None
    active: bool | None = None


class TariffCreate(BaseModel):
    vehicle_type_id: int
    amount: Decimal = Field(gt=0)
    effective_from: date
    effective_until: date | None = None
    note: str = ""


# --------------------------------------------------------------------------- #
# Administración · cuentas de acceso (módulo Usuarios)                          #
# --------------------------------------------------------------------------- #

class RoleOut(BaseModel):
    """Catálogo de roles con los permisos que la API valida en sus endpoints."""

    id: int
    code: str
    name: str
    description: str = ""
    permissions: list[str] = []


class UserCreate(BaseModel):
    """Alta de cuenta: se vincula a un empleado ya registrado.

    El formato y el largo de `username`/`password` se validan en el endpoint
    para devolver los mensajes en español del módulo.
    """

    parking_lot_id: int
    employee_id: int
    username: str = ""
    password: str = ""
    role_ids: list[int] = []
    active: bool = True


class UserUpdate(BaseModel):
    """Edición de cuenta. Las claves ausentes conservan su valor actual."""

    username: str | None = None
    password: str | None = None
    role_ids: list[int] | None = None
    active: bool | None = None


class UserStatusUpdate(BaseModel):
    active: bool


class UserAccessCheck(BaseModel):
    """Comprobación de credenciales sin crear sesión."""

    parking_lot_id: int
    username: str = ""
    password: str = ""
