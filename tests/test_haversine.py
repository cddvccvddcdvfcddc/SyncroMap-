import pytest

from utils.haversine import calcular_distancia, esta_en_rango


def test_mismo_punto_da_cero():
    assert calcular_distancia(19.4326, -99.1332, 19.4326, -99.1332) == 0


def test_un_grado_de_latitud_mide_unos_111_km():
    assert calcular_distancia(0, 0, 1, 0) == pytest.approx(111195, abs=1)


def test_la_distancia_es_igual_en_ambos_sentidos():
    ida = calcular_distancia(19.4326, -99.1332, 19.5, -99.2)
    vuelta = calcular_distancia(19.5, -99.2, 19.4326, -99.1332)
    assert ida == pytest.approx(vuelta)


def test_distancia_corta_dentro_de_la_ciudad():
    # 0.0003 grados de latitud son unos 33 metros.
    distancia = calcular_distancia(19.4326, -99.1332, 19.4329, -99.1332)
    assert distancia == pytest.approx(33.4, abs=0.5)


def test_esta_en_rango():
    assert esta_en_rango(19.4329, -99.1332, 19.4326, -99.1332, 50)
    assert not esta_en_rango(19.4329, -99.1332, 19.4326, -99.1332, 30)
