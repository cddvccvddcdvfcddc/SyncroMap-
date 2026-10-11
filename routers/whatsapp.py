import json
import logging
import unicodedata
from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Request, Response
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

import Model as models
from Conexion_DB import SessionLocal
from routers.asistencia import registrar_asistencia, resumen_del_mes
from routers.incidencias import guardar_incidencia
from schemas import AsistenciaCreate
from utils.clasificador import clasificar
from utils.horario import a_hora_local, ahora_utc
from utils.whatsapp import enviar_texto, firma_valida, token_de_verificacion_valido

router = APIRouter(prefix="/webhooks/whatsapp", tags=["WhatsApp"])
logger = logging.getLogger("uvicorn.error")

# Tiempo máximo entre escribir "entrada"/"salida" y compartir la ubicación.
MINUTOS_PARA_UBICACION = 5

# Un mensaje así de corto con "entrada" o "salida" siempre es un fichaje.
PALABRAS_DE_UN_FICHAJE = 3

AYUDA = (
    "Hola, soy SyncroMap. Escribe *entrada* o *salida* y después "
    "comparte tu ubicación actual para registrar tu asistencia.\n\n"
    "También puedes avisarme con tus palabras si vas a llegar tarde, "
    "si no puedes presentarte, si necesitas un permiso o si pasó algo en la obra. "
    "Y puedes preguntarme cuántas asistencias, retardos o faltas llevas."
)

INCIDENCIA_REGISTRADA = {
    "Retardo": "Registré tu aviso de retardo.",
    "Ausencia": "Registré tu aviso de ausencia.",
    "Permiso": "Registré tu solicitud de permiso.",
    "General": "Registré tu reporte.",
}

MESES = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
    "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)  # fmt: skip


# 1. VERIFICACIÓN DEL WEBHOOK (Meta la hace una vez al configurarlo)
@router.get("")
def verificar_webhook(
    modo: Optional[str] = Query(None, alias="hub.mode"),
    token: Optional[str] = Query(None, alias="hub.verify_token"),
    reto: Optional[str] = Query(None, alias="hub.challenge"),
):
    if modo == "subscribe" and token_de_verificacion_valido(token):
        return Response(content=reto or "", media_type="text/plain")

    raise HTTPException(status_code=403, detail="Token de verificación incorrecto.")


# 2. RECEPCIÓN DE MENSAJES
@router.post("")
async def recibir_webhook(request: Request, tareas: BackgroundTasks):
    cuerpo = await request.body()

    if not firma_valida(cuerpo, request.headers.get("X-Hub-Signature-256")):
        raise HTTPException(status_code=403, detail="Firma inválida.")

    # Se responde de inmediato a Meta y cada mensaje se procesa después.
    for mensaje in extraer_mensajes(json.loads(cuerpo)):
        tareas.add_task(procesar_en_segundo_plano, mensaje)

    return {"estatus": "recibido"}


def extraer_mensajes(datos: dict) -> list[dict]:
    mensajes = []
    for entrada in datos.get("entry", []):
        for cambio in entrada.get("changes", []):
            mensajes.extend(cambio.get("value", {}).get("messages", []))
    return mensajes


def procesar_en_segundo_plano(mensaje: dict):
    db = SessionLocal()
    try:
        respuesta = procesar_mensaje(mensaje, db)
        if respuesta:
            enviar_texto(mensaje["from"], respuesta)
    except Exception:
        logger.exception("Error al procesar un mensaje de WhatsApp")
    finally:
        db.close()


def detectar_intencion(texto: str) -> Optional[str]:
    # Quitar acentos y mayúsculas antes de buscar la palabra clave
    normalizado = unicodedata.normalize("NFD", texto.lower())
    normalizado = "".join(c for c in normalizado if unicodedata.category(c) != "Mn")

    if "entrada" in normalizado:
        return "entrada"
    if "salida" in normalizado:
        return "salida"
    return None


def interpretar(texto: str) -> Optional[str]:
    # Devuelve qué quiere el trabajador: 'entrada', 'salida', 'incidencia',
    # 'consulta' o nada. "Voy a llegar tarde a la entrada" trae la palabra
    # clave, pero es un aviso de retardo y no un fichaje.
    fichaje = detectar_intencion(texto)
    if fichaje and len(texto.split()) <= PALABRAS_DE_UN_FICHAJE:
        return fichaje

    propuesta = clasificar(texto)
    if propuesta.es_incidencia:
        return "incidencia"
    if propuesta.es_consulta:
        return "consulta"
    return fichaje


def responder_incidencia(usuario: models.Usuario, texto: str, db: Session) -> str:
    incidencia = guardar_incidencia(db, usuario, texto)

    respuesta = INCIDENCIA_REGISTRADA[incidencia.categoria]
    respuesta += " Tu supervisor lo revisará."
    if incidencia.prioridad == "Alta":
        respuesta += " Si es una emergencia, llámale de inmediato."
    return respuesta


def responder_consulta(usuario: models.Usuario, db: Session) -> str:
    ahora = ahora_utc()
    resumen = resumen_del_mes(db, usuario, ahora)
    mes = MESES[a_hora_local(ahora).month - 1]
    return (
        f"Tu resumen de {mes}:\n"
        f"Asistencias: {resumen['asistencias']}\n"
        f"Retardos: {resumen['retardos']}\n"
        f"Faltas: {resumen['faltas']}"
    )


def procesar_mensaje(mensaje: dict, db: Session) -> Optional[str]:
    # Devuelve el texto con el que se le responde al trabajador.
    telefono = mensaje.get("from")
    wa_message_id = mensaje.get("id")
    tipo = mensaje.get("type") or "desconocido"

    if not telefono or not wa_message_id:
        return None

    texto = mensaje.get("text", {}).get("body") if tipo == "text" else None
    accion = interpretar(texto) if texto else None
    # Solo un fichaje pendiente queda esperando la ubicación.
    intencion = accion if accion in ("entrada", "salida") else None

    # 1. Guardar el mensaje. Si ya existía, Meta lo reenvió y se ignora.
    try:
        db.add(
            models.MensajeWhatsapp(
                wa_message_id=wa_message_id,
                telefono=telefono,
                tipo=tipo,
                texto=texto,
                intencion=intencion,
                recibido_en=ahora_utc(),
            )
        )
        db.commit()
    except IntegrityError:
        db.rollback()
        return None

    # 2. Solo se atiende a trabajadores dados de alta y activos.
    usuario = (
        db.query(models.Usuario)
        .filter(models.Usuario.telefono == telefono, models.Usuario.activo.is_(True))
        .first()
    )
    if usuario is None:
        logger.info("Mensaje de un número no registrado: %s", telefono)
        return "Tu número no está registrado en SyncroMap. Avisa a tu supervisor."

    # 3. Responder según el tipo de mensaje.
    if tipo == "location":
        return fichar_con_ubicacion(mensaje, telefono, db)

    if intencion:
        return (
            f"Para registrar tu {intencion}, comparte tu ubicación actual "
            "(clip > Ubicación > Enviar mi ubicación actual)."
        )

    if accion == "incidencia":
        return responder_incidencia(usuario, texto, db)

    if accion == "consulta":
        return responder_consulta(usuario, db)

    return AYUDA


def fichar_con_ubicacion(mensaje: dict, telefono: str, db: Session) -> str:
    if mensaje.get("context", {}).get("forwarded"):
        return "No se aceptan ubicaciones reenviadas. Comparte tu ubicación actual."

    # La ubicación debe llegar poco después de pedir la entrada o la salida.
    limite = ahora_utc() - timedelta(minutes=MINUTOS_PARA_UBICACION)
    orden = (
        db.query(models.MensajeWhatsapp)
        .filter(
            models.MensajeWhatsapp.telefono == telefono,
            models.MensajeWhatsapp.intencion.isnot(None),
            models.MensajeWhatsapp.recibido_en >= limite,
        )
        .order_by(models.MensajeWhatsapp.id.desc())
        .first()
    )
    if orden is None:
        return "Primero escribe *entrada* o *salida* y después comparte tu ubicación."

    ubicacion = mensaje.get("location", {})
    try:
        datos = AsistenciaCreate(
            telefono_remitente=telefono,
            latitud=ubicacion.get("latitude"),
            longitud=ubicacion.get("longitude"),
            tipo=orden.intencion,
        )
        asistencia = registrar_asistencia(datos, db)
    except ValidationError:
        return "No pude leer tu ubicación. Intenta compartirla de nuevo."
    except HTTPException as error:
        return str(error.detail)

    hora = a_hora_local(asistencia.fecha_hora_fichaje).strftime("%H:%M")
    respuesta = (
        f"{asistencia.tipo.capitalize()} registrada a las {hora} "
        f"en {asistencia.obra.nombre}."
    )
    if asistencia.estatus_asistencia == "Retardo":
        respuesta += " Quedó marcada con retardo."
    return respuesta
