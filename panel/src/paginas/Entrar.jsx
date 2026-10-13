import { useState } from "react";

import { api } from "../api.js";
import { Aviso, Boton, Campo, Entrada } from "../componentes/interfaz.jsx";
import { guardarSesion } from "../sesion.js";

export default function Entrar() {
  const [datos, setDatos] = useState({ usuario: "", contrasena: "" });
  const [error, setError] = useState(null);
  const [enviando, setEnviando] = useState(false);
  const cambiar = (campo) => (e) => setDatos({ ...datos, [campo]: e.target.value });

  async function enviar(evento) {
    evento.preventDefault();
    setEnviando(true);
    setError(null);
    try {
      guardarSesion(await api.entrar(datos));
    } catch (fallo) {
      setError(fallo.message);
      setEnviando(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="mb-6 text-center">
          <h1 className="text-2xl font-semibold tracking-tight text-marca-900">SyncroMap</h1>
          <p className="mt-1 text-sm text-tenue">MONTAJES IIMYRSA · Panel de asistencia</p>
        </div>

        <form onSubmit={enviar} className="space-y-4 rounded-lg bg-white p-6 ring-1 ring-linea">
          <Campo etiqueta="Usuario">
            <Entrada
              required
              autoFocus
              maxLength={50}
              autoComplete="username"
              autoCapitalize="none"
              value={datos.usuario}
              onChange={cambiar("usuario")}
            />
          </Campo>
          <Campo etiqueta="Contraseña">
            <Entrada
              required
              type="password"
              maxLength={200}
              autoComplete="current-password"
              value={datos.contrasena}
              onChange={cambiar("contrasena")}
            />
          </Campo>

          {error && <Aviso tipo="error">{error}</Aviso>}

          <Boton type="submit" estilo="principal" className="w-full" disabled={enviando}>
            {enviando ? "Entrando…" : "Entrar"}
          </Boton>
        </form>
      </div>
    </main>
  );
}
