import { useEffect } from "react";
import { MapContainer, TileLayer, useMap } from "react-leaflet";

// Centro de México, por si todavía no hay ninguna obra que mostrar.
const CENTRO_POR_DEFECTO = [19.4326, -99.1332];

// Mueve el mapa para que quepan todos los puntos.
function Encuadre({ puntos }) {
  const mapa = useMap();
  const clave = JSON.stringify(puntos);

  useEffect(() => {
    if (puntos.length === 0) return;
    if (puntos.length === 1) {
      mapa.setView(puntos[0], 17);
    } else {
      mapa.fitBounds(puntos, { padding: [40, 40], maxZoom: 18 });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mapa, clave]);

  return null;
}

// Mapa de OpenStreetMap (gratuito). `puntos` son los [latitud, longitud] que deben verse.
export default function MapaBase({ puntos = [], className = "h-96", children }) {
  return (
    <MapContainer
      center={puntos[0] ?? CENTRO_POR_DEFECTO}
      zoom={puntos.length ? 17 : 5}
      className={`w-full rounded-lg ${className}`}
    >
      <TileLayer
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
        maxZoom={19}
      />
      <Encuadre puntos={puntos} />
      {children}
    </MapContainer>
  );
}
