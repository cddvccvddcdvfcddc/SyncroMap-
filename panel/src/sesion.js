// La sesión abierta (token y datos del administrador) se guarda en el navegador
// para no pedir la contraseña cada vez que se recarga la página.

const CLAVE = "syncromap_sesion";
const oyentes = new Set();

export function leerSesion() {
  try {
    const sesion = JSON.parse(localStorage.getItem(CLAVE));
    return sesion?.token ? sesion : null;
  } catch {
    return null;
  }
}

function avisar() {
  const sesion = leerSesion();
  oyentes.forEach((oyente) => oyente(sesion));
}

export function guardarSesion(sesion) {
  localStorage.setItem(CLAVE, JSON.stringify(sesion));
  avisar();
}

export function cerrarSesion() {
  localStorage.removeItem(CLAVE);
  avisar();
}

// Avisa cuando se entra o se sale; devuelve la función para dejar de escuchar.
export function alCambiarSesion(oyente) {
  oyentes.add(oyente);
  return () => oyentes.delete(oyente);
}
