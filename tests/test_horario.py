from datetime import datetime, time

from utils.horario import a_hora_local, estatus_de_entrada, limites_del_dia_utc

# México está 6 horas detrás de UTC: las 08:00 locales son las 14:00 UTC.
OCHO = time(8, 0)


def test_convierte_utc_a_hora_de_mexico():
    local = a_hora_local(datetime(2026, 10, 8, 14, 0))
    assert (local.hour, local.minute) == (8, 0)


def test_entrada_antes_de_la_hora_es_a_tiempo():
    assert estatus_de_entrada(datetime(2026, 10, 8, 13, 55), OCHO, 20) == "A tiempo"


def test_entrada_en_el_limite_de_tolerancia_es_a_tiempo():
    assert estatus_de_entrada(datetime(2026, 10, 8, 14, 20), OCHO, 20) == "A tiempo"


def test_entrada_despues_de_la_tolerancia_es_retardo():
    assert estatus_de_entrada(datetime(2026, 10, 8, 14, 21), OCHO, 20) == "Retardo"


def test_sin_tolerancia_un_minuto_tarde_es_retardo():
    assert estatus_de_entrada(datetime(2026, 10, 8, 14, 1), OCHO, 0) == "Retardo"


def test_el_dia_se_mide_en_hora_de_mexico():
    # Las 19:00 del día 8 en México ya son la 01:00 del día 9 en UTC.
    inicio, fin = limites_del_dia_utc(datetime(2026, 10, 9, 1, 0))
    assert inicio == datetime(2026, 10, 8, 6, 0)
    assert fin == datetime(2026, 10, 9, 6, 0)
