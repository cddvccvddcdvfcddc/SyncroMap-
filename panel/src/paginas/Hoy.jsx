import { useState } from "react";

import { api } from "../api.js";
import {
  Campo,
  Celda,
  Encabezado,
  Estado,
  Etiqueta,
  Panel,
  Selector,
  Tabla,
  TONO_DE_PRIORIDAD,
  tonoDeEstatus,
} from "../componentes/interfaz.jsx";
import { diaLegible, diaLocal, hora, horaActual } from "../fechas.js";
import { useDatos } from "../useDatos.js";

const ORDEN_DE_ESTADO = { "Sin entrada": 0, Retardo: 1, "A tiempo": 2 };
const ORDEN_DE_PRIORIDAD = { Alta: 0, Media: 1, Baja: 2 };

async function cargarElDia() {
  const hoy = diaLocal();
  const [obras, usuarios, asistencias, incidencias] = await Promise.all([
    api.obras(),
    api.usuarios(),
    api.asistencias({ desde: hoy, hasta: hoy }),
    api.incidencias({ desde: hoy, hasta: hoy }),
  ]);
  return { hoy, obras, usuarios, asistencias, incidencias, actualizado: horaActual() };
}

// Junta a cada trabajador con sus fichajes de hoy.
function estadoDelPersonal(usuarios, asistencias) {
  return usuarios.map((usuario) => {
    const suyos = asistencias.filter((fichaje) => fichaje.usuario_id === usuario.id);
    const validos = suyos.filter((f) => f.estatus_asistencia !== "Fuera de rango");
    const entrada = validos.find((f) => f.tipo === "entrada");
    const salida = validos.find((f) => f.tipo === "salida");

    let estado = "Sin entrada";
    if (entrada) estado = entrada.estatus_asistencia === "Retardo" ? "Retardo" : "A tiempo";

    return {
      usuario,
      estado,
      entrada,
      salida,
      intentosFuera: suyos.length - validos.length,
    };
  });
}

function Cifra({ titulo, valor, nota, tono = "text-tinta" }) {
  return (
    <div className="rounded-lg bg-white px-4 py-3 ring-1 ring-linea">
      <p className="text-xs font-medium text-tenue">{titulo}</p>
      <p className={`mt-1 text-3xl font-semibold tabular-nums ${tono}`}>{valor}</p>
      {nota && <p className="mt-0.5 text-xs text-tenue">{nota}</p>}
    </div>
  );
}

export default function Hoy() {
  const [obraId, setObraId] = useState("");
  // Se actualiza solo cada 30 segundos para ver los fichajes conforme llegan.
  const { datos, error, cargando } = useDatos(cargarElDia, [], { cadaSegundos: 30 });

  const enLaObra = (registro) => obraId === "" || registro.obra_id === Number(obraId);
  const usuarios = datos?.usuarios.filter((u) => u.obra_id !== null && enLaObra(u)) ?? [];
  const idsDelPersonal = new Set(usuarios.map((u) => u.id));

  const personal = estadoDelPersonal(usuarios, datos?.asistencias ?? []).sort(
    (a, b) =>
      ORDEN_DE_ESTADO[a.estado] - ORDEN_DE_ESTADO[b.estado] ||
      a.usuario.nombre.localeCompare(b.usuario.nombre),
  );
  const incidencias = (datos?.incidencias ?? [])
    .filter((incidencia) => idsDelPersonal.has(incidencia.usuario_id))
    .sort((a, b) => ORDEN_DE_PRIORIDAD[a.prioridad] - ORDEN_DE_PRIORIDAD[b.prioridad]);

  const cuenta = (estado) => personal.filter((p) => p.estado === estado).length;
  const altas = incidencias.filter((i) => i.prioridad === "Alta").length;
  const nombreDe = (id) => usuarios.find((u) => u.id === id)?.nombre ?? `Usuario ${id}`;
  const obraDe = (id) => datos.obras.find((o) => o.id === id)?.nombre ?? "—";

  return (
    <>
      <Encabezado
        titulo="Hoy"
        descripcion={
          datos && `${diaLegible(datos.hoy)} · actualizado a las ${datos.actualizado}`
        }
      >
        <Campo etiqueta="Obra">
          <Selector value={obraId} onChange={(e) => setObraId(e.target.value)}>
            <option value="">Todas las obras</option>
            {datos?.obras.map((obra) => (
              <option key={obra.id} value={obra.id}>
                {obra.nombre}
              </option>
            ))}
          </Selector>
        </Campo>
      </Encabezado>

      <Estado error={error} cargando={cargando} hayDatos={datos}>
        {datos && (
          <div className="space-y-6">
            <div className="grid grid-cols-2 gap-3 lg:grid-cols-5">
              <Cifra titulo="Personal" valor={personal.length} />
              <Cifra titulo="A tiempo" valor={cuenta("A tiempo")} tono="text-emerald-700" />
              <Cifra titulo="Con retardo" valor={cuenta("Retardo")} tono="text-amber-700" />
              <Cifra titulo="Sin entrada" valor={cuenta("Sin entrada")} tono="text-red-700" />
              <Cifra
                titulo="Incidencias"
                valor={incidencias.length}
                nota={altas > 0 ? `${altas} de prioridad alta` : "Ninguna de prioridad alta"}
              />
            </div>

            <div className="grid gap-6 xl:grid-cols-5">
              <Panel titulo="Personal" className="xl:col-span-3">
                <Tabla
                  columnas={["Trabajador", "Obra", "Estado", "Entrada", "Salida"]}
                  vacio="No hay personal asignado a esta obra."
                >
                  {personal.map(({ usuario, estado, entrada, salida, intentosFuera }) => (
                    <tr key={usuario.id}>
                      <Celda className="font-medium">
                        {usuario.nombre}
                        {usuario.rol === "supervisor" && (
                          <span className="ml-2 text-xs font-normal text-tenue">supervisor</span>
                        )}
                      </Celda>
                      <Celda className="whitespace-nowrap text-tenue">
                        {obraDe(usuario.obra_id)}
                      </Celda>
                      <Celda className="whitespace-nowrap">
                        <Etiqueta tono={estado === "Sin entrada" ? "rojo" : tonoDeEstatus(estado)}>
                          {estado}
                        </Etiqueta>
                        {intentosFuera > 0 && (
                          <span className="mt-1 block text-xs text-tenue">
                            {intentosFuera} intento{intentosFuera > 1 ? "s" : ""} fuera de rango
                          </span>
                        )}
                      </Celda>
                      <Celda className="tabular-nums">
                        {entrada ? hora(entrada.fecha_hora_fichaje) : "—"}
                      </Celda>
                      <Celda className="tabular-nums">
                        {salida ? hora(salida.fecha_hora_fichaje) : "—"}
                      </Celda>
                    </tr>
                  ))}
                </Tabla>
              </Panel>

              <Panel
                titulo="Incidencias de hoy"
                className="xl:col-span-2"
                accion={
                  <a href="#/incidencias" className="text-xs font-medium text-marca-700 hover:underline">
                    Ver todas
                  </a>
                }
              >
                {incidencias.length === 0 ? (
                  <p className="px-4 py-6 text-center text-sm text-tenue">
                    Nadie ha reportado incidencias hoy.
                  </p>
                ) : (
                  <ul className="divide-y divide-linea">
                    {incidencias.map((incidencia) => (
                      <li key={incidencia.id} className="px-4 py-3">
                        <div className="flex items-center justify-between gap-2">
                          <span className="text-sm font-medium">
                            {nombreDe(incidencia.usuario_id)}
                          </span>
                          <Etiqueta tono={TONO_DE_PRIORIDAD[incidencia.prioridad]}>
                            {incidencia.prioridad ?? "Sin prioridad"}
                          </Etiqueta>
                        </div>
                        <p className="mt-1 text-sm text-tenue">
                          <span className="text-tinta">{incidencia.categoria}:</span>{" "}
                          {incidencia.motivo_texto}
                        </p>
                      </li>
                    ))}
                  </ul>
                )}
              </Panel>
            </div>
          </div>
        )}
      </Estado>
    </>
  );
}
