import { useState } from "react";

import { api } from "../api.js";
import {
  Aviso,
  Boton,
  Campo,
  Celda,
  Encabezado,
  Entrada,
  Estado,
  Panel,
  Selector,
  Tabla,
} from "../componentes/interfaz.jsx";
import { diaLocal, primerDiaDelMes } from "../fechas.js";
import { useDatos } from "../useDatos.js";

const ARCHIVOS = [
  { formato: "excel", nombre: "Excel para nóminas", extension: "xlsx" },
  { formato: "pdf", nombre: "PDF ejecutivo", extension: "pdf" },
];

const numero = (valor) => valor.toLocaleString("es-MX", { maximumFractionDigits: 2 });

export default function Reportes() {
  const [filtros, setFiltros] = useState({
    desde: primerDiaDelMes(),
    hasta: diaLocal(),
    obra_id: "",
  });
  const [descargando, setDescargando] = useState(null);
  const [errorDeDescarga, setErrorDeDescarga] = useState(null);
  const cambiar = (campo) => (e) => setFiltros({ ...filtros, [campo]: e.target.value });

  const obras = useDatos(() => api.obras(true));
  const reporte = useDatos(() => api.resumenDelReporte(filtros), [filtros]);
  const datos = reporte.datos;

  async function descargar({ formato, extension }) {
    setDescargando(formato);
    setErrorDeDescarga(null);
    try {
      await api.descargarReporte(
        formato,
        filtros,
        `reporte_asistencia_${filtros.desde}_a_${filtros.hasta}.${extension}`,
      );
    } catch (fallo) {
      setErrorDeDescarga(fallo.message);
    } finally {
      setDescargando(null);
    }
  }

  return (
    <>
      <Encabezado
        titulo="Reportes"
        descripcion="Resumen del periodo por trabajador, descargable en Excel o PDF."
      >
        {ARCHIVOS.map((archivo) => (
          <Boton
            key={archivo.formato}
            estilo={archivo.formato === "excel" ? "principal" : "secundario"}
            disabled={!datos || descargando !== null}
            onClick={() => descargar(archivo)}
          >
            {descargando === archivo.formato ? "Generando…" : `Descargar ${archivo.nombre}`}
          </Boton>
        ))}
      </Encabezado>

      <Panel className="mb-6 p-4">
        <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
          <Campo etiqueta="Desde">
            <Entrada type="date" required value={filtros.desde} max={filtros.hasta} onChange={cambiar("desde")} />
          </Campo>
          <Campo etiqueta="Hasta">
            <Entrada type="date" required value={filtros.hasta} min={filtros.desde} onChange={cambiar("hasta")} />
          </Campo>
          <Campo etiqueta="Obra">
            <Selector value={filtros.obra_id} onChange={cambiar("obra_id")}>
              <option value="">Todas</option>
              {obras.datos?.map((obra) => (
                <option key={obra.id} value={obra.id}>
                  {obra.nombre}
                </option>
              ))}
            </Selector>
          </Campo>
        </div>
      </Panel>

      {errorDeDescarga && (
        <div className="mb-4">
          <Aviso tipo="error">{errorDeDescarga}</Aviso>
        </div>
      )}

      <Estado error={reporte.error} cargando={reporte.cargando} hayDatos={datos}>
        {datos && (
          <Panel titulo={`Resumen por trabajador · ${datos.obra}`}>
            <Tabla
              columnas={[
                "Trabajador",
                "Obra",
                "Asistencias",
                "Retardos",
                "Faltas",
                "Horas",
                "Días sin salida",
                "Incidencias",
              ]}
              vacio="No hay personal ni registros en ese periodo."
            >
              {datos.resumen.map((fila) => (
                <tr key={fila.usuario_id}>
                  <Celda className="font-medium">{fila.trabajador}</Celda>
                  <Celda className="text-tenue">{fila.obra}</Celda>
                  <Celda className="tabular-nums">{fila.asistencias}</Celda>
                  <Celda className="tabular-nums">{fila.retardos}</Celda>
                  <Celda className="tabular-nums">{fila.faltas}</Celda>
                  <Celda className="tabular-nums">{numero(fila.horas)}</Celda>
                  <Celda className="tabular-nums">{fila.sin_salida}</Celda>
                  <Celda className="tabular-nums">{fila.incidencias}</Celda>
                </tr>
              ))}
              {datos.resumen.length > 0 && (
                <tr className="font-semibold">
                  <Celda>Total</Celda>
                  <Celda />
                  <Celda className="tabular-nums">{datos.totales.asistencias}</Celda>
                  <Celda className="tabular-nums">{datos.totales.retardos}</Celda>
                  <Celda className="tabular-nums">{datos.totales.faltas}</Celda>
                  <Celda className="tabular-nums">{numero(datos.totales.horas)}</Celda>
                  <Celda className="tabular-nums">{datos.totales.sin_salida}</Celda>
                  <Celda className="tabular-nums">{datos.totales.incidencias}</Celda>
                </tr>
              )}
            </Tabla>
            <p className="border-t border-linea px-4 py-3 text-xs text-tenue">
              Las horas se cuentan solo en los días con entrada y salida registradas. El Excel
              incluye además el detalle día por día, las faltas y las incidencias.
            </p>
          </Panel>
        )}
      </Estado>
    </>
  );
}
