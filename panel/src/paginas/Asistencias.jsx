import { useState } from "react";

import { api } from "../api.js";
import {
  Campo,
  Celda,
  Encabezado,
  Entrada,
  Estado,
  Etiqueta,
  Panel,
  Selector,
  Tabla,
  tonoDeEstatus,
} from "../componentes/interfaz.jsx";
import { diaDe, diaLegible, diaLocal, hora, primerDiaDelMes } from "../fechas.js";
import { useDatos } from "../useDatos.js";

const VISTAS = [
  { clave: "fichajes", nombre: "Fichajes" },
  { clave: "faltas", nombre: "Faltas" },
];

export default function Asistencias() {
  const [vista, setVista] = useState("fichajes");
  const [filtros, setFiltros] = useState({
    desde: primerDiaDelMes(),
    hasta: diaLocal(),
    obra_id: "",
    usuario_id: "",
  });
  const cambiar = (campo) => (e) => setFiltros({ ...filtros, [campo]: e.target.value });

  const catalogos = useDatos(async () => {
    const [obras, usuarios] = await Promise.all([api.obras(true), api.usuarios(true)]);
    return { obras, usuarios };
  });
  const registros = useDatos(async () => {
    const pedir = vista === "fichajes" ? api.asistencias : api.faltas;
    return { vista, filas: await pedir(filtros) };
  }, [vista, filtros]);
  // Al cambiar de pestaña, por un instante siguen en memoria las filas de la
  // otra; no se pintan hasta que llegan las que corresponden.
  const filas = registros.datos?.vista === vista ? registros.datos.filas : null;

  const nombreDe = (lista, id) => lista?.find((x) => x.id === id)?.nombre ?? `#${id}`;
  const usuario = (id) => nombreDe(catalogos.datos?.usuarios, id);
  const obra = (id) => nombreDe(catalogos.datos?.obras, id);

  return (
    <>
      <Encabezado
        titulo="Asistencias"
        descripcion="Historial de entradas, salidas, intentos fuera de rango y faltas."
      />

      <Panel className="mb-6 p-4">
        <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
          <Campo etiqueta="Desde">
            <Entrada type="date" value={filtros.desde} max={filtros.hasta} onChange={cambiar("desde")} />
          </Campo>
          <Campo etiqueta="Hasta">
            <Entrada type="date" value={filtros.hasta} min={filtros.desde} onChange={cambiar("hasta")} />
          </Campo>
          <Campo etiqueta="Obra">
            <Selector value={filtros.obra_id} onChange={cambiar("obra_id")}>
              <option value="">Todas</option>
              {catalogos.datos?.obras.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.nombre}
                </option>
              ))}
            </Selector>
          </Campo>
          <Campo etiqueta="Trabajador">
            <Selector value={filtros.usuario_id} onChange={cambiar("usuario_id")}>
              <option value="">Todos</option>
              {catalogos.datos?.usuarios.map((u) => (
                <option key={u.id} value={u.id}>
                  {u.nombre}
                </option>
              ))}
            </Selector>
          </Campo>
        </div>
      </Panel>

      <div role="tablist" aria-label="Tipo de registro" className="mb-3 flex gap-1">
        {VISTAS.map(({ clave, nombre }) => (
          <button
            key={clave}
            type="button"
            role="tab"
            aria-selected={vista === clave}
            onClick={() => setVista(clave)}
            className={`rounded-md px-3 py-1.5 text-sm font-medium ${
              vista === clave ? "bg-marca-600 text-white" : "text-tenue hover:bg-white"
            }`}
          >
            {nombre}
          </button>
        ))}
        {filas && (
          <span className="ml-auto self-center text-xs text-tenue">
            {filas.length} registro{filas.length === 1 ? "" : "s"}
          </span>
        )}
      </div>

      <Estado
        error={catalogos.error ?? registros.error}
        cargando={registros.cargando}
        hayDatos={filas}
      >
        {filas && (
          <Panel>
            {vista === "fichajes" ? (
              <Tabla
                columnas={["Día", "Hora", "Trabajador", "Obra", "Tipo", "Estatus", "Distancia"]}
                vacio="No hay fichajes con esos filtros."
              >
                {filas.map((fichaje) => (
                  <tr key={fichaje.id}>
                    <Celda className="whitespace-nowrap">
                      {diaLegible(diaDe(fichaje.fecha_hora_fichaje))}
                    </Celda>
                    <Celda className="tabular-nums">{hora(fichaje.fecha_hora_fichaje)}</Celda>
                    <Celda className="font-medium">{usuario(fichaje.usuario_id)}</Celda>
                    <Celda className="text-tenue">{obra(fichaje.obra_id)}</Celda>
                    <Celda className="capitalize">{fichaje.tipo}</Celda>
                    <Celda>
                      <Etiqueta tono={tonoDeEstatus(fichaje.estatus_asistencia)}>
                        {fichaje.estatus_asistencia}
                      </Etiqueta>
                    </Celda>
                    <Celda className="text-right tabular-nums">
                      {Math.round(fichaje.distancia_calculada_m).toLocaleString("es-MX")} m
                    </Celda>
                  </tr>
                ))}
              </Tabla>
            ) : (
              <Tabla columnas={["Día", "Trabajador", "Obra", ""]} vacio="No hay faltas con esos filtros.">
                {filas.map((falta) => (
                  <tr key={falta.id}>
                    <Celda className="whitespace-nowrap">{diaLegible(falta.fecha)}</Celda>
                    <Celda className="font-medium">{usuario(falta.usuario_id)}</Celda>
                    <Celda className="text-tenue">{obra(falta.obra_id)}</Celda>
                    <Celda>
                      <Etiqueta tono="rojo">Falta</Etiqueta>
                    </Celda>
                  </tr>
                ))}
              </Tabla>
            )}
          </Panel>
        )}
      </Estado>
    </>
  );
}
