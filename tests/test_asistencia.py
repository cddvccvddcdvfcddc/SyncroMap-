from datetime import datetime, timedelta

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

import Model as models
import routers.asistencia as asistencia
from conftest import CENTRO, LEJOS
from schemas import AsistenciaCreate


@pytest.fixture
def fichar(db, usuario, monkeypatch):
    # Ficha como si fuera la hora local indicada del día dado de octubre de 2026.
    def _fichar(tipo, hora_local, dia=8, coordenadas=CENTRO, telefono=None):
        hora, minuto = map(int, hora_local.split(":"))
        ahora = datetime(2026, 10, dia, hora, minuto) + timedelta(hours=6)
        monkeypatch.setattr(asistencia, "ahora_utc", lambda: ahora)

        datos = AsistenciaCreate(
            telefono_remitente=telefono or usuario.telefono,
            tipo=tipo,
            **coordenadas,
        )
        return asistencia.registrar_asistencia(datos, db)

    return _fichar


def test_entrada_a_tiempo(fichar):
    assert fichar("entrada", "07:55").estatus_asistencia == "A tiempo"


def test_entrada_con_retardo(fichar):
    assert fichar("entrada", "08:21").estatus_asistencia == "Retardo"


def test_no_permite_dos_entradas_el_mismo_dia(fichar):
    fichar("entrada", "07:55")
    with pytest.raises(HTTPException) as error:
        fichar("entrada", "09:00")
    assert error.value.status_code == 409


def test_entrada_repetida_en_la_noche_sigue_siendo_el_mismo_dia(fichar):
    fichar("entrada", "07:55")
    with pytest.raises(HTTPException) as error:
        fichar("entrada", "19:00")
    assert error.value.status_code == 409


def test_permite_entrada_al_dia_siguiente(fichar):
    fichar("entrada", "07:55", dia=8)
    assert fichar("entrada", "07:55", dia=9).estatus_asistencia == "A tiempo"


def test_salida_sin_entrada_se_rechaza(fichar):
    with pytest.raises(HTTPException) as error:
        fichar("salida", "16:00")
    assert error.value.status_code == 409


def test_salida_despues_de_la_entrada(fichar):
    fichar("entrada", "07:55")
    assert fichar("salida", "16:00").estatus_asistencia == "Salida registrada"


def test_no_permite_dos_salidas(fichar):
    fichar("entrada", "07:55")
    fichar("salida", "16:00")
    with pytest.raises(HTTPException) as error:
        fichar("salida", "17:00")
    assert error.value.status_code == 409


def test_fuera_de_rango_se_rechaza_pero_queda_guardado(fichar, db):
    with pytest.raises(HTTPException) as error:
        fichar("entrada", "07:55", coordenadas=LEJOS)
    assert error.value.status_code == 400

    intento = db.query(models.Asistencia).one()
    assert intento.estatus_asistencia == "Fuera de rango"
    assert intento.distancia_calculada_m > 50


def test_un_intento_fuera_de_rango_no_bloquea_el_fichaje(fichar):
    with pytest.raises(HTTPException):
        fichar("entrada", "07:50", coordenadas=LEJOS)
    assert fichar("entrada", "07:55").estatus_asistencia == "A tiempo"


def test_telefono_desconocido(fichar):
    with pytest.raises(HTTPException) as error:
        fichar("entrada", "07:55", telefono="0000")
    assert error.value.status_code == 404


def test_usuario_inactivo_no_puede_fichar(fichar, usuario, db):
    usuario.activo = False
    db.commit()
    with pytest.raises(HTTPException) as error:
        fichar("entrada", "07:55")
    assert error.value.status_code == 400


@pytest.mark.parametrize(
    "datos",
    [
        {"latitud": 999, "longitud": 0, "tipo": "entrada"},
        {"latitud": float("nan"), "longitud": 0, "tipo": "entrada"},
        {"latitud": 0, "longitud": float("inf"), "tipo": "entrada"},
        {"latitud": 0, "longitud": 0, "tipo": "comida"},
    ],
)
def test_datos_invalidos_se_rechazan(datos):
    with pytest.raises(ValidationError):
        AsistenciaCreate(telefono_remitente="5215500000001", **datos)
