from logging.config import fileConfig

from alembic import context

from app import create_app
from app.extensions import db

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)

application = create_app()
target_metadata = db.metadata


def run_migrations_offline():
    with application.app_context():
        context.configure(
            url=application.config["SQLALCHEMY_DATABASE_URI"],
            target_metadata=target_metadata,
            literal_binds=True,
            dialect_opts={"paramstyle": "named"},
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


def run_migrations_online():
    with application.app_context():
        with db.engine.connect() as connection:
            context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
            with context.begin_transaction():
                context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
