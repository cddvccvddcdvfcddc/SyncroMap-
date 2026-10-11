import pytest

from utils.clasificador import (
    CONFIANZA_MINIMA,
    SIN_INCIDENCIA,
    Clasificacion,
    clasificar,
    leer_ejemplos,
)

CATEGORIAS = {"Retardo", "Ausencia", "Permiso", "General", SIN_INCIDENCIA}
PRIORIDADES = {"Alta", "Media", "Baja"}


# Ninguna de estas frases está escrita igual en los ejemplos de entrenamiento.
@pytest.mark.parametrize(
    "texto, categoria, prioridad",
    [
        ("voy a llegar tarde, hay tráfico", "Retardo", "Media"),
        ("el camion se descompuso voy tarde", "Retardo", "Media"),
        ("Buenos días, hoy no voy a poder presentarme, tengo gripa", "Ausencia", "Media"),
        ("ando malo de la panza hoy no voy", "Ausencia", "Media"),
        ("tengo cita en el imss el lunes no voy a ir", "Ausencia", "Baja"),
        ("necesito permiso el viernes para ir al doctor", "Permiso", "Baja"),
        ("me deja salir temprano hoy", "Permiso", "Media"),
        ("un compañero se cortó con la sierra", "General", "Alta"),
        ("no hay cemento", "General", "Media"),
    ],
)
def test_clasifica_incidencias_en_texto_libre(texto, categoria, prioridad):
    resultado = clasificar(texto)
    assert (resultado.categoria, resultado.prioridad) == (categoria, prioridad)
    assert resultado.es_incidencia


@pytest.mark.parametrize(
    "texto", ["hola", "gracias", "Entrada", "SALIDA", "ya llegué", "cuántos retardos llevo?"]
)
def test_lo_que_no_es_incidencia(texto):
    assert not clasificar(texto).es_incidencia


def test_la_confianza_baja_marca_la_clasificacion_como_ambigua():
    assert Clasificacion("Retardo", "Media", CONFIANZA_MINIMA - 0.01).ambigua
    assert not Clasificacion("Retardo", "Media", CONFIANZA_MINIMA).ambigua


def test_los_ejemplos_de_entrenamiento_estan_bien_etiquetados():
    for ejemplo in leer_ejemplos():
        assert ejemplo["texto"].strip()
        assert ejemplo["categoria"] in CATEGORIAS
        if ejemplo["categoria"] == SIN_INCIDENCIA:
            assert ejemplo["prioridad"] == ""
        else:
            assert ejemplo["prioridad"] in PRIORIDADES
