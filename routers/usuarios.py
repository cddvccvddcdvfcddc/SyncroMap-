from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

import Model as models
import schemas
from Conexion_DB import get_db

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])


def validar_datos_usuario(
    db: Session, usuario: schemas.UsuarioCreate, usuario_id: Optional[int] = None
):
    # Verificar que el teléfono no pertenezca a otro usuario
    consulta = db.query(models.Usuario).filter(
        models.Usuario.telefono == usuario.telefono
    )
    if usuario_id is not None:
        consulta = consulta.filter(models.Usuario.id != usuario_id)

    if consulta.first():
        raise HTTPException(
            status_code=400, detail="Este número de teléfono ya está registrado."
        )

    # Verificar que la obra asignada exista
    if usuario.obra_id is not None:
        obra = db.query(models.Obra).filter(models.Obra.id == usuario.obra_id).first()
        if not obra:
            raise HTTPException(status_code=404, detail="Obra no encontrada")


# 1. CREAR USUARIO
@router.post(
    "/", response_model=schemas.UsuarioResponse, status_code=status.HTTP_201_CREATED
)
def crear_usuario(usuario: schemas.UsuarioCreate, db: Session = Depends(get_db)):
    validar_datos_usuario(db, usuario)

    nuevo_usuario = models.Usuario(**usuario.model_dump())
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)
    return nuevo_usuario


# 2. OBTENER USUARIOS (solo los activos, salvo que se pidan todos)
@router.get("/", response_model=List[schemas.UsuarioResponse])
def listar_usuarios(incluir_inactivos: bool = False, db: Session = Depends(get_db)):
    consulta = db.query(models.Usuario)
    if not incluir_inactivos:
        consulta = consulta.filter(models.Usuario.activo.is_(True))
    return consulta.all()


# 3. OBTENER USUARIO POR ID
@router.get("/{usuario_id}", response_model=schemas.UsuarioResponse)
def obtener_usuario(usuario_id: int, db: Session = Depends(get_db)):
    usuario = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return usuario


# 4. ACTUALIZAR USUARIO
@router.put("/{usuario_id}", response_model=schemas.UsuarioResponse)
def actualizar_usuario(
    usuario_id: int,
    datos_actualizados: schemas.UsuarioCreate,
    db: Session = Depends(get_db),
):
    usuario_query = db.query(models.Usuario).filter(models.Usuario.id == usuario_id)
    usuario = usuario_query.first()

    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    validar_datos_usuario(db, datos_actualizados, usuario_id)

    usuario_query.update(datos_actualizados.model_dump(), synchronize_session=False)
    db.commit()
    db.refresh(usuario)
    return usuario


# 5. DAR DE BAJA USUARIO (baja lógica: se conserva su historial de asistencias)
@router.delete("/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_usuario(usuario_id: int, db: Session = Depends(get_db)):
    usuario = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()

    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    usuario.activo = False
    db.commit()
    return None
