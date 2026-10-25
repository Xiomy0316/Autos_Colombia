import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ["DATABASE_URL"] = "sqlite:///./autos_colombia_test.db"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database import Base, engine
from app.main import app, seed_database


@pytest.fixture
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with Session(bind=engine) as db:
        seed_database(db)
    with TestClient(app) as test_client:
        yield test_client
    Base.metadata.drop_all(bind=engine)
