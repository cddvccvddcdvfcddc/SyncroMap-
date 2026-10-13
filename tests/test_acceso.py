from datetime import datetime, timedelta

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

import Model as models
import routers.acceso as acceso
from Conexion_DB import get_db
from crear_administrador import guardar_administrador
from main import app
from schemas import CambioDeContrasena, Credenciales
from utils.horario import ahora_utc
from utils.seguridad import (
    HORAS_DE_SESION,
    contrasena_correcta,
    crear_token,
    hash_de_contrasena,
    leer_token,
)

CONTRASENA = "una-clave-larga"


@pytest.fixture(autouse=True)
def sin_intentos_previos():
    acceso._intentos_fallidos.clear()
    yield
    acceso._intentos_fallidos.clear()


@pytest.fixture
def administrador(db):
    cuenta, _ = guardar_administrador(db, "Mario", CONTRASENA, "Mario Prueba")
    return cuenta


@pytest.fixture
def cliente(db):
    app.dependency_overrides[get_db] = lambda: db
    yield TestClient(app)
    app.dependency_overrides.clear()


def entrar(db, usuario="mario", contrasena=CONTRASENA, ahora=None):
    return acceso.iniciar_sesion(
        db, Credenciales(usuario=usuario, contrasena=contrasena), ahora
    )


# --- Contraseñas y tokens ---


def test_la_contrasena_no_se_guarda_tal_cual(administrador):
    assert CONTRASENA not in administrador.contrasena_hash
    assert contrasena_correcta(CONTRASENA, administrador.contrasena_hash)
    assert not contrasena_correcta("otra-clave-larga", administrador.contrasena_hash)


def test_dos_resumenes_de_la_misma_contrasena_son_distintos():
    assert hash_de_contrasena(CONTRASENA) != hash_de_contrasena(CONTRASENA)


def test_un_resumen_danado_no_da_acceso():
    assert not contrasena_correcta(CONTRASENA, "esto-no-es-un-resumen")


def test_el_token_identifica_al_administrador():
    assert leer_token(crear_token(7)) == 7


def test_un_token_alterado_o_inventado_no_sirve():
    token = crear_token(7)
    assert leer_token(token[:-2] + "xx") is None
    assert leer_token("cualquier-cosa") is None


def test_el_token_vence_al_terminar_la_sesion():
    ayer = ahora_utc() - timedelta(hours=HORAS_DE_SESION + 1)
    assert leer_token(crear_token(7, ayer)) is None


# --- Inicio de sesión ---


def test_entrar_con_la_contrasena_correcta(db, administrador):
    sesion = entrar(db)
    assert leer_token(sesion["token"]) == administrador.id
    assert sesion["administrador"].nombre == "Mario Prueba"


def test_el_usuario_no_distingue_mayusculas_ni_espacios(db, administrador):
    assert entrar(db, usuario="  MARIO ")["token"]


@pytest.mark.parametrize(
    "usuario, contrasena", [("mario", "equivocada"), ("nadie", CONTRASENA)]
)
def test_datos_incorrectos_dan_el_mismo_error(db, administrador, usuario, contrasena):
    with pytest.raises(HTTPException) as error:
        entrar(db, usuario, contrasena)
    assert error.value.status_code == 401
    assert error.value.detail == "Usuario o contraseña incorrectos."


def test_una_cuenta_dada_de_baja_no_entra(db, administrador):
    administrador.activo = False
    db.commit()
    with pytest.raises(HTTPException) as error:
        entrar(db)
    assert error.value.status_code == 401


def test_se_bloquea_tras_varios_intentos_fallidos(db, administrador):
    ahora = ahora_utc()
    for _ in range(acceso.INTENTOS_PERMITIDOS):
        with pytest.raises(HTTPException):
            entrar(db, contrasena="equivocada", ahora=ahora)

    # Ni con la contraseña correcta se entra mientras dura el bloqueo.
    with pytest.raises(HTTPException) as error:
        entrar(db, ahora=ahora)
    assert error.value.status_code == 429

    despues = ahora + timedelta(minutes=acceso.MINUTOS_DE_BLOQUEO + 1)
    assert entrar(db, ahora=despues)["token"]


def test_volver_a_crear_la_cuenta_solo_cambia_la_contrasena(db, administrador):
    cuenta, es_nueva = guardar_administrador(db, "mario", "otra-clave-larga")
    assert not es_nueva
    assert cuenta.id == administrador.id
    assert cuenta.nombre == "Mario Prueba"
    assert db.query(models.Administrador).count() == 1
    assert entrar(db, contrasena="otra-clave-larga")["token"]


def test_no_se_aceptan_contrasenas_cortas(db):
    with pytest.raises(ValueError):
        guardar_administrador(db, "mario", "corta")


def test_cambiar_la_contrasena_propia(db, administrador):
    acceso.cambiar_contrasena(
        CambioDeContrasena(actual=CONTRASENA, nueva="otra-clave-larga"), administrador, db
    )
    assert entrar(db, contrasena="otra-clave-larga")["token"]

    with pytest.raises(HTTPException) as error:
        acceso.cambiar_contrasena(
            CambioDeContrasena(actual="no-es-esta", nueva="tercera-clave"), administrador, db
        )
    assert error.value.status_code == 400


# --- Rutas protegidas ---

RUTAS_DEL_PANEL = [
    "/obras/",
    "/usuarios/",
    "/asistencia/",
    "/asistencia/faltas",
    "/incidencias/",
    "/reportes/resumen?desde=2026-10-01&hasta=2026-10-31",
    "/reportes/excel?desde=2026-10-01&hasta=2026-10-31",
    "/reportes/pdf?desde=2026-10-01&hasta=2026-10-31",
    "/acceso/yo",
]


@pytest.mark.parametrize("ruta", RUTAS_DEL_PANEL)
def test_sin_sesion_no_se_ven_los_datos(cliente, ruta):
    assert cliente.get(ruta).status_code == 401
    falso = {"Authorization": "Bearer inventado"}
    assert cliente.get(ruta, headers=falso).status_code == 401


def test_sin_sesion_tampoco_se_puede_escribir(cliente, obra):
    assert cliente.post("/usuarios/", json={}).status_code == 401
    assert cliente.delete(f"/obras/{obra.id}").status_code == 401
    assert cliente.put("/incidencias/1/revision", json={}).status_code == 401


def test_con_sesion_se_ven_los_datos(cliente, administrador, obra):
    respuesta = cliente.post(
        "/acceso/", json={"usuario": "mario", "contrasena": CONTRASENA}
    )
    assert respuesta.status_code == 200
    sesion = respuesta.json()
    assert sesion["administrador"] == {
        "id": administrador.id,
        "usuario": "mario",
        "nombre": "Mario Prueba",
    }
    assert "contrasena_hash" not in respuesta.text

    cabecera = {"Authorization": "Bearer " + sesion["token"]}
    for ruta in RUTAS_DEL_PANEL:
        assert cliente.get(ruta, headers=cabecera).status_code == 200
    assert cliente.get("/obras/", headers=cabecera).json()[0]["nombre"] == obra.nombre


def test_el_token_de_una_cuenta_dada_de_baja_deja_de_servir(cliente, db, administrador):
    cabecera = {"Authorization": "Bearer " + crear_token(administrador.id)}
    assert cliente.get("/acceso/yo", headers=cabecera).status_code == 200

    administrador.activo = False
    db.commit()
    assert cliente.get("/acceso/yo", headers=cabecera).status_code == 401


def test_el_inicio_y_el_webhook_no_piden_sesion(cliente):
    assert cliente.get("/").status_code == 200
    # El webhook responde con su propia regla (token de Meta), no con la del panel.
    assert cliente.get("/webhooks/whatsapp").status_code == 403
