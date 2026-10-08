import pytest
from fastapi import HTTPException

import Model as models
import routers.obras as obras
import routers.usuarios as usuarios
from schemas import UsuarioCreate


def nuevo(telefono, obra_id=None, **extra):
    return UsuarioCreate(nombre="Otro", telefono=telefono, obra_id=obra_id, **extra)


def test_crear_usuario_con_telefono_repetido(db, usuario):
    with pytest.raises(HTTPException) as error:
        usuarios.crear_usuario(nuevo(usuario.telefono), db)
    assert error.value.status_code == 400


def test_crear_usuario_con_obra_inexistente(db):
    with pytest.raises(HTTPException) as error:
        usuarios.crear_usuario(nuevo("5215500000002", obra_id=999), db)
    assert error.value.status_code == 404


def test_actualizar_con_el_telefono_de_otro_usuario(db, usuario, obra):
    otro = usuarios.crear_usuario(nuevo("5215500000002", obra.id), db)
    with pytest.raises(HTTPException) as error:
        usuarios.actualizar_usuario(otro.id, nuevo(usuario.telefono), db)
    assert error.value.status_code == 400


def test_actualizar_conservando_el_propio_telefono(db, usuario, obra):
    actualizado = usuarios.actualizar_usuario(
        usuario.id, nuevo(usuario.telefono, obra.id), db
    )
    assert actualizado.nombre == "Otro"


def test_baja_de_usuario_conserva_su_historial(db, usuario, obra):
    db.add(
        models.Asistencia(
            usuario_id=usuario.id,
            obra_id=obra.id,
            tipo="entrada",
            latitud_enviada=0,
            longitud_enviada=0,
            distancia_calculada_m=0,
            estatus_asistencia="A tiempo",
        )
    )
    db.commit()

    usuarios.eliminar_usuario(usuario.id, db)

    assert usuarios.obtener_usuario(usuario.id, db).activo is False
    assert db.query(models.Asistencia).count() == 1


def test_las_listas_ocultan_los_inactivos(db, usuario, obra):
    usuarios.eliminar_usuario(usuario.id, db)
    obras.eliminar_obra(obra.id, db)

    assert usuarios.listar_usuarios(False, db) == []
    assert obras.listar_obras(False, db) == []
    assert len(usuarios.listar_usuarios(True, db)) == 1
    assert len(obras.listar_obras(True, db)) == 1


def test_reactivar_usuario(db, usuario, obra):
    usuarios.eliminar_usuario(usuario.id, db)
    reactivado = usuarios.actualizar_usuario(
        usuario.id, nuevo(usuario.telefono, obra.id, activo=True), db
    )
    assert reactivado.activo is True


def test_baja_de_usuario_inexistente(db):
    with pytest.raises(HTTPException) as error:
        usuarios.eliminar_usuario(999, db)
    assert error.value.status_code == 404
