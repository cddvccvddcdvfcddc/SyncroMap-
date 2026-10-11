import hashlib
import hmac
import json
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient

import Model as models
import routers.asistencia as asistencia
import routers.whatsapp as whatsapp
from conftest import CENTRO, LEJOS
from main import app

cliente = TestClient(app)
RUTA = "/webhooks/whatsapp"


def firmar(cuerpo: bytes) -> str:
    return "sha256=" + hmac.new(b"secreto-de-prueba", cuerpo, hashlib.sha256).hexdigest()


def aviso_de_meta(*mensajes):
    return {"entry": [{"changes": [{"value": {"messages": list(mensajes)}}]}]}


# ---------- Verificación y firma ----------


def test_verificacion_con_token_correcto():
    respuesta = cliente.get(
        RUTA,
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "token-de-prueba",
            "hub.challenge": "12345",
        },
    )
    assert respuesta.status_code == 200
    assert respuesta.text == "12345"


def test_verificacion_con_token_incorrecto():
    respuesta = cliente.get(
        RUTA,
        params={"hub.mode": "subscribe", "hub.verify_token": "otro", "hub.challenge": "1"},
    )
    assert respuesta.status_code == 403


def test_mensaje_sin_firma_se_rechaza():
    assert cliente.post(RUTA, json=aviso_de_meta()).status_code == 403


def test_mensaje_con_firma_falsa_se_rechaza():
    respuesta = cliente.post(
        RUTA, json=aviso_de_meta(), headers={"X-Hub-Signature-256": "sha256=abc"}
    )
    assert respuesta.status_code == 403


def test_mensaje_con_firma_valida_se_acepta(monkeypatch):
    procesados = []
    monkeypatch.setattr(whatsapp, "procesar_en_segundo_plano", procesados.append)

    cuerpo = json.dumps(aviso_de_meta({"id": "wamid.1", "from": "1", "type": "text"})).encode()
    respuesta = cliente.post(
        RUTA,
        content=cuerpo,
        headers={"X-Hub-Signature-256": firmar(cuerpo), "Content-Type": "application/json"},
    )

    assert respuesta.status_code == 200
    assert [m["id"] for m in procesados] == ["wamid.1"]


def test_los_avisos_de_entrega_no_traen_mensajes():
    aviso = {"entry": [{"changes": [{"value": {"statuses": [{"status": "delivered"}]}}]}]}
    assert whatsapp.extraer_mensajes(aviso) == []


# ---------- Conversación ----------


@pytest.fixture
def chat(db, usuario, monkeypatch):
    # Simula mensajes del trabajador a una hora local del 8 de octubre de 2026.
    reloj = {"ahora": datetime(2026, 10, 8, 13, 50)}
    monkeypatch.setattr(asistencia, "ahora_utc", lambda: reloj["ahora"])
    monkeypatch.setattr(whatsapp, "ahora_utc", lambda: reloj["ahora"])
    contador = iter(range(1, 1000))

    class Chat:
        telefono = usuario.telefono

        def esperar(self, minutos):
            reloj["ahora"] += timedelta(minutes=minutos)

        def enviar(self, **mensaje):
            mensaje.setdefault("id", f"wamid.{next(contador)}")
            mensaje.setdefault("from", self.telefono)
            return whatsapp.procesar_mensaje(mensaje, db)

        def texto(self, cuerpo):
            return self.enviar(type="text", text={"body": cuerpo})

        def ubicacion(self, coordenadas=CENTRO, **extra):
            return self.enviar(
                type="location",
                location={
                    "latitude": coordenadas["latitud"],
                    "longitude": coordenadas["longitud"],
                },
                **extra,
            )

    return Chat()


def test_entrada_completa_por_whatsapp(chat, db):
    assert "comparte tu ubicación" in chat.texto("Entrada")

    respuesta = chat.ubicacion()

    assert respuesta == "Entrada registrada a las 07:50 en Obra de prueba."
    assert db.query(models.Asistencia).one().estatus_asistencia == "A tiempo"


def test_entrada_con_retardo_avisa_al_trabajador(chat):
    chat.esperar(60)
    chat.texto("entrada")
    assert chat.ubicacion().endswith("Quedó marcada con retardo.")


def test_salida_por_whatsapp(chat):
    chat.texto("entrada")
    chat.ubicacion()
    chat.esperar(480)
    chat.texto("SALIDA")
    assert chat.ubicacion().startswith("Salida registrada a las 15:50")


def test_ubicacion_sin_haber_escrito_entrada_o_salida(chat, db):
    assert "Primero escribe" in chat.ubicacion()
    assert db.query(models.Asistencia).count() == 0


def test_ubicacion_enviada_demasiado_tarde(chat, db):
    chat.texto("entrada")
    chat.esperar(6)
    assert "Primero escribe" in chat.ubicacion()
    assert db.query(models.Asistencia).count() == 0


def test_ubicacion_reenviada_se_rechaza(chat, db):
    chat.texto("entrada")
    respuesta = chat.ubicacion(context={"forwarded": True})
    assert "reenviadas" in respuesta
    assert db.query(models.Asistencia).count() == 0


def test_ubicacion_fuera_de_la_obra(chat, db):
    chat.texto("entrada")
    assert "fuera del perímetro" in chat.ubicacion(LEJOS)
    assert db.query(models.Asistencia).one().estatus_asistencia == "Fuera de rango"


def test_mensaje_repetido_por_meta_se_procesa_una_sola_vez(chat, db):
    chat.texto("entrada")
    primera = chat.ubicacion(id="wamid.repetido")
    segunda = chat.ubicacion(id="wamid.repetido")

    assert primera.startswith("Entrada registrada")
    assert segunda is None
    assert db.query(models.Asistencia).count() == 1


def test_numero_no_registrado(chat):
    assert "no está registrado" in chat.enviar(**{"from": "5210000000000"}, type="text", text={"body": "entrada"})


def test_usuario_dado_de_baja_no_es_atendido(chat, usuario, db):
    usuario.activo = False
    db.commit()
    assert "no está registrado" in chat.texto("entrada")


def test_mensaje_que_no_se_entiende_recibe_ayuda(chat):
    assert chat.texto("hola") == whatsapp.AYUDA


# ---------- Incidencias en texto libre ----------


def test_aviso_de_retardo_en_texto_libre(chat, db):
    respuesta = chat.texto("voy a llegar tarde, hay tráfico")

    assert respuesta == "Registré tu aviso de retardo. Tu supervisor lo revisará."
    incidencia = db.query(models.Incidencia).one()
    assert incidencia.motivo_texto == "voy a llegar tarde, hay tráfico"
    assert (incidencia.categoria, incidencia.prioridad) == ("Retardo", "Media")


def test_aviso_de_ausencia_en_texto_libre(chat, db):
    assert chat.texto("estoy enfermo, hoy no voy a ir").startswith(
        "Registré tu aviso de ausencia."
    )
    assert db.query(models.Incidencia).one().categoria == "Ausencia"


def test_incidencia_de_prioridad_alta_pide_llamar_al_supervisor(chat, db):
    respuesta = chat.texto("un compañero se cortó con la sierra")

    assert respuesta.endswith("Si es una emergencia, llámale de inmediato.")
    assert db.query(models.Incidencia).one().prioridad == "Alta"


def test_un_aviso_que_menciona_la_entrada_no_es_un_fichaje(chat, db):
    respuesta = chat.texto("voy a llegar tarde a la entrada porque hay trafico")

    assert respuesta.startswith("Registré tu aviso de retardo.")
    # La ubicación que llegue después no debe convertirse en un fichaje.
    assert "Primero escribe" in chat.ubicacion()
    assert db.query(models.Asistencia).count() == 0


def test_un_saludo_o_un_fichaje_no_generan_incidencia(chat, db):
    chat.texto("hola")
    chat.texto("gracias")
    chat.texto("quiero registrar mi entrada")

    assert db.query(models.Incidencia).count() == 0


def test_fichaje_escrito_con_una_frase_larga(chat):
    assert "comparte tu ubicación" in chat.texto("quiero registrar mi entrada")
    assert chat.ubicacion().startswith("Entrada registrada")


def test_un_numero_no_registrado_no_genera_incidencia(chat, db):
    chat.enviar(**{"from": "5210000000000"}, type="text", text={"body": "estoy enfermo"})
    assert db.query(models.Incidencia).count() == 0


def test_incidencia_repetida_por_meta_se_guarda_una_sola_vez(chat, db):
    mensaje = {"id": "wamid.aviso", "type": "text", "text": {"body": "estoy enfermo"}}
    chat.enviar(**mensaje)
    chat.enviar(**mensaje)
    assert db.query(models.Incidencia).count() == 1


# ---------- Consultas ----------


def test_consulta_sin_asistencias(chat):
    assert chat.texto("cuántas faltas llevo?") == (
        "Tu resumen de octubre:\nAsistencias: 0\nRetardos: 0\nFaltas: 0"
    )


def test_consulta_despues_de_fichar_con_retardo(chat):
    chat.esperar(60)
    chat.texto("entrada")
    chat.ubicacion()

    respuesta = chat.texto("cuantos retardos tengo")

    assert "Asistencias: 1" in respuesta
    assert "Retardos: 1" in respuesta


def test_una_consulta_no_genera_incidencia_ni_fichaje(chat, db):
    chat.texto("cuántos retardos llevo?")

    assert db.query(models.Incidencia).count() == 0
    assert "Primero escribe" in chat.ubicacion()


@pytest.mark.parametrize(
    "texto, esperado",
    [
        ("entrada", "entrada"),
        ("Registrar ENTRADA", "entrada"),
        ("salida", "salida"),
        ("Salída", "salida"),
        ("hola", None),
    ],
)
def test_detectar_intencion(texto, esperado):
    assert whatsapp.detectar_intencion(texto) == esperado
