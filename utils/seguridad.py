import base64
import hashlib
import hmac
import os
import secrets
from datetime import timedelta, timezone
from typing import Optional

import jwt
from dotenv import load_dotenv

from utils.horario import ahora_utc

load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    raise RuntimeError("Falta JWT_SECRET. Revisa el archivo .env.")

ALGORITMO = "HS256"

# La sesión del panel dura una jornada; después hay que volver a entrar.
HORAS_DE_SESION = 12

LARGO_MINIMO_DE_CONTRASENA = 8

# Parámetros de scrypt (recomendados para contraseñas); se guardan junto al hash.
SCRYPT_N, SCRYPT_R, SCRYPT_P = 2**14, 8, 1


def _derivar(contrasena: str, sal: bytes, n: int, r: int, p: int) -> bytes:
    return hashlib.scrypt(contrasena.encode("utf-8"), salt=sal, n=n, r=r, p=p, dklen=32)


def _b64(datos: bytes) -> str:
    return base64.b64encode(datos).decode("ascii")


def hash_de_contrasena(contrasena: str) -> str:
    # Nunca se guarda la contraseña: solo este resumen, que no se puede revertir.
    sal = secrets.token_bytes(16)
    resumen = _derivar(contrasena, sal, SCRYPT_N, SCRYPT_R, SCRYPT_P)
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${_b64(sal)}${_b64(resumen)}"


def contrasena_correcta(contrasena: str, guardado: str) -> bool:
    try:
        metodo, n, r, p, sal, resumen = guardado.split("$")
        if metodo != "scrypt":
            return False
        calculado = _derivar(contrasena, base64.b64decode(sal), int(n), int(r), int(p))
        return hmac.compare_digest(calculado, base64.b64decode(resumen))
    except (ValueError, TypeError):
        return False


def crear_token(administrador_id: int, ahora=None) -> str:
    # Las fechas del sistema son UTC sin zona; aquí hay que decirlo explícitamente.
    vence = (ahora or ahora_utc()) + timedelta(hours=HORAS_DE_SESION)
    datos = {
        "sub": str(administrador_id),
        "exp": int(vence.replace(tzinfo=timezone.utc).timestamp()),
    }
    return jwt.encode(datos, JWT_SECRET, algorithm=ALGORITMO)


def leer_token(token: str) -> Optional[int]:
    # Devuelve el id del administrador, o None si el token es falso o ya venció.
    try:
        datos = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITMO])
        return int(datos["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None
