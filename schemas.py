from pydantic import BaseModel, Field
from datetime import datetime, date, time
from typing import Optional

# ==========================================
# 1. ESQUEMAS PARA OBRAS
# ==========================================


class ObraBase(BaseModel):
    nombre: str = Field(..., max_length=100, description="Nombre oficial de la obra")
    latitud_centro: float = Field(
        ..., ge=-90.0, le=90.0, description="Latitud GPS central"
    )
    longitud_centro: float = Field(
        ..., ge=-180.0, le=180.0, description="Longitud GPS central"
    )
    radio_tolerancia_m: Optional[float] = Field(
        50.0, gt=0, description="Radio de tolerancia en metros"
    )
    hora_entrada: Optional[time] = Field(default="08:00:00")
    minutos_tolerancia: Optional[int] = Field(20, ge=0)
    activo: Optional[bool] = True


class ObraCreate(ObraBase):
    pass


class ObraResponse(ObraBase):
    id: int
    creado_en: datetime

    class Config:
        from_attributes = True


# ==========================================
# 2. ESQUEMAS PARA USUARIOS
# ==========================================


class UsuarioBase(BaseModel):
    nombre: str = Field(..., max_length=100)
    telefono: str = Field(
        ..., max_length=20, description="Número de WhatsApp con formato internacional"
    )
    rol: Optional[str] = "operativo"
    obra_id: Optional[int] = None
    activo: Optional[bool] = True


class UsuarioCreate(UsuarioBase):
    pass


class UsuarioResponse(UsuarioBase):
    id: int
    creado_en: datetime

    class Config:
        from_attributes = True


# ==========================================
# 3. ESQUEMAS PARA ASISTENCIAS (WhatsApp/GPS)
# ==========================================


class AsistenciaCreate(BaseModel):
    telefono_remitente: str = Field(
        ..., description="Número que envía la ubicación desde WhatsApp"
    )
    latitud: float = Field(..., ge=-90.0, le=90.0)
    longitud: float = Field(..., ge=-180.0, le=180.0)
    tipo: str = Field(
        ...,
        pattern="^(entrada|salida)$",
        description="Tipo de marcado: entrada o salida",
    )


class AsistenciaResponse(BaseModel):
    id: int
    usuario_id: int
    obra_id: int
    fecha_hora_fichaje: datetime
    tipo: str
    latitud_enviada: float
    longitud_enviada: float
    distancia_calculada_m: float
    estatus_asistencia: str

    class Config:
        from_attributes = True


# ==========================================
# 4. ESQUEMAS PARA INCIDENCIAS (NLP / Justificantes)
# ==========================================


class IncidenciaCreate(BaseModel):
    telefono_remitente: str = Field(
        ..., description="Número de WhatsApp del trabajador"
    )
    motivo_texto: str = Field(
        ..., min_length=5, description="Mensaje o justificante enviado"
    )


class IncidenciaResponse(BaseModel):
    id: int
    usuario_id: int
    fecha: date
    motivo_texto: str
    categoria: str
    estatus_revision: str

    class Config:
        from_attributes = True
