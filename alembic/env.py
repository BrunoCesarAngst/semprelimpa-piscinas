from logging.config import fileConfig
import os
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
from models import Base
from config import settings

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# Obter ambiente atual
environment = os.environ.get("ENVIRONMENT", "development")

# Configurações específicas por ambiente
if environment == "production":
    # Configurações de produção
    config.set_main_option("sqlalchemy.url", os.environ.get("DATABASE_URL", settings.DB_PATH))
    print("🔒 Ambiente de produção detectado")
else:
    # Configurações de desenvolvimento
    config.set_main_option("sqlalchemy.url", f"sqlite:///{settings.DB_PATH}")
    print("🔧 Ambiente de desenvolvimento detectado")

# Adicionar suporte para SQLite
def include_object(object, name, type_, reflected, compare_to):
    if type_ == "table" and name == "sqlite_sequence":
        return False
    return True

def process_revision_directives(context, revision, directives):
    # Não ignorar tabelas vazias na migração inicial
    if directives and len(directives) > 0:
        script = directives[0]
        if script.upgrade_ops.is_empty():
            # Verificar se é a migração inicial
            if context.get_current_revision() is None:
                print("🔧 Migração inicial - não ignorando tabelas vazias")
                return
            directives[:] = []
            print("🔧 Nenhuma alteração detectada")

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Configurações específicas para cada ambiente
    configuration = config.get_section(config.config_ini_section)

    # Remover configurações de pool para SQLite
    if "sqlite" in configuration.get("sqlalchemy.url", ""):
        # SQLite não suporta configurações de pool
        for key in list(configuration.keys()):
            if key.startswith("sqlalchemy.pool_"):
                del configuration[key]
    else:
        # Configurações de pool apenas para outros bancos de dados
        if environment == "production":
            configuration["sqlalchemy.pool_size"] = "20"
            configuration["sqlalchemy.max_overflow"] = "10"
            configuration["sqlalchemy.pool_timeout"] = "30"
            configuration["sqlalchemy.pool_recycle"] = "1800"
        else:
            configuration["sqlalchemy.pool_size"] = "5"
            configuration["sqlalchemy.max_overflow"] = "2"
            configuration["sqlalchemy.pool_timeout"] = "30"
            configuration["sqlalchemy.pool_recycle"] = "3600"

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
            render_as_batch=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
