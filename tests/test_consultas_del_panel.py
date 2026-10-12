from datetime import date, datetime

import Model as models
import routers.asistencia as asistencia
import routers.incidencias as incidencias


def fichaje(db, usuario, dia, hora, tipo="entrada", estatus="A tiempo"):
    db.add(
        models.Asistencia(
            usuario_id=usuario.id,
            obra_id=usuario.obra_id,
            fecha_hora_fichaje=datetime(2026, 10, dia, hora),
            tipo=tipo,
            latitud_enviada=0,
            longitud_enviada=0,
            distancia_calculada_m=0,
            estatus_asistencia=estatus,
        )
    )
    db.commit()


def listar(funcion, db, **filtros):
    vacios = {"desde": None, "hasta": None, "obra_id": None, "usuario_id": None}
    return funcion(db=db, **(vacios | filtros))


def test_los_fichajes_se_filtran_por_dia_de_mexico(db, usuario):
    fichaje(db, usuario, 8, 3)  # 7 de octubre a las 21:00 en México
    fichaje(db, usuario, 8, 14)  # 8 de octubre a las 08:00
    fichaje(db, usuario, 9, 5, tipo="salida", estatus="Salida registrada")  # 8, 23:00
    fichaje(db, usuario, 9, 14)  # 9 de octubre a las 08:00

    del_dia = listar(
        asistencia.listar_asistencias, db, desde=date(2026, 10, 8), hasta=date(2026, 10, 8)
    )

    # Los más recientes primero.
    assert [(f.tipo, f.fecha_hora_fichaje.hour) for f in del_dia] == [
        ("salida", 5),
        ("entrada", 14),
    ]
    assert len(listar(asistencia.listar_asistencias, db)) == 4


def test_los_fichajes_se_filtran_por_obra_y_trabajador(db, usuario):
    fichaje(db, usuario, 8, 14)

    assert len(listar(asistencia.listar_asistencias, db, obra_id=usuario.obra_id)) == 1
    assert listar(asistencia.listar_asistencias, db, obra_id=usuario.obra_id + 1) == []
    assert listar(asistencia.listar_asistencias, db, usuario_id=usuario.id + 1) == []


def test_las_faltas_se_filtran_por_fecha(db, usuario):
    for dia in (5, 6, 7):
        db.add(
            models.Falta(
                usuario_id=usuario.id, obra_id=usuario.obra_id, fecha=date(2026, 10, dia)
            )
        )
    db.commit()

    faltas = listar(
        asistencia.listar_faltas, db, desde=date(2026, 10, 6), hasta=date(2026, 10, 7)
    )

    assert [f.fecha.day for f in faltas] == [7, 6]
    assert listar(asistencia.listar_faltas, db, usuario_id=usuario.id + 1) == []


def test_las_incidencias_se_filtran_por_fecha(db, usuario):
    for dia in (7, 8):
        db.add(
            models.Incidencia(
                usuario_id=usuario.id,
                fecha=date(2026, 10, dia),
                motivo_texto=f"aviso del día {dia}",
                categoria="General",
                prioridad="Baja",
            )
        )
    db.commit()

    del_dia = incidencias.listar_incidencias(
        prioridad=None,
        estatus_revision=None,
        usuario_id=None,
        desde=date(2026, 10, 8),
        hasta=date(2026, 10, 8),
        db=db,
    )

    assert [i.motivo_texto for i in del_dia] == ["aviso del día 8"]
