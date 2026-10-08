import math

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

import Model as models
from Conexion_DB import get_db
from schemas import AsistenciaCreate, AsistenciaResponse
from utils.haversine import calcular_distancia
from utils.horario import ahora_utc, estatus_de_entrada, limites_del_dia_utc

router = APIRouter(prefix="/asistencia", tags=["Asistencia"])

FUERA_DE_RANGO = "Fuera de rango"


def buscar_fichaje_del_dia(db: Session, usuario_id: int, tipo: str, ahora):
    # Los intentos fuera de rango no cuentan como fichaje válido.
    inicio, fin = limites_del_dia_utc(ahora)
    return (
        db.query(models.Asistencia)
        .filter(
            models.Asistencia.usuario_id == usuario_id,
            models.Asistencia.tipo == tipo,
            models.Asistencia.estatus_asistencia != FUERA_DE_RANGO,
            models.Asistencia.fecha_hora_fichaje >= inicio,
            models.Asistencia.fecha_hora_fichaje < fin,
        )
        .first()
    )


@router.post("/fichar", response_model=AsistenciaResponse, status_code=201)
def registrar_asistencia(
    fichaje: AsistenciaCreate,
    db: Session = Depends(get_db),
):
    ahora = ahora_utc()

    # 1. Buscar al usuario por su teléfono en PostgreSQL.
    usuario = (
        db.query(models.Usuario)
        .filter(models.Usuario.telefono == fichaje.telefono_remitente)
        .first()
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

    # 2. Obtener la obra real asignada al usuario.
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

    if obra.hora_entrada is None:
        raise HTTPException(
            status_code=400,
            detail="La obra necesita una hora de entrada.",
        )

    # 3. Permitir una sola entrada y una sola salida por día.
    if buscar_fichaje_del_dia(db, usuario.id, fichaje.tipo, ahora) is not None:
        raise HTTPException(
            status_code=409,
            detail=f"Ya existe una {fichaje.tipo} registrada hoy.",
        )

    if (
        fichaje.tipo == "salida"
        and buscar_fichaje_del_dia(db, usuario.id, "entrada", ahora) is None
    ):
        raise HTTPException(
            status_code=409,
            detail="No se puede registrar la salida sin una entrada previa hoy.",
        )

    # 4. Calcular la distancia respecto a la obra.
    distancia = calcular_distancia(
        fichaje.latitud,
        fichaje.longitud,
        obra.latitud_centro,
        obra.longitud_centro,
    )
    dentro_de_rango = distancia <= obra.radio_tolerancia_m

    # 5. Definir el estatus del fichaje.
    if not dentro_de_rango:
        estatus = FUERA_DE_RANGO
    elif fichaje.tipo == "entrada":
        estatus = estatus_de_entrada(
            ahora, obra.hora_entrada, obra.minutos_tolerancia or 0
        )
    else:
        estatus = "Salida registrada"

    asistencia = models.Asistencia(
        usuario_id=usuario.id,
        obra_id=obra.id,
        fecha_hora_fichaje=ahora,
        tipo=fichaje.tipo,
        latitud_enviada=fichaje.latitud,
        longitud_enviada=fichaje.longitud,
        distancia_calculada_m=distancia,
        estatus_asistencia=estatus,
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

    # 7. El intento fuera de rango queda guardado como evidencia, pero se rechaza.
    if not dentro_de_rango:
        raise HTTPException(
            status_code=400,
            detail="Fichaje rechazado: el usuario está fuera del perímetro.",
        )

    return asistencia
