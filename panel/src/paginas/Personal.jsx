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
  Etiqueta,
  Panel,
  Selector,
  Tabla,
  Ventana,
} from "../componentes/interfaz.jsx";
import { useDatos } from "../useDatos.js";

const NUEVO = { nombre: "", telefono: "", rol: "operativo", obra_id: "", activo: true };

function Formulario({ usuario, obras, alGuardar, alCerrar }) {
  const [datos, setDatos] = useState({ ...usuario, obra_id: usuario.obra_id ?? "" });
  const [guardando, setGuardando] = useState(false);
  const [error, setError] = useState(null);
  const cambiar = (campo) => (e) => setDatos({ ...datos, [campo]: e.target.value });

  async function enviar(evento) {
    evento.preventDefault();
    setGuardando(true);
    setError(null);
    const cuerpo = {
      nombre: datos.nombre.trim(),
      telefono: datos.telefono.trim(),
      rol: datos.rol,
      obra_id: datos.obra_id === "" ? null : Number(datos.obra_id),
      activo: datos.activo,
    };
    try {
      if (usuario.id) await api.actualizarUsuario(usuario.id, cuerpo);
      else await api.crearUsuario(cuerpo);
      await alGuardar();
    } catch (fallo) {
      setError(fallo.message);
      setGuardando(false);
    }
  }

  return (
    <Ventana titulo={usuario.id ? "Editar trabajador" : "Nuevo trabajador"} alCerrar={alCerrar}>
      <form onSubmit={enviar} className="space-y-4">
        <Campo etiqueta="Nombre">
          <Entrada required maxLength={100} value={datos.nombre} onChange={cambiar("nombre")} />
        </Campo>
        <Campo
          etiqueta="Teléfono de WhatsApp"
          ayuda="Como lo envía WhatsApp: 521 y los 10 dígitos, sin espacios. Ejemplo: 5215512345678."
        >
          <Entrada
            required
            maxLength={20}
            value={datos.telefono}
            onChange={cambiar("telefono")}
          />
        </Campo>
        <div className="grid grid-cols-2 gap-3">
          <Campo etiqueta="Rol" ayuda="El supervisor recibe el reporte matutino.">
            <Selector value={datos.rol ?? "operativo"} onChange={cambiar("rol")}>
              <option value="operativo">Operativo</option>
              <option value="supervisor">Supervisor</option>
            </Selector>
          </Campo>
          <Campo etiqueta="Obra asignada">
            <Selector value={datos.obra_id} onChange={cambiar("obra_id")}>
              <option value="">Sin obra</option>
              {obras.map((obra) => (
                <option key={obra.id} value={obra.id}>
                  {obra.nombre}
                </option>
              ))}
            </Selector>
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

export default function Personal() {
  const [verInactivos, setVerInactivos] = useState(false);
  const [enEdicion, setEnEdicion] = useState(null);
  const [error, setError] = useState(null);

  const { datos, error: errorDeCarga, cargando, recargar } = useDatos(
    async () => {
      const [usuarios, obras] = await Promise.all([api.usuarios(verInactivos), api.obras()]);
      return { usuarios, obras };
    },
    [verInactivos],
  );

  const obraDe = (id) => datos.obras.find((o) => o.id === id)?.nombre;

  async function cambiarActivo(usuario, activo) {
    setError(null);
    try {
      if (activo) {
        const { id, creado_en, ...resto } = usuario;
        await api.actualizarUsuario(id, { ...resto, activo: true });
      } else {
        if (!window.confirm(`¿Dar de baja a ${usuario.nombre}? Su historial se conserva.`)) return;
        await api.darDeBajaUsuario(usuario.id);
      }
      await recargar();
    } catch (fallo) {
      setError(fallo.message);
    }
  }

  return (
    <>
      <Encabezado
        titulo="Personal"
        descripcion="Solo los números registrados y activos pueden usar el bot de WhatsApp."
      >
        <label className="flex items-center gap-2 pb-1.5 text-sm text-tenue">
          <input
            type="checkbox"
            className="size-4 accent-marca-600"
            checked={verInactivos}
            onChange={(e) => setVerInactivos(e.target.checked)}
          />
          Ver dados de baja
        </label>
        <Boton estilo="principal" onClick={() => setEnEdicion(NUEVO)}>
          Nuevo trabajador
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
              columnas={["Nombre", "Teléfono", "Rol", "Obra", "Estado", ""]}
              vacio="Todavía no hay trabajadores registrados."
            >
              {datos.usuarios
                .toSorted((a, b) => a.nombre.localeCompare(b.nombre))
                .map((usuario) => (
                  <tr key={usuario.id} className={usuario.activo ? "" : "text-tenue"}>
                    <Celda className="font-medium">{usuario.nombre}</Celda>
                    <Celda className="tabular-nums">{usuario.telefono}</Celda>
                    <Celda className="capitalize">{usuario.rol ?? "operativo"}</Celda>
                    <Celda>
                      {obraDe(usuario.obra_id) ?? <span className="text-tenue">Sin obra</span>}
                    </Celda>
                    <Celda>
                      <Etiqueta tono={usuario.activo ? "verde" : "gris"}>
                        {usuario.activo ? "Activo" : "De baja"}
                      </Etiqueta>
                    </Celda>
                    <Celda className="text-right whitespace-nowrap">
                      {usuario.activo ? (
                        <span className="inline-flex gap-2">
                          <Boton onClick={() => setEnEdicion(usuario)}>Editar</Boton>
                          <Boton estilo="peligro" onClick={() => cambiarActivo(usuario, false)}>
                            Dar de baja
                          </Boton>
                        </span>
                      ) : (
                        <Boton onClick={() => cambiarActivo(usuario, true)}>Reactivar</Boton>
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
          usuario={enEdicion}
          obras={datos?.obras ?? []}
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
