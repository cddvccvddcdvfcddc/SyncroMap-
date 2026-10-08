from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import Model as models
from Conexion_DB import engine
from routers import obras, usuarios, asistencia

# Crear las tablas que aún no existan.
models.Base.metadata.create_all(bind=engine)

# Crear una sola aplicación.
app = FastAPI(
    title="SyncroMap API",
    description=(
        "API para gestionar obras, usuarios y asistencia "
        "mediante validación de ubicación."
    ),
    version="1.0.0",
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
app.include_router(obras.router)
app.include_router(usuarios.router)
app.include_router(asistencia.router)


@app.get("/", tags=["Inicio"])
def mensaje_bienvenida():
    return {
        "mensaje": "Bienvenido a SyncroMap API",
        "documentacion": "/docs",
        "estatus": "Servidor en línea",
    }
