from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

import Model as models
import schemas
from Conexion_DB import get_db
from utils.horario import ahora_utc
from utils.seguridad import (
    LARGO_MINIMO_DE_CONTRASENA,
    contrasena_correcta,
    crear_token,
    hash_de_contrasena,
    leer_token,
)

router = APIRouter(prefix="/acceso", tags=["Acceso"])

# Con esto, la documentación (/docs) muestra el botón "Authorize" para pegar el token.
esquema_bearer = HTTPBearer(auto_error=False)

# Freno contra quien intente adivinar contraseñas a fuerza de probar.
INTENTOS_PERMITIDOS = 5
MINUTOS_DE_BLOQUEO = 15
_intentos_fallidos: dict = {}  # usuario -> momentos de sus intentos fallidos

# Se compara contra este resumen cuando el usuario no existe, para que la
# respuesta tarde lo mismo y no delate qué nombres sí están registrados.
_HASH_DE_RELLENO = hash_de_contrasena("sin-usuario")


def normalizar_usuario(usuario: str) -> str:
    return usuario.strip().lower()


def _fallos_recientes(usuario: str, ahora) -> list:
    limite = ahora - timedelta(minutes=MINUTOS_DE_BLOQUEO)
    recientes = [momento for momento in _intentos_fallidos.get(usuario, []) if momento > limite]
    if recientes:
        _intentos_fallidos[usuario] = recientes
    else:
        _intentos_fallidos.pop(usuario, None)
    return recientes


def iniciar_sesion(db: Session, credenciales: schemas.Credenciales, ahora=None):
    ahora = ahora or ahora_utc()
    usuario = normalizar_usuario(credenciales.usuario)

    if len(_fallos_recientes(usuario, ahora)) >= INTENTOS_PERMITIDOS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Demasiados intentos. Espera {MINUTOS_DE_BLOQUEO} minutos.",
        )

    administrador = (
        db.query(models.Administrador)
        .filter(
            models.Administrador.usuario == usuario,
            models.Administrador.activo.is_(True),
        )
        .first()
    )
    guardado = administrador.contrasena_hash if administrador else _HASH_DE_RELLENO
    coincide = contrasena_correcta(credenciales.contrasena, guardado)

    if administrador is None or not coincide:
        _intentos_fallidos.setdefault(usuario, []).append(ahora)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos.",
        )

    _intentos_fallidos.pop(usuario, None)
    return {"token": crear_token(administrador.id, ahora), "administrador": administrador}


def administrador_actual(
    credenciales: Optional[HTTPAuthorizationCredentials] = Depends(esquema_bearer),
    db: Session = Depends(get_db),
) -> models.Administrador:
    # Protege las rutas del panel: sin un token vigente no se pasa.
    administrador_id = leer_token(credenciales.credentials) if credenciales else None
    administrador = None
    if administrador_id is not None:
        administrador = (
            db.query(models.Administrador)
            .filter(
                models.Administrador.id == administrador_id,
                models.Administrador.activo.is_(True),
            )
            .first()
        )

    if administrador is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Inicia sesión para continuar.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return administrador


# 1. INICIAR SESIÓN
@router.post("/", response_model=schemas.SesionResponse)
def entrar(credenciales: schemas.Credenciales, db: Session = Depends(get_db)):
    return iniciar_sesion(db, credenciales)


# 2. QUIÉN TIENE LA SESIÓN ABIERTA
@router.get("/yo", response_model=schemas.AdministradorResponse)
def sesion_actual(
    administrador: models.Administrador = Depends(administrador_actual),
):
    return administrador


# 3. CAMBIAR LA CONTRASEÑA PROPIA
@router.put("/contrasena", status_code=status.HTTP_204_NO_CONTENT)
def cambiar_contrasena(
    cambio: schemas.CambioDeContrasena,
    administrador: models.Administrador = Depends(administrador_actual),
    db: Session = Depends(get_db),
):
    if not contrasena_correcta(cambio.actual, administrador.contrasena_hash):
        raise HTTPException(status_code=400, detail="La contraseña actual no coincide.")
    if len(cambio.nueva) < LARGO_MINIMO_DE_CONTRASENA:
        raise HTTPException(
            status_code=400,
            detail=f"La contraseña nueva debe tener al menos {LARGO_MINIMO_DE_CONTRASENA} caracteres.",
        )

    administrador.contrasena_hash = hash_de_contrasena(cambio.nueva)
    db.commit()
    return None
