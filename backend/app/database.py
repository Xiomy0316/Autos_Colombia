import os
from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

# Este proyecto funciona exclusivamente con PostgreSQL: no existe ningún
# respaldo en SQLite. Si falta la conexión, el proceso no debe arrancar.
POSTGRESQL_PREFIXES = ("postgresql://", "postgresql+")


def _normalize_postgres_url(url: str, source: str) -> str:
    """Normaliza y valida una URL de PostgreSQL.

    Render y Heroku entregan el esquema heredado `postgres://` y SQLAlchemy 2 ya
    no lo admite, así que se convierte al driver `psycopg` antes de validar.
    """
    if url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url[len("postgres://"):]
    if not url.startswith(POSTGRESQL_PREFIXES):
        scheme = url.split(":", 1)[0]
        raise RuntimeError(
            f"{source} debe apuntar a PostgreSQL (postgresql+psycopg://...). Recibido: {scheme}://"
        )
    return url


def load_database_url() -> str:
    """Valida `DATABASE_URL` y devuelve la conexión a PostgreSQL.

    Es la cadena que usa la aplicación en funcionamiento: en Neon, la que pasa
    por el pooler.
    """
    url = os.getenv("DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError(
            "DATABASE_URL no está definida. Este proyecto usa únicamente PostgreSQL: "
            "copia .env.example a .env, completa la conexión y vuelve a iniciar."
        )
    return _normalize_postgres_url(url, "DATABASE_URL")


def load_migration_database_url() -> str:
    """URL que usa Alembic para aplicar las migraciones.

    Neon publica dos cadenas para la misma base: `DATABASE_URL` (a través del
    pooler, para el tráfico normal) y `DATABASE_URL_UNPOOLED` (conexión
    directa). Las migraciones van por la directa porque el pooler trabaja en
    modo transacción y no conserva el estado de sesión (`SET`, `search_path`,
    transacciones explícitas) que Alembic necesita; falla de formas que no
    mencionan el pooling, como `prepared statement "s0" already exists`.

    Si `DATABASE_URL_UNPOOLED` no está definida (por ejemplo, un PostgreSQL
    local), se usa `DATABASE_URL` como hasta ahora.
    """
    unpooled = os.getenv("DATABASE_URL_UNPOOLED", "").strip()
    if not unpooled:
        return load_database_url()
    return _normalize_postgres_url(unpooled, "DATABASE_URL_UNPOOLED")


DATABASE_URL = load_database_url()
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
