import { useState } from "react";
import { Circle, CircleMarker, useMapEvents } from "react-leaflet";

import { api } from "../api.js";
import MapaBase from "../componentes/MapaBase.jsx";
import {
  Aviso,
  Boton,
  Campo,
  Celda,
  Encabezado,
  Entrada,
  Estado,
  Etiqueta,
  Panel,
  Tabla,
  Ventana,
} from "../componentes/interfaz.jsx";
import { useDatos } from "../useDatos.js";

const NUEVA = {
  nombre: "",
  latitud_centro: "",
  longitud_centro: "",
  radio_tolerancia_m: 50,
  hora_entrada: "08:00",
  minutos_tolerancia: 20,
  activo: true,
};

function AlHacerClic({ alElegir }) {
  useMapEvents({ click: (evento) => alElegir(evento.latlng) });
  return null;
}

function Formulario({ obra, alGuardar, alCerrar }) {
  const [datos, setDatos] = useState({
    ...obra,
    hora_entrada: (obra.hora_entrada ?? "08:00").slice(0, 5),
  });
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState(null);
  const cambiar = (campo) => (e) => setDatos({ ...datos, [campo]: e.target.value });

  const latitud = Number(datos.latitud_centro);
  const longitud = Number(datos.longitud_centro);
  const hayCentro =
    datos.latitud_centro !== "" &&
    datos.longitud_centro !== "" &&
    Number.isFinite(latitud) &&
    Number.isFinite(longitud);
  const centro = hayCentro ? [latitud, longitud] : null;

  async function enviar(evento) {
    evento.preventDefault();
    if (!hayCentro) {
      setError("Haz clic en el mapa o escribe las coordenadas del centro de la obra.");
      return;
    }
    setGuardando(true);
    setError(null);
    const cuerpo = {
      nombre: datos.nombre.trim(),
      latitud_centro: latitud,
      longitud_centro: longitud,
      radio_tolerancia_m: Number(datos.radio_tolerancia_m),
      hora_entrada: datos.hora_entrada + ":00",
      minutos_tolerancia: Number(datos.minutos_tolerancia),
      activo: datos.activo,
    };
    try {
      if (obra.id) await api.actualizarObra(obra.id, cuerpo);
      else await api.crearObra(cuerpo);
      await alGuardar();
    } catch (fallo) {
      setError(fallo.message);
      setGuardando(false);
    }
  }

  return (
    <Ventana titulo={obra.id ? "Editar obra" : "Nueva obra"} alCerrar={alCerrar}>
      <form onSubmit={enviar} className="space-y-4">
        <Campo etiqueta="Nombre">
          <Entrada required maxLength={100} value={datos.nombre} onChange={cambiar("nombre")} />
        </Campo>

        <div>
          <p className="mb-1 text-xs font-medium text-tenue">
            Centro y perímetro (haz clic en el mapa para mover el centro)
          </p>
          <MapaBase puntos={centro ? [centro] : []} className="h-56">
            <AlHacerClic
              alElegir={({ lat, lng }) =>
                setDatos({
                  ...datos,
                  latitud_centro: lat.toFixed(7),
                  longitud_centro: lng.toFixed(7),
                })
              }
            />
            {centro && (
              <>
                <Circle
                  center={centro}
                  radius={Number(datos.radio_tolerancia_m) || 1}
                  pathOptions={{ color: "#0f766e", weight: 2, fillOpacity: 0.12 }}
                />
                <CircleMarker
                  center={centro}
                  radius={4}
                  pathOptions={{ color: "#0f766e", fillOpacity: 1 }}
                />
              </>
            )}
          </MapaBase>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <Campo etiqueta="Latitud">
            <Entrada
              required
              type="number"
              step="any"
              min={-90}
              max={90}
              value={datos.latitud_centro}
              onChange={cambiar("latitud_centro")}
            />
          </Campo>
          <Campo etiqueta="Longitud">
            <Entrada
              required
              type="number"
              step="any"
              min={-180}
              max={180}
              value={datos.longitud_centro}
              onChange={cambiar("longitud_centro")}
            />
          </Campo>
        </div>

        <div className="grid grid-cols-3 gap-3">
          <Campo etiqueta="Radio (metros)">
            <Entrada
              required
              type="number"
              min={1}
              step="any"
              value={datos.radio_tolerancia_m}
              onChange={cambiar("radio_tolerancia_m")}
            />
          </Campo>
          <Campo etiqueta="Hora de entrada">
            <Entrada required type="time" value={datos.hora_entrada} onChange={cambiar("hora_entrada")} />
          </Campo>
          <Campo etiqueta="Tolerancia (min)">
            <Entrada
              required
              type="number"
              min={0}
              step={1}
              value={datos.minutos_tolerancia}
              onChange={cambiar("minutos_tolerancia")}
            />
          </Campo>
        </div>

        {error && (
          <p role="alert" className="text-sm text-red-700">
            {error}
          </p>
        )}

        <div className="flex justify-end gap-2 pt-2">
          <Boton onClick={alCerrar}>Cancelar</Boton>
          <Boton type="submit" estilo="principal" disabled={guardando}>
            {guardando ? "Guardando…" : "Guardar"}
          </Boton>
        </div>
      </form>
    </Ventana>
  );
}

export default function Obras() {
  const [verInactivas, setVerInactivas] = useState(false);
  const [enEdicion, setEnEdicion] = useState(null);
  const [error, setError] = useState(null);

  const { datos, error: errorDeCarga, cargando, recargar } = useDatos(
    async () => {
      const [obras, usuarios] = await Promise.all([api.obras(verInactivas), api.usuarios()]);
      return { obras, usuarios };
    },
    [verInactivas],
  );

  const personalDe = (obra) => datos.usuarios.filter((u) => u.obra_id === obra.id).length;

  async function cambiarActiva(obra, activo) {
    setError(null);
    try {
      if (activo) {
        const { id, creado_en, ...resto } = obra;
        await api.actualizarObra(id, { ...resto, activo: true });
      } else {
        const asignados = personalDe(obra);
        const aviso =
          asignados > 0
            ? ` Tiene ${asignados} trabajador${asignados > 1 ? "es" : ""} asignado${asignados > 1 ? "s" : ""}, que ya no podrán fichar.`
            : "";
        if (!window.confirm(`¿Dar de baja "${obra.nombre}"?${aviso} Su historial se conserva.`)) {
          return;
        }
        await api.darDeBajaObra(obra.id);
      }
      await recargar();
    } catch (fallo) {
      setError(fallo.message);
    }
  }

  return (
    <>
      <Encabezado
        titulo="Obras"
        descripcion="El trabajador solo puede fichar dentro del radio de la obra que tiene asignada."
      >
        <label className="flex items-center gap-2 pb-1.5 text-sm text-tenue">
          <input
            type="checkbox"
            className="size-4 accent-marca-600"
            checked={verInactivas}
            onChange={(e) => setVerInactivas(e.target.checked)}
          />
          Ver dadas de baja
        </label>
        <Boton estilo="principal" onClick={() => setEnEdicion(NUEVA)}>
          Nueva obra
        </Boton>
      </Encabezado>

      {error && (
        <div className="mb-4">
          <Aviso tipo="error">{error}</Aviso>
        </div>
      )}

      <Estado error={errorDeCarga} cargando={cargando} hayDatos={datos}>
        {datos && (
          <Panel>
            <Tabla
              columnas={["Nombre", "Entrada", "Tolerancia", "Radio", "Personal", "Estado", ""]}
              vacio="Todavía no hay obras registradas."
            >
              {datos.obras
                .toSorted((a, b) => a.nombre.localeCompare(b.nombre))
                .map((obra) => (
                  <tr key={obra.id} className={obra.activo ? "" : "text-tenue"}>
                    <Celda className="font-medium">{obra.nombre}</Celda>
                    <Celda className="tabular-nums">{obra.hora_entrada?.slice(0, 5)}</Celda>
                    <Celda className="tabular-nums">{obra.minutos_tolerancia} min</Celda>
                    <Celda className="tabular-nums">{Math.round(obra.radio_tolerancia_m)} m</Celda>
                    <Celda className="tabular-nums">{personalDe(obra)}</Celda>
                    <Celda>
                      <Etiqueta tono={obra.activo ? "verde" : "gris"}>
                        {obra.activo ? "Activa" : "De baja"}
                      </Etiqueta>
                    </Celda>
                    <Celda className="text-right whitespace-nowrap">
                      {obra.activo ? (
                        <span className="inline-flex gap-2">
                          <Boton onClick={() => setEnEdicion(obra)}>Editar</Boton>
                          <Boton estilo="peligro" onClick={() => cambiarActiva(obra, false)}>
                            Dar de baja
                          </Boton>
                        </span>
                      ) : (
                        <Boton onClick={() => cambiarActiva(obra, true)}>Reactivar</Boton>
                      )}
                    </Celda>
                  </tr>
                ))}
            </Tabla>
          </Panel>
        )}
      </Estado>

      {enEdicion && (
        <Formulario
          obra={enEdicion}
          alCerrar={() => setEnEdicion(null)}
          alGuardar={async () => {
            setEnEdicion(null);
            await recargar();
          }}
        />
      )}
    </>
  );
}
