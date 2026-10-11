import pytest
from fastapi import HTTPException

import routers.incidencias as incidencias
from schemas import IncidenciaCreate, IncidenciaRevision
from utils.clasificador import SIN_INCIDENCIA, Clasificacion


def reporte(usuario, texto):
    return IncidenciaCreate(telefono_remitente=usuario.telefono, motivo_texto=texto)


def clasificar_como(monkeypatch, categoria, prioridad, confianza):
    monkeypatch.setattr(
        incidencias,
        "clasificar",
        lambda texto: Clasificacion(categoria, prioridad, confianza),
    )


def test_la_incidencia_se_guarda_clasificada(db, usuario):
    texto = "voy a llegar tarde, hay tráfico"
    incidencia = incidencias.crear_incidencia(reporte(usuario, texto), db)

    assert incidencia.motivo_texto == texto
    assert (incidencia.categoria, incidencia.prioridad) == ("Retardo", "Media")
    assert incidencia.estatus_revision == incidencias.PENDIENTE
    assert 0 < incidencia.confianza <= 1


def test_la_clasificacion_dudosa_queda_para_revision_humana(db, usuario, monkeypatch):
    clasificar_como(monkeypatch, "Permiso", "Baja", 0.41)
    incidencia = incidencias.crear_incidencia(reporte(usuario, "un mensaje confuso"), db)

    assert incidencia.estatus_revision == incidencias.AMBIGUA
    assert (incidencia.categoria, incidencia.prioridad) == ("Permiso", "Baja")


def test_un_reporte_que_no_parece_incidencia_tambien_se_revisa(db, usuario, monkeypatch):
    clasificar_como(monkeypatch, SIN_INCIDENCIA, "Media", 0.95)
    incidencia = incidencias.crear_incidencia(reporte(usuario, "buenos días"), db)

    assert incidencia.categoria == "General"
    assert incidencia.estatus_revision == incidencias.AMBIGUA


def test_incidencia_de_un_telefono_desconocido(db):
    datos = IncidenciaCreate(telefono_remitente="000", motivo_texto="estoy enfermo")
    with pytest.raises(HTTPException) as error:
        incidencias.crear_incidencia(datos, db)
    assert error.value.status_code == 404


def test_incidencia_de_un_usuario_inactivo(db, usuario):
    usuario.activo = False
    db.commit()
    with pytest.raises(HTTPException) as error:
        incidencias.crear_incidencia(reporte(usuario, "estoy enfermo"), db)
    assert error.value.status_code == 400


def test_la_revision_corrige_y_conserva_el_mensaje_original(db, usuario):
    texto = "voy a llegar tarde, hay tráfico"
    creada = incidencias.crear_incidencia(reporte(usuario, texto), db)

    revisada = incidencias.revisar_incidencia(
        creada.id, IncidenciaRevision(prioridad="Alta"), db
    )

    assert revisada.prioridad == "Alta"
    assert revisada.categoria == "Retardo"
    assert revisada.estatus_revision == incidencias.REVISADA
    assert revisada.motivo_texto == texto


def test_revisar_una_incidencia_inexistente(db):
    with pytest.raises(HTTPException) as error:
        incidencias.revisar_incidencia(999, IncidenciaRevision(), db)
    assert error.value.status_code == 404


def test_las_listas_se_filtran_por_prioridad_y_estatus(db, usuario, monkeypatch):
    clasificar_como(monkeypatch, "General", "Alta", 0.9)
    incidencias.crear_incidencia(reporte(usuario, "me caí del andamio"), db)
    clasificar_como(monkeypatch, "Retardo", "Media", 0.3)
    incidencias.crear_incidencia(reporte(usuario, "ahí voy llegando"), db)

    def listar(**filtros):
        filtros = {"prioridad": None, "estatus_revision": None, "usuario_id": None} | filtros
        return incidencias.listar_incidencias(db=db, **filtros)

    assert [i.prioridad for i in listar()] == ["Media", "Alta"]
    assert [i.categoria for i in listar(prioridad="Alta")] == ["General"]
    assert [i.categoria for i in listar(estatus_revision="Ambigua")] == ["Retardo"]
    assert listar(usuario_id=usuario.id + 1) == []
