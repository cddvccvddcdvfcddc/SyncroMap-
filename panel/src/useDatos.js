import { useCallback, useEffect, useRef, useState } from "react";

// Carga datos del servidor y los vuelve a pedir cuando cambian las dependencias.
// Con `cadaSegundos` se actualizan solos, para ver los fichajes conforme llegan.
export function useDatos(cargar, dependencias = [], { cadaSegundos } = {}) {
  const [datos, setDatos] = useState(null);
  const [error, setError] = useState(null);
  const [cargando, setCargando] = useState(true);
  const peticion = useRef(0);

  const recargar = useCallback(async () => {
    // Si llegan dos respuestas desordenadas, solo cuenta la de la última petición.
    const numero = ++peticion.current;
    try {
      const resultado = await cargar();
      if (numero !== peticion.current) return;
      setDatos(resultado);
      setError(null);
    } catch (fallo) {
      if (numero !== peticion.current) return;
      setError(fallo.message);
    } finally {
      if (numero === peticion.current) setCargando(false);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, dependencias);

  useEffect(() => {
    // Al cambiar los filtros se descartan los datos anteriores: ya no corresponden.
    setDatos(null);
    setCargando(true);
    recargar();
    if (!cadaSegundos) return;
    const reloj = setInterval(recargar, cadaSegundos * 1000);
    return () => clearInterval(reloj);
  }, [recargar, cadaSegundos]);

  return { datos, error, cargando, recargar };
}
