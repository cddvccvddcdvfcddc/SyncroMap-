"""Crea una cuenta para entrar al panel, o le cambia la contraseña si ya existe.

Uso:  py crear_administrador.py
"""

import getpass
import sys

import Model as models
from Conexion_DB import SessionLocal
from routers.acceso import normalizar_usuario
from utils.seguridad import LARGO_MINIMO_DE_CONTRASENA, hash_de_contrasena


def guardar_administrador(db, usuario: str, contrasena: str, nombre: str = ""):
    # Devuelve la cuenta y si se acaba de crear (True) o ya existía (False).
    usuario = normalizar_usuario(usuario)
    if not usuario:
        raise ValueError("El usuario no puede quedar vacío.")
    if len(contrasena) < LARGO_MINIMO_DE_CONTRASENA:
        raise ValueError(
            f"La contraseña debe tener al menos {LARGO_MINIMO_DE_CONTRASENA} caracteres."
        )

    administrador = (
        db.query(models.Administrador)
        .filter(models.Administrador.usuario == usuario)
        .first()
    )
    es_nuevo = administrador is None
    if es_nuevo:
        administrador = models.Administrador(usuario=usuario, nombre=nombre or usuario)
        db.add(administrador)
    elif nombre:
        administrador.nombre = nombre

    administrador.contrasena_hash = hash_de_contrasena(contrasena)
    administrador.activo = True
    db.commit()
    return administrador, es_nuevo


def main():
    print("Cuenta para entrar al panel de SyncroMap")
    usuario = input("Usuario (por ejemplo, mario): ")
    nombre = input("Nombre completo (opcional): ").strip()
    # Lo que se escribe aquí no se ve en la pantalla; es normal.
    contrasena = getpass.getpass("Contraseña (no se ve al escribir): ")
    if contrasena != getpass.getpass("Repite la contraseña: "):
        sys.exit("Las contraseñas no coinciden. No se guardó nada.")

    db = SessionLocal()
    try:
        administrador, es_nuevo = guardar_administrador(db, usuario, contrasena, nombre)
        # Se lee antes de cerrar la conexión; después ya no se puede consultar.
        usuario_guardado = administrador.usuario
    except ValueError as error:
        sys.exit(f"{error} No se guardó nada.")
    finally:
        db.close()

    accion = "Cuenta creada" if es_nuevo else "Contraseña actualizada"
    print(f"{accion}. Ya puedes entrar al panel con el usuario: {usuario_guardado}")


if __name__ == "__main__":
    main()
