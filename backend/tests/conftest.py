import os
import sys
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Las pruebas corren contra PostgreSQL, en una base propia para no tocar datos
# reales. Se deriva de DATABASE_URL conservando usuario, clave y servidor.
configured = os.environ.get("DATABASE_URL", "").strip()
if not configured:
    raise RuntimeError(
        "Define DATABASE_URL antes de ejecutar las pruebas: "
        "las pruebas usan PostgreSQL y se derivan de esa conexión."
    )

parsed = urlparse(configured)
if not parsed.scheme.startswith("postgresql"):
    raise RuntimeError(f"Las pruebas usan PostgreSQL. DATABASE_URL recibida: {parsed.scheme}://")

os.environ["DATABASE_URL"] = configured.rsplit("/", 1)[0] + "/autos_colombia_test"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app.database import Base, engine  # noqa: E402
from app.main import app, seed_database  # noqa: E402
from app.views import drop_reporting_views  # noqa: E402


def reset_schema() -> None:
    """Retira la vista propia antes de `drop_all()`: si no, PG bloquea el DROP."""
    with engine.begin() as connection:
        drop_reporting_views(connection)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with Session(bind=engine) as db:
        seed_database(db)


@pytest.fixture
def client():
    reset_schema()
    with TestClient(app) as test_client:
        yield test_client
    reset_schema()
