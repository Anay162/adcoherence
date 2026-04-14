import os
import sys
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# Make sure the backend package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from models.base import Base
from models import User, ConnectedAccount, Audit, AdPagePair  # noqa: F401 — registers models

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Allow DATABASE_URL env var to override alembic.ini (useful in CI/CD)
_ini_url = config.get_main_option("sqlalchemy.url") or ""
db_url = os.environ.get("DATABASE_URL", _ini_url)
# Alembic needs a sync driver; swap asyncpg for psycopg2
db_url = (
    db_url
    .replace("postgresql+asyncpg://", "postgresql://")
    .replace("postgres://", "postgresql://")
)
if not db_url:
    db_url = "postgresql://adcoherence:adcoherence@localhost:5432/adcoherence"
config.set_main_option("sqlalchemy.url", db_url)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    from sqlalchemy import create_engine
    connectable = create_engine(db_url, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
