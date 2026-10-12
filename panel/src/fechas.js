// El servidor guarda las fechas en UTC; el panel siempre las muestra en hora de México.

const ZONA = "America/Mexico_City";

// "2026-10-11T03:08:13" llega sin zona, pero es UTC.
function aFecha(textoUtc) {
  return new Date(textoUtc.endsWith("Z") ? textoUtc : textoUtc + "Z");
}

// Día de México en formato AAAA-MM-DD, el que usan los filtros del servidor.
export function diaLocal(fecha = new Date()) {
  return new Intl.DateTimeFormat("en-CA", { timeZone: ZONA }).format(fecha);
}

export function diaDe(textoUtc) {
  return diaLocal(aFecha(textoUtc));
}

export function primerDiaDelMes() {
  return diaLocal().slice(0, 8) + "01";
}

export function hora(textoUtc) {
  return new Intl.DateTimeFormat("es-MX", {
    timeZone: ZONA,
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(aFecha(textoUtc));
}

// Recibe un día AAAA-MM-DD y devuelve, por ejemplo, "sáb 10 oct 2026".
export function diaLegible(dia) {
  const [anio, mes, numero] = dia.split("-").map(Number);
  return new Intl.DateTimeFormat("es-MX", {
    timeZone: "UTC",
    weekday: "short",
    day: "numeric",
    month: "short",
    year: "numeric",
  })
    .format(new Date(Date.UTC(anio, mes - 1, numero)))
    .replaceAll(".", "")
    .replaceAll(",", "");
}

export function horaActual() {
  return new Intl.DateTimeFormat("es-MX", {
    timeZone: ZONA,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).format(new Date());
}
