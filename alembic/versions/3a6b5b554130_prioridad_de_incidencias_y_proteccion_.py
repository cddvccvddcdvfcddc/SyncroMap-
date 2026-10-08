"""prioridad de incidencias y proteccion del historial

Revision ID: 3a6b5b554130
Revises: 83aeb2b91285
Create Date: 2026-10-08 14:07:57.386444

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3a6b5b554130'
down_revision: Union[str, Sequence[str], None] = '83aeb2b91285'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (tabla, columna, tabla referida, nombre de la llave foranea)
LLAVES_DE_HISTORIAL = [
    ("asistencias", "usuario_id", "usuarios", "asistencias_usuario_id_fkey"),
    ("asistencias", "obra_id", "obras", "asistencias_obra_id_fkey"),
    ("incidencias", "usuario_id", "usuarios", "incidencias_usuario_id_fkey"),
]


def cambiar_borrado(regla: str) -> None:
    for tabla, columna, referida, nombre in LLAVES_DE_HISTORIAL:
        op.drop_constraint(nombre, tabla, type_="foreignkey")
        op.create_foreign_key(
            nombre, tabla, referida, [columna], ["id"], ondelete=regla
        )


def upgrade() -> None:
    # El tipo de fichaje pasa a ser obligatorio.
    op.alter_column(
        "asistencias", "tipo", existing_type=sa.VARCHAR(length=10), nullable=False
    )

    # Prioridad de la incidencia; queda vacia hasta que se clasifica.
    op.add_column(
        "incidencias", sa.Column("prioridad", sa.String(length=10), nullable=True)
    )
    op.create_check_constraint(
        "incidencias_prioridad_check",
        "incidencias",
        "prioridad IN ('Alta', 'Media', 'Baja')",
    )

    # El historial ya no se borra en cascada al eliminar un usuario o una obra.
    cambiar_borrado("RESTRICT")


def downgrade() -> None:
    cambiar_borrado("CASCADE")
    op.drop_constraint("incidencias_prioridad_check", "incidencias", type_="check")
    op.drop_column("incidencias", "prioridad")
    op.alter_column(
        "asistencias", "tipo", existing_type=sa.VARCHAR(length=10), nullable=True
    )
