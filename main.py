from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import acceso, obras, usuarios, asistencia, incidencias, whatsapp
from tareas import iniciar_planificador

# Las tablas se crean y modifican con Alembic: py -m alembic upgrade head


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    # Las tareas programadas viven mientras el servidor esté encendido.
    planificador = iniciar_planificador()
    yield
    planificador.shutdown(wait=False)


# Crear una sola aplicación.
app = FastAPI(
    title="SyncroMap API",
    description=(
        "API para gestionar obras, usuarios y asistencia "
        "mediante validación de ubicación."
    ),
    version="1.0.0",
    lifespan=ciclo_de_vida,
)

# Configuración para las pruebas de desarrollo.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Conectar las rutas de cada módulo.
app.include_router(acceso.router)

# Todo lo que usa el panel exige haber iniciado sesión.
solo_con_sesion = [Depends(acceso.administrador_actual)]
app.include_router(obras.router, dependencies=solo_con_sesion)
app.include_router(usuarios.router, dependencies=solo_con_sesion)
app.include_router(asistencia.router, dependencies=solo_con_sesion)
app.include_router(incidencias.router, dependencies=solo_con_sesion)

# El webhook no lleva sesión: Meta firma cada mensaje y esa firma se verifica.
app.include_router(whatsapp.router)


@app.get("/", tags=["Inicio"])
def mensaje_bienvenida():
    return {
        "mensaje": "Bienvenido a SyncroMap API",
        "documentacion": "/docs",
        "estatus": "Servidor en línea",
    }
