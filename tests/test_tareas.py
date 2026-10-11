from datetime import date, datetime

import pytest

import Model as models
import tareas

# Jueves 8 de octubre de 2026 en hora de México (UTC-6).
ANTES_DEL_CIERRE = datetime(2026, 10, 8, 13, 50)  # 07:50
DESPUES_DEL_CIERRE = datetime(2026, 10, 8, 14, 25)  # 08:25; la tolerancia cierra 08:20
DEMASIADO_TARDE = datetime(2026, 10, 8, 17, 0)  # 11:00
DOMINGO = datetime(2026, 10, 11, 14, 25)


def alta(db, obra, nombre, telefono, dia=1, **extra):
    usuario = models.Usuario(
        nombre=nombre,
        telefono=telefono,
        obra_id=obra.id,
        creado_en=datetime(2026, 10, dia, 15),
        **extra,
    )
    db.add(usuario)
    db.commit()
    return usuario


def entrada(db, usuario, dia, estatus="A tiempo", hora=14):
    db.add(
        models.Asistencia(
            usuario_id=usuario.id,
            obra_id=usuario.obra_id,
            fecha_hora_fichaje=datetime(2026, 10, dia, hora),
            tipo="entrada",
            latitud_enviada=0,
            longitud_enviada=0,
            distancia_calculada_m=0,
            estatus_asistencia=estatus,
        )
    )
    db.commit()


def fechas_de_falta(db, usuario):
    faltas = db.query(models.Falta).filter(models.Falta.usuario_id == usuario.id)
    return sorted(f.fecha.day for f in faltas)


@pytest.fixture
def enviados(monkeypatch):
    mensajes = []
    monkeypatch.setattr(
        tareas, "enviar_texto", lambda telefono, texto: mensajes.append((telefono, texto))
    )
    return mensajes


# ---------- Faltas ----------


def test_falta_por_cada_dia_laborable_sin_entrada(db, obra):
    trabajador = alta(db, obra, "Ana", "1")
    entrada(db, trabajador, 1)
    entrada(db, trabajador, 2, "Retardo")
    entrada(db, trabajador, 5, "Fuera de rango")

    assert tareas.registrar_faltas(db, ANTES_DEL_CIERRE) == 4
    # El 4 es domingo y el 8 es hoy: ninguno de los dos cuenta.
    assert fechas_de_falta(db, trabajador) == [3, 5, 6, 7]


def test_registrar_faltas_dos_veces_no_las_repite(db, obra):
    alta(db, obra, "Ana", "1", dia=6)

    assert tareas.registrar_faltas(db, ANTES_DEL_CIERRE) == 2
    assert tareas.registrar_faltas(db, ANTES_DEL_CIERRE) == 0
    assert db.query(models.Falta).count() == 2


def test_no_hay_faltas_antes_del_alta_del_trabajador(db, obra):
    trabajador = alta(db, obra, "Ana", "1", dia=7)
    tareas.registrar_faltas(db, ANTES_DEL_CIERRE)
    assert fechas_de_falta(db, trabajador) == [7]


def test_solo_se_revisan_los_ultimos_dias(db, obra, monkeypatch):
    monkeypatch.setattr(tareas, "DIAS_HACIA_ATRAS", 2)
    trabajador = alta(db, obra, "Ana", "1")
    tareas.registrar_faltas(db, ANTES_DEL_CIERRE)
    assert fechas_de_falta(db, trabajador) == [6, 7]


def test_a_quien_no_se_le_marcan_faltas(db, obra):
    alta(db, obra, "Iván", "2", activo=False)
    db.add(models.Usuario(nombre="Olga", telefono="3"))  # sin obra asignada
    db.commit()

    assert tareas.registrar_faltas(db, ANTES_DEL_CIERRE) == 0

    obra.activo = False
    alta(db, obra, "Ana", "4")
    assert tareas.registrar_faltas(db, ANTES_DEL_CIERRE) == 0
    assert db.query(models.Falta).count() == 0


def test_al_supervisor_tambien_se_le_marcan_faltas(db, obra):
    supervisor = alta(db, obra, "Sara", "1", dia=7, rol="supervisor")
    tareas.registrar_faltas(db, ANTES_DEL_CIERRE)
    assert fechas_de_falta(db, supervisor) == [7]


# ---------- Reporte matutino ----------


@pytest.fixture
def cuadrilla(db, obra):
    # Ana y Sara (la supervisora) llegaron a tiempo, Beto con retardo y Carla no ha llegado.
    ana = alta(db, obra, "Ana", "1")
    beto = alta(db, obra, "Beto", "2")
    carla = alta(db, obra, "Carla", "3")
    supervisor = alta(db, obra, "Sara", "5215500000009", rol="supervisor")
    entrada(db, ana, 8, hora=13)
    entrada(db, supervisor, 8, hora=13)
    entrada(db, beto, 8, "Retardo", hora=14)
    return {"ana": ana, "beto": beto, "carla": carla, "supervisor": supervisor}


def test_texto_del_reporte(db, obra, cuadrilla):
    db.add_all(
        [
            models.Incidencia(
                usuario_id=cuadrilla["beto"].id,
                fecha=date(2026, 10, 8),
                motivo_texto="voy a llegar tarde",
                categoria="Retardo",
                prioridad="Media",
            ),
            models.Incidencia(
                usuario_id=cuadrilla["carla"].id,
                fecha=date(2026, 10, 8),
                motivo_texto="me caí del andamio",
                categoria="General",
                prioridad="Alta",
            ),
            models.Incidencia(
                usuario_id=cuadrilla["ana"].id,
                fecha=date(2026, 10, 7),
                motivo_texto="esta es de ayer",
                categoria="General",
                prioridad="Baja",
            ),
        ]
    )
    db.commit()

    assert tareas.texto_del_reporte(db, obra, DESPUES_DEL_CIERRE) == (
        "*Reporte de Obra de prueba*\n"
        "8 de octubre, 08:25\n"
        "\n"
        "Personal: 4\n"
        "A tiempo: 2\n"
        "Con retardo: 1\n"
        "• Beto\n"
        "Sin entrada: 1\n"
        "• Carla\n"
        "\n"
        "Incidencias de hoy: 2\n"
        "• Alta | Carla: me caí del andamio\n"
        "• Media | Beto: voy a llegar tarde"
    )


def test_el_reporte_se_envia_al_cerrar_la_tolerancia(db, obra, cuadrilla, enviados):
    assert tareas.enviar_reportes_matutinos(db, ANTES_DEL_CIERRE) == 0
    assert enviados == []

    assert tareas.enviar_reportes_matutinos(db, DESPUES_DEL_CIERRE) == 1
    (telefono, texto), = enviados
    assert telefono == cuadrilla["supervisor"].telefono
    assert texto.startswith("*Reporte de Obra de prueba*")


def test_el_reporte_se_envia_una_sola_vez_al_dia(db, obra, cuadrilla, enviados):
    tareas.enviar_reportes_matutinos(db, DESPUES_DEL_CIERRE)
    assert tareas.enviar_reportes_matutinos(db, DESPUES_DEL_CIERRE) == 0
    assert len(enviados) == 1


@pytest.mark.parametrize("momento", [DEMASIADO_TARDE, DOMINGO])
def test_el_reporte_no_se_envia_tarde_ni_en_domingo(db, obra, cuadrilla, enviados, momento):
    assert tareas.enviar_reportes_matutinos(db, momento) == 0
    assert enviados == []


def test_sin_supervisor_el_reporte_queda_pendiente(db, obra, cuadrilla, enviados):
    cuadrilla["supervisor"].activo = False
    db.commit()

    assert tareas.enviar_reportes_matutinos(db, DESPUES_DEL_CIERRE) == 0
    assert obra.ultimo_reporte is None
