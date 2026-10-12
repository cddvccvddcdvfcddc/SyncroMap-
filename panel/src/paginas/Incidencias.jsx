import { useState } from "react";

import { api } from "../api.js";
import {
  Aviso,
  Boton,
  Campo,
  Encabezado,
  Estado,
  Etiqueta,
  Panel,
  Selector,
  TONO_DE_PRIORIDAD,
  TONO_DE_REVISION,
} from "../componentes/interfaz.jsx";
import { diaLegible } from "../fechas.js";
import { useDatos } from "../useDatos.js";

const CATEGORIAS = ["Retardo", "Ausencia", "Permiso", "General"];
const PRIORIDADES = ["Alta", "Media", "Baja"];
const ESTATUS = ["Pendiente", "Ambigua", "Revisada"];

// Una incidencia con los controles para que una persona confirme o corrija
// lo que propuso el clasificador.
function Incidencia({ incidencia, trabajador, alRevisar }) {
  const [categoria, setCategoria] = useState(incidencia.categoria);
  const [prioridad, setPrioridad] = useState(incidencia.prioridad ?? "Media");
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState(null);

  const revisada = incidencia.estatus_revision === "Revisada";
  const sinCambios =
    categoria === incidencia.categoria && prioridad === incidencia.prioridad;

  async function guardar() {
    setGuardando(true);
    setError(null);
    try {
      await api.revisarIncidencia(incidencia.id, { categoria, prioridad });
      await alRevisar();
    } catch (fallo) {
      setError(fallo.message);
    } finally {
      setGuardando(false);
    }
  }

  return (
    <li className="px-4 py-4">
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <span className="text-sm font-medium">{trabajador}</span>
        <span className="text-xs text-tenue">{diaLegible(incidencia.fecha)}</span>
        <span className="ml-auto flex items-center gap-2">
          <Etiqueta tono={TONO_DE_PRIORIDAD[incidencia.prioridad]}>
            {incidencia.prioridad ?? "Sin prioridad"}
          </Etiqueta>
          <Etiqueta tono={TONO_DE_REVISION[incidencia.estatus_revision]}>
            {incidencia.estatus_revision}
          </Etiqueta>
        </span>
      </div>

      <p className="mt-2 text-sm">“{incidencia.motivo_texto}”</p>

      <div className="mt-3 flex flex-wrap items-end gap-3">
        <Campo etiqueta="Categoría">
          <Selector value={categoria} onChange={(e) => setCategoria(e.target.value)}>
            {CATEGORIAS.map((c) => (
              <option key={c}>{c}</option>
            ))}
          </Selector>
        </Campo>
        <Campo etiqueta="Prioridad">
          <Selector value={prioridad} onChange={(e) => setPrioridad(e.target.value)}>
            {PRIORIDADES.map((p) => (
              <option key={p}>{p}</option>
            ))}
          </Selector>
        </Campo>
        <Boton
          estilo={revisada ? "secundario" : "principal"}
          disabled={guardando || (revisada && sinCambios)}
          onClick={guardar}
        >
          {guardando
            ? "Guardando…"
            : sinCambios
              ? revisada
                ? "Revisada"
                : "Confirmar"
              : "Guardar corrección"}
        </Boton>
        {incidencia.confianza !== null && (
          <span className="pb-2 text-xs text-tenue">
            Confianza del clasificador: {Math.round(incidencia.confianza * 100)} %
          </span>
        )}
      </div>

      {error && (
        <p role="alert" className="mt-2 text-sm text-red-700">
          {error}
        </p>
      )}
    </li>
  );
}

export default function Incidencias() {
  const [filtros, setFiltros] = useState({ prioridad: "", estatus_revision: "" });
  const cambiar = (campo) => (e) => setFiltros({ ...filtros, [campo]: e.target.value });

  const usuarios = useDatos(() => api.usuarios(true));
  const incidencias = useDatos(() => api.incidencias(filtros), [filtros]);

  const trabajador = (id) =>
    usuarios.datos?.find((u) => u.id === id)?.nombre ?? `Usuario ${id}`;
  const porRevisar =
    incidencias.datos?.filter((i) => i.estatus_revision !== "Revisada").length ?? 0;

  return (
    <>
      <Encabezado
        titulo="Incidencias"
        descripcion="El sistema propone la categoría y la prioridad de cada mensaje. Aquí se confirman o se corrigen."
      >
        <Campo etiqueta="Prioridad">
          <Selector value={filtros.prioridad} onChange={cambiar("prioridad")}>
            <option value="">Todas</option>
            {PRIORIDADES.map((p) => (
              <option key={p}>{p}</option>
            ))}
          </Selector>
        </Campo>
        <Campo etiqueta="Revisión">
          <Selector value={filtros.estatus_revision} onChange={cambiar("estatus_revision")}>
            <option value="">Todas</option>
            {ESTATUS.map((e) => (
              <option key={e}>{e}</option>
            ))}
          </Selector>
        </Campo>
      </Encabezado>

      <Estado
        error={usuarios.error ?? incidencias.error}
        cargando={incidencias.cargando}
        hayDatos={incidencias.datos}
      >
        {incidencias.datos?.length === 0 && (
          <Aviso>No hay incidencias con esos filtros.</Aviso>
        )}
        {incidencias.datos?.length > 0 && (
          <Panel
            titulo={`${incidencias.datos.length} incidencia${incidencias.datos.length === 1 ? "" : "s"}`}
            accion={
              <span className="text-xs text-tenue">
                {porRevisar === 0 ? "Todas revisadas" : `${porRevisar} por revisar`}
              </span>
            }
          >
            <ul className="divide-y divide-linea">
              {incidencias.datos.map((incidencia) => (
                <Incidencia
                  // Al guardar cambia el estatus; la clave obliga a repintar la fila.
                  key={`${incidencia.id}-${incidencia.estatus_revision}-${incidencia.categoria}-${incidencia.prioridad}`}
                  incidencia={incidencia}
                  trabajador={trabajador(incidencia.usuario_id)}
                  alRevisar={incidencias.recargar}
                />
              ))}
            </ul>
          </Panel>
        )}
      </Estado>
    </>
  );
}
