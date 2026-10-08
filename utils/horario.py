from datetime import datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

# Las fechas se guardan en UTC y las reglas de horario se aplican en hora local.
ZONA_LOCAL = ZoneInfo("America/Mexico_City")


def ahora_utc() -> datetime:
    # Fecha y hora actual en UTC, sin zona, igual que se guarda en PostgreSQL
    return datetime.now(timezone.utc).replace(tzinfo=None)


def a_hora_local(fecha_utc: datetime) -> datetime:
    return fecha_utc.replace(tzinfo=timezone.utc).astimezone(ZONA_LOCAL)


def limites_del_dia_utc(fecha_utc: datetime) -> tuple[datetime, datetime]:
    # Inicio y fin (en UTC) del día local al que pertenece la fecha
    inicio_local = a_hora_local(fecha_utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    fin_local = inicio_local + timedelta(days=1)

    inicio = inicio_local.astimezone(timezone.utc).replace(tzinfo=None)
    fin = fin_local.astimezone(timezone.utc).replace(tzinfo=None)
    return inicio, fin


def estatus_de_entrada(
    fecha_utc: datetime,
    hora_entrada: time,
    minutos_tolerancia: int,
) -> str:
    fecha_local = a_hora_local(fecha_utc)
    limite = datetime.combine(
        fecha_local.date(), hora_entrada, tzinfo=ZONA_LOCAL
    ) + timedelta(minutes=minutos_tolerancia)

    return "A tiempo" if fecha_local <= limite else "Retardo"
