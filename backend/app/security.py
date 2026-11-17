"""Credenciales: hash y verificación de contraseñas.

Se usa PBKDF2-HMAC-SHA256 de la biblioteca estándar para no añadir
dependencias al proyecto. El formato almacenado es:

    pbkdf2_sha256$<iteraciones>$<salto en hexadecimal>$<hash en hexadecimal>

La contraseña en texto plano nunca se guarda, ni en `users` ni en
`user_activity`, y nunca se devuelve en una respuesta de la API.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets

ALGORITHM = "pbkdf2_sha256"
ITERATIONS = 210_000
SALT_BYTES = 16
DIGEST_BYTES = 32


def hash_password(password: str) -> str:
    """Devuelve el hash con salto aleatorio listo para almacenar."""
    salt = secrets.token_bytes(SALT_BYTES)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS, DIGEST_BYTES)
    return f"{ALGORITHM}${ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str | None) -> bool:
    """Comprueba una contraseña contra su hash de forma constante en tiempo."""
    if not stored:
        return False
    try:
        algorithm, iterations, salt_hex, digest_hex = stored.split("$")
        iterations_count = int(iterations)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
    except (ValueError, AttributeError):
        return False
    if algorithm != ALGORITHM or iterations_count <= 0:
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations_count, len(expected))
    return hmac.compare_digest(digest, expected)
