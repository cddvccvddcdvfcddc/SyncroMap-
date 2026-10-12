import { useEffect, useState } from "react";

import Asistencias from "./paginas/Asistencias.jsx";
import Hoy from "./paginas/Hoy.jsx";
import Incidencias from "./paginas/Incidencias.jsx";
import Mapa from "./paginas/Mapa.jsx";
import Obras from "./paginas/Obras.jsx";
import Personal from "./paginas/Personal.jsx";

const PAGINAS = [
  { ruta: "hoy", nombre: "Hoy", componente: Hoy },
  { ruta: "mapa", nombre: "Mapa", componente: Mapa },
  { ruta: "asistencias", nombre: "Asistencias", componente: Asistencias },
  { ruta: "incidencias", nombre: "Incidencias", componente: Incidencias },
  { ruta: "personal", nombre: "Personal", componente: Personal },
  { ruta: "obras", nombre: "Obras", componente: Obras },
];

function rutaActual() {
  const ruta = window.location.hash.replace("#/", "");
  return PAGINAS.some((pagina) => pagina.ruta === ruta) ? ruta : "hoy";
}

export default function App() {
  // La página abierta se guarda en la dirección (#/mapa) para poder recargar o compartirla.
  const [ruta, setRuta] = useState(rutaActual);

  useEffect(() => {
    const alCambiar = () => setRuta(rutaActual());
    window.addEventListener("hashchange", alCambiar);
    return () => window.removeEventListener("hashchange", alCambiar);
  }, []);

  const Pagina = PAGINAS.find((pagina) => pagina.ruta === ruta).componente;

  return (
    <div className="min-h-screen md:flex">
      <aside className="bg-marca-900 text-white md:fixed md:inset-y-0 md:w-52">
        <div className="px-5 pt-5 pb-3 md:pb-6">
          <p className="text-lg font-semibold tracking-tight">SyncroMap</p>
          <p className="text-xs text-white/60">MONTAJES IIMYRSA</p>
        </div>
        <nav aria-label="Secciones" className="flex gap-1 overflow-x-auto px-3 pb-3 md:block md:space-y-1">
          {PAGINAS.map((pagina) => (
            <a
              key={pagina.ruta}
              href={`#/${pagina.ruta}`}
              aria-current={pagina.ruta === ruta ? "page" : undefined}
              className={`block rounded-md px-3 py-2 text-sm whitespace-nowrap transition-colors ${
                pagina.ruta === ruta
                  ? "bg-white/15 font-medium text-white"
                  : "text-white/70 hover:bg-white/10 hover:text-white"
              }`}
            >
              {pagina.nombre}
            </a>
          ))}
        </nav>
      </aside>

      <main className="min-w-0 flex-1 px-4 py-6 md:ml-52 md:px-8">
        <div className="mx-auto max-w-6xl">
          <Pagina />
        </div>
      </main>
    </div>
  );
}
