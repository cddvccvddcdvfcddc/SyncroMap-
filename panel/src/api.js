// Todas las llamadas del panel al servidor de SyncroMap (FastAPI).

import { cerrarSesion, leerSesion } from "./sesion.js";

const URL_API = import.meta.env.VITE_API_URL ?? "http://127.0.0.1:8000";

function mensajeDeError(datos, estado) {
  const detalle = datos?.detail;
  if (typeof detalle === "string") return detalle;
  // Los errores de validación de FastAPI llegan como una lista.
  if (Array.isArray(detalle)) {
    return detalle
      .map((error) => `${error.loc?.at(-1) ?? "dato"}: ${error.msg}`)
      .join(". ");
  }
  return `El servidor respondió con un error (${estado}).`;
}

async function pedir(ruta, { metodo = "GET", cuerpo, filtros } = {}) {
  const url = new URL(URL_API + ruta);
  for (const [clave, valor] of Object.entries(filtros ?? {})) {
    if (valor !== "" && valor !== null && valor !== undefined) {
      url.searchParams.set(clave, valor);
    }
  }

  const cabeceras = {};
  if (cuerpo) cabeceras["Content-Type"] = "application/json";
  // El token de la sesión acompaña a cada petición.
  const token = leerSesion()?.token;
  if (token) cabeceras.Authorization = `Bearer ${token}`;

  let respuesta;
  try {
    respuesta = await fetch(url, {
      method: metodo,
      headers: cabeceras,
      body: cuerpo ? JSON.stringify(cuerpo) : undefined,
    });
  } catch {
    throw new Error(
      "No se pudo conectar con el servidor de SyncroMap. Revisa que esté encendido.",
    );
  }

  if (respuesta.status === 204) return null;
  const datos = await respuesta.json().catch(() => null);
  // La sesión venció o ya no es válida: se regresa a la pantalla de entrada.
  if (respuesta.status === 401 && token) cerrarSesion();
  if (!respuesta.ok) throw new Error(mensajeDeError(datos, respuesta.status));
  return datos;
}

export const api = {
  entrar: (credenciales) => pedir("/acceso/", { metodo: "POST", cuerpo: credenciales }),

  obras: (incluirInactivos = false) =>
    pedir("/obras/", { filtros: { incluir_inactivos: incluirInactivos } }),
  crearObra: (obra) => pedir("/obras/", { metodo: "POST", cuerpo: obra }),
  actualizarObra: (id, obra) => pedir(`/obras/${id}`, { metodo: "PUT", cuerpo: obra }),
  darDeBajaObra: (id) => pedir(`/obras/${id}`, { metodo: "DELETE" }),

  usuarios: (incluirInactivos = false) =>
    pedir("/usuarios/", { filtros: { incluir_inactivos: incluirInactivos } }),
  crearUsuario: (usuario) => pedir("/usuarios/", { metodo: "POST", cuerpo: usuario }),
  actualizarUsuario: (id, usuario) =>
    pedir(`/usuarios/${id}`, { metodo: "PUT", cuerpo: usuario }),
  darDeBajaUsuario: (id) => pedir(`/usuarios/${id}`, { metodo: "DELETE" }),

  // Filtros: desde, hasta (días en formato AAAA-MM-DD), obra_id, usuario_id
  asistencias: (filtros) => pedir("/asistencia/", { filtros }),
  faltas: (filtros) => pedir("/asistencia/faltas", { filtros }),

  // Filtros: prioridad, estatus_revision, usuario_id, desde, hasta
  incidencias: (filtros) => pedir("/incidencias/", { filtros }),
  revisarIncidencia: (id, cambios) =>
    pedir(`/incidencias/${id}/revision`, { metodo: "PUT", cuerpo: cambios }),
};
