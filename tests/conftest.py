import os

# Las pruebas usan SQLite en memoria; nunca tocan la base de PostgreSQL.
os.environ["DATABASE_URL"] = "sqlite://"

from datetime import time

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import Model as models

# Coordenadas del centro de la obra de prueba y de un punto a varios kilómetros.
CENTRO = {"latitud": 19.4326, "longitud": -99.1332}
LEJOS = {"latitud": 19.5, "longitud": -99.1332}


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def activar_llaves_foraneas(conexion, _):
        conexion.execute("PRAGMA foreign_keys=ON")

    models.Base.metadata.create_all(engine)
    sesion = sessionmaker(bind=engine)()
    yield sesion
    sesion.close()


@pytest.fixture
def obra(db):
    # Entrada a las 08:00 con 20 minutos de tolerancia y radio de 50 m.
    obra = models.Obra(
        nombre="Obra de prueba",
        latitud_centro=CENTRO["latitud"],
        longitud_centro=CENTRO["longitud"],
        radio_tolerancia_m=50,
        hora_entrada=time(8, 0),
        minutos_tolerancia=20,
    )
    db.add(obra)
    db.commit()
    return obra


@pytest.fixture
def usuario(db, obra):
    usuario = models.Usuario(
        nombre="Trabajador", telefono="5215500000001", obra_id=obra.id
    )
    db.add(usuario)
    db.commit()
    return usuario
