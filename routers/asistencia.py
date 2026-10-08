import math
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

import Model as models
from Conexion_DB import get_db
from schemas import FichajeCreate, AsistenciaResponse
from utils.haversine import calcular_distancia

router = APIRouter(prefix="/asistencia", tags=["Asistencia"])


@router.post("/fichar", response_model=AsistenciaResponse, status_code=201)
def registrar_asistencia(
    fichaje: FichajeCreate,
    db: Session = Depends(get_db),
):
    # 1. Comprobar que las coordenadas sean válidas.
    latitud = fichaje.latitud_usuario
    longitud = fichaje.longitud_usuario

    if (
        not math.isfinite(latitud)
        or not math.isfinite(longitud)
        or not -90 <= latitud <= 90
        or not -180 <= longitud <= 180
    ):
        raise HTTPException(
            status_code=422,
            detail="Las coordenadas enviadas no son válidas.",
        )

    # 2. Buscar al usuario en PostgreSQL.
    usuario = (
        db.query(models.Usuario).filter(models.Usuario.id == fichaje.usuario_id).first()
    )

    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")

    if not usuario.activo:
        raise HTTPException(status_code=400, detail="El usuario está inactivo.")

    if usuario.obra_id is None:
        raise HTTPException(
            status_code=400,
            detail="El usuario no tiene una obra asignada.",
        )

    if usuario.obra_id != fichaje.obra_id:
        raise HTTPException(
            status_code=400,
            detail="La obra enviada no corresponde a la asignada al usuario.",
        )

    # 3. Obtener la obra real asignada al usuario.
    obra = db.query(models.Obra).filter(models.Obra.id == usuario.obra_id).first()

    if obra is None:
        raise HTTPException(status_code=404, detail="Obra no encontrada.")

    if not obra.activo:
        raise HTTPException(status_code=400, detail="La obra está inactiva.")

    if (
        obra.radio_tolerancia_m is None
        or not math.isfinite(obra.radio_tolerancia_m)
        or obra.radio_tolerancia_m <= 0
    ):
        raise HTTPException(
            status_code=400,
            detail="La obra necesita un radio de tolerancia válido.",
        )

    # 4. Calcular la distancia respecto a la obra.
    distancia = calcular_distancia(
        latitud,
        longitud,
        obra.latitud_centro,
        obra.longitud_centro,
    )

    if distancia > obra.radio_tolerancia_m:
        raise HTTPException(
            status_code=400,
            detail="Fichaje rechazado: el usuario está fuera del perímetro.",
        )

    # 5. Preparar la entrada para guardarla.
    asistencia = models.Asistencia(
        usuario_id=usuario.id,
        obra_id=obra.id,
        fecha_hora_fichaje=datetime.now(timezone.utc).replace(tzinfo=None),
        tipo="entrada",
        latitud_enviada=latitud,
        longitud_enviada=longitud,
        distancia_calculada_m=distancia,
        estatus_asistencia="Dentro de rango",
    )

    # 6. Guardar y recuperar el identificador generado.
    try:
        db.add(asistencia)
        db.commit()
        db.refresh(asistencia)
    except SQLAlchemyError:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="No se pudo completar el registro. Revisa la base de datos antes de reintentar.",
        )

    return asistencia
