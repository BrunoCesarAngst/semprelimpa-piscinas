import os
import sqlite3
from migrations import run_migrations

def get_db_connection(environment: str) -> sqlite3.Connection:
    """Retorna uma conexão com o banco de dados do ambiente especificado"""
    db_path = f"data/database_{environment}.db"
    return sqlite3.connect(db_path)

def create_database(environment: str) -> None:
    """Cria e inicializa o banco de dados para o ambiente especificado"""
    db_path = f"data/database_{environment}.db"

    # Garante que o diretório data existe
    os.makedirs("data", exist_ok=True)

    # Conecta ao banco de dados
    print(f"🔄 Inicializando banco de dados para o ambiente {environment}...")
    conn = get_db_connection(environment)

    try:
        # Executa as migrações
        run_migrations(conn)
        print(f"✅ Banco de dados criado/atualizado com sucesso: {db_path}")
    except Exception as e:
        print(f"❌ Erro ao inicializar banco de dados: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    environments = ['development', 'staging', 'production']

    for env in environments:
        print(f"\n=== Configurando ambiente {env} ===")
        create_database(env)

    print("\n✨ Todos os bancos de dados foram inicializados com sucesso!")