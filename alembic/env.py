from logging.config import fileConfig

from alembic import context

import Model as models
from Conexion_DB import DATABASE_URL, engine

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Los modelos de Model.py son la referencia para generar las migraciones.
target_metadata = models.Base.metadata


def run_migrations_offline() -> None:
    # Genera el SQL sin conectarse a la base (alembic upgrade head --sql).
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    # Usa la misma conexión del .env que el resto de la aplicación.
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
