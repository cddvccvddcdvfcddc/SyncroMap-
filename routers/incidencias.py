from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

import Model as models
import schemas
from Conexion_DB import get_db
from utils.clasificador import clasificar

router = APIRouter(prefix="/incidencias", tags=["Incidencias"])

PENDIENTE = "Pendiente"  # clasificada por el sistema; nadie la ha revisado
AMBIGUA = "Ambigua"  # el clasificador dudó: necesita revisión humana
REVISADA = "Revisada"  # una persona la confirmó o la corrigió


def guardar_incidencia(db: Session, usuario: models.Usuario, texto: str):
    # El clasificador solo propone; el mensaje original se conserva intacto.
    propuesta = clasificar(texto)
    ambigua = propuesta.ambigua or not propuesta.es_incidencia

    incidencia = models.Incidencia(
        usuario_id=usuario.id,
        motivo_texto=texto,
        categoria=propuesta.categoria if propuesta.es_incidencia else "General",
        prioridad=propuesta.prioridad,
        confianza=propuesta.confianza,
        estatus_revision=AMBIGUA if ambigua else PENDIENTE,
    )
    db.add(incidencia)
    db.commit()
    db.refresh(incidencia)
    return incidencia


# 1. REGISTRAR INCIDENCIA (la clasifica el sistema)
@router.post(
    "/", response_model=schemas.IncidenciaResponse, status_code=status.HTTP_201_CREATED
)
def crear_incidencia(datos: schemas.IncidenciaCreate, db: Session = Depends(get_db)):
    usuario = (
        db.query(models.Usuario)
        .filter(models.Usuario.telefono == datos.telefono_remitente)
        .first()
    )
    if usuario is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")

    if not usuario.activo:
        raise HTTPException(status_code=400, detail="El usuario está inactivo.")

    return guardar_incidencia(db, usuario, datos.motivo_texto)


# 2. OBTENER INCIDENCIAS (las más recientes primero)
@router.get("/", response_model=List[schemas.IncidenciaResponse])
def listar_incidencias(
    prioridad: Optional[str] = None,
    estatus_revision: Optional[str] = None,
    usuario_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    consulta = db.query(models.Incidencia)
    if prioridad is not None:
        consulta = consulta.filter(models.Incidencia.prioridad == prioridad)
    if estatus_revision is not None:
        consulta = consulta.filter(
            models.Incidencia.estatus_revision == estatus_revision
        )
    if usuario_id is not None:
        consulta = consulta.filter(models.Incidencia.usuario_id == usuario_id)
    return consulta.order_by(models.Incidencia.id.desc()).all()


# 3. OBTENER INCIDENCIA POR ID
@router.get("/{incidencia_id}", response_model=schemas.IncidenciaResponse)
def obtener_incidencia(incidencia_id: int, db: Session = Depends(get_db)):
    incidencia = (
        db.query(models.Incidencia)
        .filter(models.Incidencia.id == incidencia_id)
        .first()
    )
    if not incidencia:
        raise HTTPException(status_code=404, detail="Incidencia no encontrada")
    return incidencia


# 4. REVISAR INCIDENCIA (una persona confirma o corrige la clasificación)
@router.put("/{incidencia_id}/revision", response_model=schemas.IncidenciaResponse)
def revisar_incidencia(
    incidencia_id: int,
    revision: schemas.IncidenciaRevision,
    db: Session = Depends(get_db),
):
    incidencia = obtener_incidencia(incidencia_id, db)

    if revision.categoria is not None:
        incidencia.categoria = revision.categoria
    if revision.prioridad is not None:
        incidencia.prioridad = revision.prioridad
    incidencia.estatus_revision = REVISADA

    db.commit()
    db.refresh(incidencia)
    return incidencia
