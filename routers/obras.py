from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

import Model as models
import schemas
from Conexion_DB import get_db

router = APIRouter(prefix="/obras", tags=["Obras"])


# 1. CREAR OBRA
@router.post(
    "/", response_model=schemas.ObraResponse, status_code=status.HTTP_201_CREATED
)
def crear_obra(obra: schemas.ObraCreate, db: Session = Depends(get_db)):
    db_obra = models.Obra(**obra.model_dump())
    db.add(db_obra)
    db.commit()
    db.refresh(db_obra)
    return db_obra


# 2. OBTENER TODAS LAS OBRAS
@router.get("/", response_model=List[schemas.ObraResponse])
def listar_obras(db: Session = Depends(get_db)):
    return db.query(models.Obra).all()


# 3. OBTENER UNA OBRA POR ID
@router.get("/{obra_id}", response_model=schemas.ObraResponse)
def obtener_obra(obra_id: int, db: Session = Depends(get_db)):
    obra = db.query(models.Obra).filter(models.Obra.id == obra_id).first()
    if not obra:
        raise HTTPException(status_code=404, detail="Obra no encontrada")
    return obra


# 4. ACTUALIZAR OBRA
@router.put("/{obra_id}", response_model=schemas.ObraResponse)
def actualizar_obra(
    obra_id: int, datos_actualizados: schemas.ObraCreate, db: Session = Depends(get_db)
):
    obra_query = db.query(models.Obra).filter(models.Obra.id == obra_id)
    obra = obra_query.first()

    if not obra:
        raise HTTPException(status_code=404, detail="Obra no encontrada")

    obra_query.update(datos_actualizados.model_dump(), synchronize_session=False)
    db.commit()
    db.refresh(obra)
    return obra


# 5. ELIMINAR OBRA
@router.delete("/{obra_id}", status_code=status.HTTP_204_NO_CONTENT)
def eliminar_obra(obra_id: int, db: Session = Depends(get_db)):
    obra = db.query(models.Obra).filter(models.Obra.id == obra_id).first()

    if not obra:
        raise HTTPException(status_code=404, detail="Obra no encontrada")

    db.delete(obra)
    db.commit()
    return None
