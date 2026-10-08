from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

import Model as models
import schemas
from Conexion_DB import get_db

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])


# 1. CREAR USUARIO
@router.post(
    "/", response_model=schemas.UsuarioResponse, status_code=status.HTTP_201_CREATED
)
def crear_usuario(usuario: schemas.UsuarioCreate, db: Session = Depends(get_db)):
    # Verificar si el teléfono ya está registrado
    db_usuario = (
        db.query(models.Usuario)
        .filter(models.Usuario.telefono == usuario.telefono)
        .first()
    )
    if db_usuario:
        raise HTTPException(
            status_code=400, detail="Este número de teléfono ya está registrado."
        )

    nuevo_usuario = models.Usuario(**usuario.model_dump())
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)
    return nuevo_usuario


# 2. OBTENER TODOS LOS USUARIOS
@router.get("/", response_model=List[schemas.UsuarioResponse])
def listar_usuarios(db: Session = Depends(get_db)):
    return db.query(models.Usuario).all()


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

    usuario_query.update(datos_actualizados.model_dump(), synchronize_session=False)
    db.commit()
    db.refresh(usuario)
    return usuario


# 5. ELIMINAR USUARIO
@router.delete("/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_usuario(usuario_id: int, db: Session = Depends(get_db)):
    usuario = db.query(models.Usuario).filter(models.Usuario.id == usuario_id).first()

    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    db.delete(usuario)
    db.commit()
    return None
