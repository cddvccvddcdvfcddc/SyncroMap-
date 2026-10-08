from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    Time,
    Date,
    DateTime,
    Text,
    ForeignKey,
    Index,
    CheckConstraint,
)
from sqlalchemy.orm import relationship
from Conexion_DB import Base
from utils.horario import ahora_utc, hoy_local


class Obra(Base):
    __tablename__ = "obras"

    id = Column(Integer, primary_key=True)
    nombre = Column(String(100), nullable=False)
    latitud_centro = Column(Float, nullable=False)
    longitud_centro = Column(Float, nullable=False)
    radio_tolerancia_m = Column(Float, default=50.0)
    hora_entrada = Column(Time, default="08:00:00")
    minutos_tolerancia = Column(Integer, default=20)
    activo = Column(Boolean, default=True)
    creado_en = Column(DateTime, default=ahora_utc)


class Usuario(Base):
    __tablename__ = "usuarios"
    __table_args__ = (Index("idx_usuarios_telefono", "telefono"),)

    id = Column(Integer, primary_key=True)
    nombre = Column(String(100), nullable=False)
    telefono = Column(String(20), unique=True, nullable=False)
    rol = Column(String(20), default="operativo")
    obra_id = Column(
        Integer, ForeignKey("obras.id", ondelete="SET NULL"), nullable=True
    )
    activo = Column(Boolean, default=True)
    creado_en = Column(DateTime, default=ahora_utc)

    # Relaciones ORM
    obra = relationship("Obra", backref="usuarios")


class Asistencia(Base):
    __tablename__ = "asistencias"
    __table_args__ = (
        Index("idx_asistencias_usuario", "usuario_id"),
        CheckConstraint(
            "tipo IN ('entrada', 'salida')", name="asistencias_tipo_check"
        ),
    )

    id = Column(Integer, primary_key=True)
    usuario_id = Column(
        Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False
    )
    obra_id = Column(
        Integer, ForeignKey("obras.id", ondelete="RESTRICT"), nullable=False
    )
    fecha_hora_fichaje = Column(DateTime, default=ahora_utc)
    tipo = Column(String(10), nullable=False)  # 'entrada' o 'salida'
    latitud_enviada = Column(Float, nullable=False)
    longitud_enviada = Column(Float, nullable=False)
    distancia_calculada_m = Column(Float, nullable=False)
    estatus_asistencia = Column(
        String(30), nullable=False
    )  # 'A tiempo', 'Retardo', 'Fuera de rango', 'Salida registrada'

    # Relaciones ORM
    usuario = relationship("Usuario", backref="asistencias")
    obra = relationship("Obra", backref="asistencias")


class Incidencia(Base):
    __tablename__ = "incidencias"
    __table_args__ = (
        CheckConstraint(
            "prioridad IN ('Alta', 'Media', 'Baja')",
            name="incidencias_prioridad_check",
        ),
    )

    id = Column(Integer, primary_key=True)
    usuario_id = Column(
        Integer, ForeignKey("usuarios.id", ondelete="RESTRICT"), nullable=False
    )
    fecha = Column(Date, default=hoy_local)
    motivo_texto = Column(Text, nullable=False)
    categoria = Column(
        String(50), default="General"
    )  # tipo de incidencia: 'Retardo', 'Ausencia', 'Permiso', 'General'
    prioridad = Column(String(10), nullable=True)  # 'Alta', 'Media', 'Baja'
    estatus_revision = Column(String(20), default="Pendiente")

    # Relación ORM
    usuario = relationship("Usuario", backref="incidencias")
