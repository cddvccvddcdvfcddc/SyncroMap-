"""esquema inicial

Revision ID: 83aeb2b91285
Revises: 
Create Date: 2026-10-08 13:55:14.335094

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '83aeb2b91285'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Las cuatro tablas originales, tal como se crearon con Tablas.sql.
    op.execute(
        """
        CREATE TABLE obras (
            id SERIAL PRIMARY KEY,
            nombre VARCHAR(100) NOT NULL,
            latitud_centro DOUBLE PRECISION NOT NULL,
            longitud_centro DOUBLE PRECISION NOT NULL,
            radio_tolerancia_m DOUBLE PRECISION DEFAULT 50.0,
            hora_entrada TIME DEFAULT '08:00:00',
            minutos_tolerancia INTEGER DEFAULT 20,
            activo BOOLEAN DEFAULT TRUE,
            creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    op.execute(
        """
        CREATE TABLE usuarios (
            id SERIAL PRIMARY KEY,
            nombre VARCHAR(100) NOT NULL,
            telefono VARCHAR(20) UNIQUE NOT NULL,
            rol VARCHAR(20) DEFAULT 'operativo',
            obra_id INTEGER REFERENCES obras(id) ON DELETE SET NULL,
            activo BOOLEAN DEFAULT TRUE,
            creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    op.execute(
        """
        CREATE TABLE asistencias (
            id SERIAL PRIMARY KEY,
            usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
            obra_id INTEGER NOT NULL REFERENCES obras(id) ON DELETE CASCADE,
            fecha_hora_fichaje TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            tipo VARCHAR(10) CHECK (tipo IN ('entrada', 'salida')),
            latitud_enviada DOUBLE PRECISION NOT NULL,
            longitud_enviada DOUBLE PRECISION NOT NULL,
            distancia_calculada_m DOUBLE PRECISION NOT NULL,
            estatus_asistencia VARCHAR(30) NOT NULL
        )
        """
    )
    op.execute(
        """
        CREATE TABLE incidencias (
            id SERIAL PRIMARY KEY,
            usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
            fecha DATE DEFAULT CURRENT_DATE,
            motivo_texto TEXT NOT NULL,
            categoria VARCHAR(50) DEFAULT 'General',
            estatus_revision VARCHAR(20) DEFAULT 'Pendiente'
        )
        """
    )
    op.execute("CREATE INDEX idx_usuarios_telefono ON usuarios(telefono)")
    op.execute("CREATE INDEX idx_asistencias_usuario ON asistencias(usuario_id)")


def downgrade() -> None:
    op.execute("DROP TABLE incidencias")
    op.execute("DROP TABLE asistencias")
    op.execute("DROP TABLE usuarios")
    op.execute("DROP TABLE obras")
