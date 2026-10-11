from datetime import datetime

import Model as models
from routers.asistencia import resumen_del_mes

# Jueves 8 de octubre de 2026, 07:50 hora de México.
AHORA = datetime(2026, 10, 8, 13, 50)


def fichar(db, usuario, dia, estatus="A tiempo", tipo="entrada", mes=10, hora=14):
    db.add(
        models.Asistencia(
            usuario_id=usuario.id,
            obra_id=usuario.obra_id,
            fecha_hora_fichaje=datetime(2026, mes, dia, hora),
            tipo=tipo,
            latitud_enviada=0,
            longitud_enviada=0,
            distancia_calculada_m=0,
            estatus_asistencia=estatus,
        )
    )
    db.commit()


def con_alta_el(db, usuario, mes, dia):
    usuario.creado_en = datetime(2026, mes, dia, 15)
    db.commit()
    return usuario


def test_resumen_del_mes(db, usuario):
    con_alta_el(db, usuario, 9, 1)
    fichar(db, usuario, 1)
    fichar(db, usuario, 2, "Retardo")
    fichar(db, usuario, 2, "Salida registrada", tipo="salida", hora=23)
    fichar(db, usuario, 5, "Fuera de rango")
    fichar(db, usuario, 30, mes=9)

    # Días laborables antes de hoy: 1, 2, 3, 5, 6 y 7 (el 4 es domingo).
    assert resumen_del_mes(db, usuario, AHORA) == {
        "asistencias": 2,
        "retardos": 1,
        "faltas": 4,
    }


def test_las_faltas_se_cuentan_desde_el_alta_del_trabajador(db, usuario):
    con_alta_el(db, usuario, 10, 6)
    assert resumen_del_mes(db, usuario, AHORA)["faltas"] == 2


def test_el_dia_de_hoy_cuenta_como_asistencia_pero_nunca_como_falta(db, usuario):
    con_alta_el(db, usuario, 10, 8)
    assert resumen_del_mes(db, usuario, AHORA)["faltas"] == 0

    fichar(db, usuario, 8, hora=13)
    assert resumen_del_mes(db, usuario, AHORA)["asistencias"] == 1


def test_el_mes_se_corta_con_la_hora_de_mexico(db, usuario):
    con_alta_el(db, usuario, 10, 8)
    # Las 03:00 UTC del 1 de octubre todavía son el 30 de septiembre en México.
    fichar(db, usuario, 1, hora=3)
    assert resumen_del_mes(db, usuario, AHORA)["asistencias"] == 0
