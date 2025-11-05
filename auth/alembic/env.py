from __future__ import annotations
import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# this is the Alembic Config object, which provides access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Inject DB URL from env
db_url = os.environ.get("MIGRATIONS_DATABASE_URL") or os.environ.get("DATABASE_URL")
# Normalize to SQLAlchemy's psycopg v3 driver if a generic URL is provided
if db_url and db_url.startswith("postgresql://") and "+psycopg" not in db_url:
    db_url = db_url.replace("postgresql://", "postgresql+psycopg://", 1)
if not db_url:
    raise RuntimeError("DATABASE_URL or MIGRATIONS_DATABASE_URL must be set for migrations")
config.set_main_option("sqlalchemy.url", db_url)

# Target metadata not used (SQL migrations)
target_metadata = None

# Ensure version table lives in 'auth' schema
config.set_main_option("version_table_schema", "auth")

# For multiple schemas support
include_schemas = True


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    ctx_cfg = {
        "url": url,
        "target_metadata": target_metadata,
        "literal_binds": True,
        "dialect_opts": {"paramstyle": "named"},
        "version_table_schema": "auth",
        "include_schemas": include_schemas,
    }
    with context.begin_transaction():
        context.configure(**ctx_cfg)
        # Set search_path so unqualified names hit our schema first
        context.execute("SET search_path TO auth, public")
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        # Ensure schema exists
        connection.exec_driver_sql("CREATE SCHEMA IF NOT EXISTS auth")
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table_schema="auth",
            include_schemas=include_schemas,
        )
        with context.begin_transaction():
            # Make sure our schema is first in search_path
            context.execute("SET search_path TO auth, public")
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
