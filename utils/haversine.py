import math


def calcular_distancia(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    # Radio de la Tierra en metros
    R = 6371000.0

    # Convertir grados a radianes
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    # Fórmula de Haversine
    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )

    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))

    # Distancia en metros
    return R * c


def esta_en_rango(
    lat_usuario: float,
    lon_usuario: float,
    lat_obra: float,
    lon_obra: float,
    radio_maximo_m: float,
) -> bool:
    distancia = calcular_distancia(lat_usuario, lon_usuario, lat_obra, lon_obra)
    return distancia <= radio_maximo_m
