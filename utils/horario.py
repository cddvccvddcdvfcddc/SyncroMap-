from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

# Las fechas se guardan en UTC y las reglas de horario se aplican en hora local.
ZONA_LOCAL = ZoneInfo("America/Mexico_City")

# Días en que se espera al trabajador: de lunes (0) a sábado (5).
DIAS_LABORABLES = (0, 1, 2, 3, 4, 5)

MESES = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
    "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)  # fmt: skip


def ahora_utc() -> datetime:
    # Fecha y hora actual en UTC, sin zona, igual que se guarda en PostgreSQL
    return datetime.now(timezone.utc).replace(tzinfo=None)


def a_hora_local(fecha_utc: datetime) -> datetime:
    return fecha_utc.replace(tzinfo=timezone.utc).astimezone(ZONA_LOCAL)


def hoy_local() -> date:
    return a_hora_local(ahora_utc()).date()


def limites_del_dia_utc(fecha_utc: datetime) -> tuple[datetime, datetime]:
    # Inicio y fin (en UTC) del día local al que pertenece la fecha
    inicio_local = a_hora_local(fecha_utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    fin_local = inicio_local + timedelta(days=1)

    inicio = inicio_local.astimezone(timezone.utc).replace(tzinfo=None)
    fin = fin_local.astimezone(timezone.utc).replace(tzinfo=None)
    return inicio, fin


def inicio_del_mes_utc(fecha_utc: datetime) -> datetime:
    # Primer instante (en UTC) del mes local al que pertenece la fecha
    inicio_local = a_hora_local(fecha_utc).replace(
        day=1, hour=0, minute=0, second=0, microsecond=0
    )
    return inicio_local.astimezone(timezone.utc).replace(tzinfo=None)


def inicio_del_dia_utc(dia: date) -> datetime:
    # Primer instante (en UTC) de un día local
    inicio_local = datetime.combine(dia, time.min, tzinfo=ZONA_LOCAL)
    return inicio_local.astimezone(timezone.utc).replace(tzinfo=None)


def es_dia_laborable(dia: date) -> bool:
    return dia.weekday() in DIAS_LABORABLES


def cierre_de_tolerancia(
    dia: date, hora_entrada: time, minutos_tolerancia: int
) -> datetime:
    # Hora local hasta la que una entrada todavía cuenta como "A tiempo"
    return datetime.combine(dia, hora_entrada, tzinfo=ZONA_LOCAL) + timedelta(
        minutes=minutos_tolerancia
    )


def estatus_de_entrada(
    fecha_utc: datetime,
    hora_entrada: time,
    minutos_tolerancia: int,
) -> str:
    fecha_local = a_hora_local(fecha_utc)
    limite = cierre_de_tolerancia(fecha_local.date(), hora_entrada, minutos_tolerancia)

    return "A tiempo" if fecha_local <= limite else "Retardo"
