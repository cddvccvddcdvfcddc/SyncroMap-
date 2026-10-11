import hashlib
import hmac
import logging
import os

import httpx
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("uvicorn.error")

URL_API = "https://graph.facebook.com/v21.0"


def firma_valida(cuerpo: bytes, firma: str | None) -> bool:
    # Meta firma cada aviso con la clave secreta de la app (HMAC-SHA256)
    secreto = os.getenv("WHATSAPP_APP_SECRET", "")
    if not secreto or not firma or not firma.startswith("sha256="):
        return False

    esperada = hmac.new(secreto.encode(), cuerpo, hashlib.sha256).hexdigest()
    return hmac.compare_digest(esperada, firma.removeprefix("sha256="))


def token_de_verificacion_valido(token: str | None) -> bool:
    esperado = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
    return bool(esperado) and hmac.compare_digest(token or "", esperado)


def _enviar(telefono: str, texto: str) -> httpx.Response:
    return httpx.post(
        f"{URL_API}/{os.getenv('WHATSAPP_PHONE_ID')}/messages",
        headers={"Authorization": f"Bearer {os.getenv('WHATSAPP_TOKEN')}"},
        json={
            "messaging_product": "whatsapp",
            "to": telefono,
            "type": "text",
            "text": {"body": texto},
        },
        timeout=15,
    )


def enviar_texto(telefono: str, texto: str) -> bool:
    try:
        respuesta = _enviar(telefono, texto)

        # Los celulares de México llegan como 521XXXXXXXXXX, pero a veces
        # Meta solo acepta enviarles como 52XXXXXXXXXX.
        if respuesta.status_code >= 400 and telefono.startswith("521"):
            respuesta = _enviar("52" + telefono[3:], texto)
    except httpx.HTTPError as error:
        logger.error("No se pudo enviar el mensaje de WhatsApp: %s", error)
        return False

    if respuesta.status_code >= 400:
        logger.error(
            "WhatsApp rechazó el envío (%s): %s", respuesta.status_code, respuesta.text
        )
        return False

    return True
