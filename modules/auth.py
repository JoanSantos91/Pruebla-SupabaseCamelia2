"""Autenticación simple compatible con la aplicación actual.

Los valores pueden sobreescribirse con variables de entorno en producción.
"""
import hashlib
import os

ADMIN_USER = os.getenv("CAMELIA_ADMIN_USER", "administrador")
ADMIN_PIN = os.getenv("CAMELIA_ADMIN_PIN", "5866")
OWNER_USER = os.getenv("CAMELIA_OWNER_USER", "Camelia Robles")
OWNER_PIN = os.getenv("CAMELIA_OWNER_PIN", "7319")
GUEST_USER = os.getenv("CAMELIA_GUEST_USER", "Invitado")
GUEST_PIN = os.getenv("CAMELIA_GUEST_PIN", "2026")


def _hash(value) -> str:
    return hashlib.sha256(str(value).encode()).hexdigest()


def authenticate(user: str, pin: str):
    normalized = user.strip().lower()
    if normalized == ADMIN_USER.lower() and _hash(pin) == _hash(ADMIN_PIN):
        return {"name": "Administrador", "role": "admin"}
    if normalized == OWNER_USER.lower() and _hash(pin) == _hash(OWNER_PIN):
        return {"name": "Camelia Robles", "role": "viewer"}
    if normalized == GUEST_USER.lower() and _hash(pin) == _hash(GUEST_PIN):
        return {"name": "Invitado", "role": "guest"}
    return None
