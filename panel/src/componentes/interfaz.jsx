// Piezas pequeñas que comparten todas las pantallas del panel.

import { useEffect, useRef, useState } from "react";

const TONOS = {
  verde: "bg-emerald-50 text-emerald-800 ring-emerald-600/20",
  ambar: "bg-amber-50 text-amber-800 ring-amber-600/25",
  rojo: "bg-red-50 text-red-700 ring-red-600/20",
  gris: "bg-slate-100 text-slate-600 ring-slate-500/15",
  marca: "bg-marca-50 text-marca-700 ring-marca-600/20",
};

export function Etiqueta({ tono = "gris", children }) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium whitespace-nowrap ring-1 ring-inset ${TONOS[tono]}`}
    >
      {children}
    </span>
  );
}

// Color de cada estatus de asistencia.
export function tonoDeEstatus(estatus) {
  if (estatus === "A tiempo" || estatus === "Dentro de rango") return "verde";
  if (estatus === "Retardo") return "ambar";
  if (estatus === "Fuera de rango" || estatus === "Falta") return "rojo";
  return "gris";
}

export const TONO_DE_PRIORIDAD = { Alta: "rojo", Media: "ambar", Baja: "gris" };

export const TONO_DE_REVISION = { Pendiente: "gris", Ambigua: "ambar", Revisada: "verde" };

const ESTILOS_DE_BOTON = {
  principal: "bg-marca-600 text-white hover:bg-marca-700 disabled:bg-slate-300",
  secundario:
    "bg-white text-tinta ring-1 ring-inset ring-linea hover:bg-slate-50 disabled:text-slate-400",
  peligro: "bg-white text-red-700 ring-1 ring-inset ring-red-200 hover:bg-red-50",
};

export function Boton({ estilo = "secundario", className = "", ...props }) {
  return (
    <button
      type="button"
      className={`inline-flex items-center justify-center rounded-md px-3 py-1.5 text-sm font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-marca-600 disabled:cursor-not-allowed ${ESTILOS_DE_BOTON[estilo]} ${className}`}
      {...props}
    />
  );
}

const ESTILO_DE_CONTROL =
  "block w-full rounded-md border-0 bg-white px-2.5 py-1.5 text-sm text-tinta ring-1 ring-inset ring-linea focus:ring-2 focus:ring-marca-600 focus:outline-none";

export function Campo({ etiqueta, ayuda, children }) {
  return (
    <label className="block">
      <span className="mb-1 block text-xs font-medium text-tenue">{etiqueta}</span>
      {children}
      {ayuda && <span className="mt-1 block text-xs text-tenue">{ayuda}</span>}
    </label>
  );
}

export function Entrada(props) {
  return <input className={ESTILO_DE_CONTROL} {...props} />;
}

export function Selector({ children, ...props }) {
  return (
    <select className={ESTILO_DE_CONTROL} {...props}>
      {children}
    </select>
  );
}

export function Encabezado({ titulo, descripcion, children }) {
  return (
    <header className="mb-6 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-xl font-semibold tracking-tight">{titulo}</h1>
        {descripcion && <p className="mt-1 text-sm text-tenue">{descripcion}</p>}
      </div>
      {children && <div className="flex flex-wrap items-end gap-2">{children}</div>}
    </header>
  );
}

export function Panel({ titulo, accion, children, className = "" }) {
  return (
    <section className={`rounded-lg bg-white ring-1 ring-linea ${className}`}>
      {titulo && (
        <div className="flex items-center justify-between gap-3 border-b border-linea px-4 py-3">
          <h2 className="text-sm font-semibold">{titulo}</h2>
          {accion}
        </div>
      )}
      {children}
    </section>
  );
}

export function Aviso({ tipo = "info", children }) {
  const estilo =
    tipo === "error"
      ? "bg-red-50 text-red-800 ring-red-200"
      : "bg-white text-tenue ring-linea";
  return (
    <p role={tipo === "error" ? "alert" : undefined} className={`rounded-lg px-4 py-3 text-sm ring-1 ${estilo}`}>
      {children}
    </p>
  );
}

// Muestra el error o el aviso de carga; si ya hay datos, pinta el contenido.
export function Estado({ error, cargando, hayDatos, children }) {
  if (error) return <Aviso tipo="error">{error}</Aviso>;
  if (cargando && !hayDatos) return <Aviso>Cargando…</Aviso>;
  return children;
}

export function Tabla({ columnas, children, vacio = "No hay registros." }) {
  const filas = Array.isArray(children) ? children.flat().filter(Boolean) : children;
  const sinFilas = Array.isArray(filas) && filas.length === 0;
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="border-b border-linea text-xs text-tenue">
            {columnas.map((columna) => (
              <th key={columna} scope="col" className="px-4 py-2 font-medium whitespace-nowrap">
                {columna}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-linea">
          {sinFilas ? (
            <tr>
              <td colSpan={columnas.length} className="px-4 py-6 text-center text-tenue">
                {vacio}
              </td>
            </tr>
          ) : (
            filas
          )}
        </tbody>
      </table>
    </div>
  );
}

export function Celda({ className = "", ...props }) {
  return <td className={`px-4 py-2.5 align-middle ${className}`} {...props} />;
}

// Ventana emergente para los formularios.
export function Ventana({ titulo, alCerrar, children }) {
  const dialogo = useRef(null);
  // El contenido se pinta con la ventana ya abierta: un mapa necesita medir su espacio.
  const [abierta, setAbierta] = useState(false);

  useEffect(() => {
    dialogo.current?.showModal();
    setAbierta(true);
  }, []);

  return (
    <dialog
      ref={dialogo}
      onClose={alCerrar}
      className="m-auto w-full max-w-lg rounded-xl bg-white p-0 text-tinta shadow-xl"
    >
      <div className="flex items-center justify-between border-b border-linea px-5 py-3">
        <h2 className="text-base font-semibold">{titulo}</h2>
        <button
          type="button"
          onClick={alCerrar}
          aria-label="Cerrar"
          className="rounded-md px-2 py-1 text-tenue hover:bg-slate-100"
        >
          ✕
        </button>
      </div>
      <div className="px-5 py-4">{abierta && children}</div>
    </dialog>
  );
}
