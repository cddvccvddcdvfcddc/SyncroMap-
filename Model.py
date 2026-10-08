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
from datetime import datetime
from Conexion_DB import Base


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
    creado_en = Column(DateTime, default=datetime.utcnow)


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
    creado_en = Column(DateTime, default=datetime.utcnow)

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
        Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False
    )
    obra_id = Column(
        Integer, ForeignKey("obras.id", ondelete="CASCADE"), nullable=False
    )
    fecha_hora_fichaje = Column(DateTime, default=datetime.utcnow)
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

    id = Column(Integer, primary_key=True)
    usuario_id = Column(
        Integer, ForeignKey("usuarios.id", ondelete="CASCADE"), nullable=False
    )
    fecha = Column(Date, default=datetime.utcnow().date)
    motivo_texto = Column(Text, nullable=False)
    categoria = Column(String(50), default="General")
    estatus_revision = Column(String(20), default="Pendiente")

    # Relación ORM
    usuario = relationship("Usuario", backref="incidencias")
