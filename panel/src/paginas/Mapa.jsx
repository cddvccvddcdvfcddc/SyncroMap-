import { useState } from "react";
import { Circle, CircleMarker, Popup, Tooltip } from "react-leaflet";

import { api } from "../api.js";
import MapaBase from "../componentes/MapaBase.jsx";
import { Campo, Encabezado, Entrada, Estado, Panel } from "../componentes/interfaz.jsx";
import { diaLocal, hora } from "../fechas.js";
import { useDatos } from "../useDatos.js";

// Un color por estatus, igual que en el resto del panel.
const COLORES = [
  { nombre: "A tiempo", color: "#059669", estatus: ["A tiempo", "Dentro de rango"] },
  { nombre: "Retardo", color: "#d97706", estatus: ["Retardo"] },
  { nombre: "Fuera de rango", color: "#dc2626", estatus: ["Fuera de rango"] },
  { nombre: "Salida", color: "#475569", estatus: ["Salida registrada"] },
];

function colorDe(estatus) {
  return COLORES.find((c) => c.estatus.includes(estatus))?.color ?? "#475569";
}

export default function Mapa() {
  const [dia, setDia] = useState(diaLocal);
  const esHoy = dia === diaLocal();

  const { datos, error, cargando } = useDatos(
    async () => {
      const [obras, usuarios, asistencias] = await Promise.all([
        api.obras(),
        api.usuarios(true),
        api.asistencias({ desde: dia, hasta: dia }),
      ]);
      return { obras, usuarios, asistencias };
    },
    [dia],
    { cadaSegundos: esHoy ? 30 : undefined },
  );

  const nombreDe = (id) => datos.usuarios.find((u) => u.id === id)?.nombre ?? `Usuario ${id}`;
  const puntos = datos
    ? [
        ...datos.obras.map((o) => [o.latitud_centro, o.longitud_centro]),
        ...datos.asistencias.map((a) => [a.latitud_enviada, a.longitud_enviada]),
      ]
    : [];

  return (
    <>
      <Encabezado
        titulo="Mapa"
        descripcion="Cada círculo es el perímetro de una obra; cada punto, un fichaje del día."
      >
        <Campo etiqueta="Día">
          <Entrada type="date" value={dia} max={diaLocal()} onChange={(e) => setDia(e.target.value)} />
        </Campo>
      </Encabezado>

      <Estado error={error} cargando={cargando} hayDatos={datos}>
        {datos && (
          <Panel className="p-3">
            <MapaBase puntos={puntos} className="h-[32rem]">
              {datos.obras.map((obra) => (
                <Circle
                  key={obra.id}
                  center={[obra.latitud_centro, obra.longitud_centro]}
                  radius={obra.radio_tolerancia_m}
                  pathOptions={{ color: "#0f766e", weight: 2, fillOpacity: 0.08 }}
                >
                  <Tooltip>
                    {obra.nombre} · radio de {Math.round(obra.radio_tolerancia_m)} m
                  </Tooltip>
                </Circle>
              ))}

              {/* Del más antiguo al más reciente, para que el último quede encima. */}
              {datos.asistencias.toReversed().map((fichaje) => (
                <CircleMarker
                  key={fichaje.id}
                  center={[fichaje.latitud_enviada, fichaje.longitud_enviada]}
                  radius={7}
                  pathOptions={{
                    color: "#ffffff",
                    weight: 2,
                    fillColor: colorDe(fichaje.estatus_asistencia),
                    fillOpacity: 1,
                  }}
                >
                  <Popup>
                    <strong>{nombreDe(fichaje.usuario_id)}</strong>
                    <br />
                    {fichaje.tipo === "entrada" ? "Entrada" : "Salida"} a las{" "}
                    {hora(fichaje.fecha_hora_fichaje)}
                    <br />
                    {fichaje.estatus_asistencia} · a {Math.round(fichaje.distancia_calculada_m)} m
                    del centro
                  </Popup>
                </CircleMarker>
              ))}
            </MapaBase>

            <div className="flex flex-wrap items-center gap-x-5 gap-y-1 px-1 pt-3 text-xs text-tenue">
              {COLORES.map((c) => (
                <span key={c.nombre} className="inline-flex items-center gap-1.5">
                  <span
                    aria-hidden="true"
                    className="size-2.5 rounded-full"
                    style={{ backgroundColor: c.color }}
                  />
                  {c.nombre}
                </span>
              ))}
              <span className="ml-auto">
                {datos.asistencias.length === 0
                  ? "Sin fichajes este día"
                  : `${datos.asistencias.length} fichaje${datos.asistencias.length > 1 ? "s" : ""}`}
              </span>
            </div>
          </Panel>
        )}
      </Estado>
    </>
  );
}
