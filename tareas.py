import logging
from datetime import timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from sqlalchemy.orm import Session

import Model as models
from Conexion_DB import SessionLocal
from routers.asistencia import FUERA_DE_RANGO
from utils.horario import (
    MESES,
    ZONA_LOCAL,
    a_hora_local,
    ahora_utc,
    cierre_de_tolerancia,
    es_dia_laborable,
    inicio_del_dia_utc,
    limites_del_dia_utc,
)
from utils.whatsapp import enviar_texto

logger = logging.getLogger("uvicorn.error")

ROL_SUPERVISOR = "supervisor"

# Si el servidor estuvo apagado, al volver se registran las faltas de estos días.
DIAS_HACIA_ATRAS = 31

# El reporte matutino solo se envía dentro de este tiempo tras el cierre de tolerancia.
HORAS_PARA_ENVIAR_REPORTE = 2

MINUTOS_ENTRE_REVISIONES = 5

ORDEN_DE_PRIORIDAD = {"Alta": 0, "Media": 1, "Baja": 2}


def trabajadores_de(db: Session, obra: models.Obra) -> list[models.Usuario]:
    # Personal activo que debe fichar en la obra. El supervisor también cuenta:
    # trabaja en la obra, ficha y puede reportar incidencias como los demás.
    return (
        db.query(models.Usuario)
        .filter(models.Usuario.obra_id == obra.id, models.Usuario.activo.is_(True))
        .order_by(models.Usuario.nombre)
        .all()
    )


def supervisores_de(db: Session, obra: models.Obra) -> list[models.Usuario]:
    return (
        db.query(models.Usuario)
        .filter(
            models.Usuario.obra_id == obra.id,
            models.Usuario.activo.is_(True),
            models.Usuario.rol == ROL_SUPERVISOR,
        )
        .all()
    )


def obras_activas(db: Session) -> list[models.Obra]:
    return db.query(models.Obra).filter(models.Obra.activo.is_(True)).all()


# 1. FALTAS
def registrar_faltas(db: Session, ahora) -> int:
    # Marca una falta por cada día laborable ya terminado en que el trabajador
    # no registró una entrada válida. Se puede ejecutar varias veces: no repite.
    hoy = a_hora_local(ahora).date()
    desde = hoy - timedelta(days=DIAS_HACIA_ATRAS)
    nuevas = 0

    for obra in obras_activas(db):
        for usuario in trabajadores_de(db, obra):
            # No hay faltas anteriores al día en que se dio de alta al trabajador.
            dia = desde
            if usuario.creado_en is not None:
                dia = max(dia, a_hora_local(usuario.creado_en).date())

            entradas = (
                db.query(models.Asistencia.fecha_hora_fichaje)
                .filter(
                    models.Asistencia.usuario_id == usuario.id,
                    models.Asistencia.tipo == "entrada",
                    models.Asistencia.estatus_asistencia != FUERA_DE_RANGO,
                    models.Asistencia.fecha_hora_fichaje >= inicio_del_dia_utc(dia),
                )
                .all()
            )
            dias_cubiertos = {a_hora_local(fecha).date() for (fecha,) in entradas}
            dias_cubiertos.update(
                fecha
                for (fecha,) in db.query(models.Falta.fecha).filter(
                    models.Falta.usuario_id == usuario.id, models.Falta.fecha >= dia
                )
            )

            while dia < hoy:
                if es_dia_laborable(dia) and dia not in dias_cubiertos:
                    db.add(
                        models.Falta(usuario_id=usuario.id, obra_id=obra.id, fecha=dia)
                    )
                    nuevas += 1
                dia += timedelta(days=1)

    db.commit()
    return nuevas


# 2. REPORTE MATUTINO
def texto_del_reporte(db: Session, obra: models.Obra, ahora) -> str:
    trabajadores = trabajadores_de(db, obra)
    ids = [t.id for t in trabajadores]
    inicio, fin = limites_del_dia_utc(ahora)
    local = a_hora_local(ahora)

    entradas = (
        db.query(models.Asistencia)
        .filter(
            models.Asistencia.usuario_id.in_(ids),
            models.Asistencia.tipo == "entrada",
            models.Asistencia.estatus_asistencia != FUERA_DE_RANGO,
            models.Asistencia.fecha_hora_fichaje >= inicio,
            models.Asistencia.fecha_hora_fichaje < fin,
        )
        .all()
    )
    estatus = {e.usuario_id: e.estatus_asistencia for e in entradas}
    con_retardo = [t.nombre for t in trabajadores if estatus.get(t.id) == "Retardo"]
    sin_entrada = [t.nombre for t in trabajadores if t.id not in estatus]

    incidencias = (
        db.query(models.Incidencia)
        .filter(
            models.Incidencia.usuario_id.in_(ids),
            models.Incidencia.fecha == local.date(),
        )
        .all()
    )
    incidencias.sort(key=lambda i: (ORDEN_DE_PRIORIDAD.get(i.prioridad, 3), i.id))

    lineas = [
        f"*Reporte de {obra.nombre}*",
        f"{local.day} de {MESES[local.month - 1]}, {local:%H:%M}",
        "",
        f"Personal: {len(trabajadores)}",
        f"A tiempo: {len(estatus) - len(con_retardo)}",
        f"Con retardo: {len(con_retardo)}",
        *(f"• {nombre}" for nombre in con_retardo),
        f"Sin entrada: {len(sin_entrada)}",
        *(f"• {nombre}" for nombre in sin_entrada),
        "",
        f"Incidencias de hoy: {len(incidencias)}",
    ]
    for incidencia in incidencias:
        motivo = incidencia.motivo_texto
        if len(motivo) > 80:
            motivo = motivo[:77] + "..."
        lineas.append(
            f"• {incidencia.prioridad or 'Sin prioridad'} | "
            f"{incidencia.usuario.nombre}: {motivo}"
        )
    return "\n".join(lineas)


def enviar_reportes_matutinos(db: Session, ahora) -> int:
    # Al cerrar la tolerancia de entrada de cada obra, su supervisor recibe
    # quién llegó, quién no y las incidencias del día. Un reporte por obra y día.
    local = a_hora_local(ahora)
    hoy = local.date()
    if not es_dia_laborable(hoy):
        return 0

    enviados = 0
    for obra in obras_activas(db):
        if obra.hora_entrada is None or obra.ultimo_reporte == hoy:
            continue

        cierre = cierre_de_tolerancia(
            hoy, obra.hora_entrada, obra.minutos_tolerancia or 0
        )
        limite = cierre + timedelta(hours=HORAS_PARA_ENVIAR_REPORTE)
        if not cierre <= local < limite:
            continue

        supervisores = supervisores_de(db, obra)
        if not supervisores:
            continue

        texto = texto_del_reporte(db, obra, ahora)
        for supervisor in supervisores:
            enviar_texto(supervisor.telefono, texto)

        obra.ultimo_reporte = hoy
        db.commit()
        enviados += 1

    return enviados


# 3. PLANIFICADOR
def ejecutar(tarea):
    # Cada tarea abre su propia conexión y un error no detiene al planificador.
    db = SessionLocal()
    try:
        resultado = tarea(db, ahora_utc())
        if resultado:
            logger.info("Tarea programada %s: %s", tarea.__name__, resultado)
    except Exception:
        logger.exception("Error en la tarea programada %s", tarea.__name__)
    finally:
        db.close()


def iniciar_planificador() -> BackgroundScheduler:
    planificador = BackgroundScheduler(timezone=ZONA_LOCAL)

    # Faltas: poco después de la medianoche y también al arrancar el servidor,
    # por si estuvo apagado a esa hora.
    planificador.add_job(ejecutar, "cron", hour=0, minute=5, args=[registrar_faltas])
    planificador.add_job(ejecutar, "date", args=[registrar_faltas])

    # Reportes: se revisa cada pocos minutos si ya cerró la tolerancia de una obra.
    planificador.add_job(
        ejecutar,
        "interval",
        minutes=MINUTOS_ENTRE_REVISIONES,
        args=[enviar_reportes_matutinos],
    )

    planificador.start()
    return planificador
