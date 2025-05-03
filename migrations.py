import sqlite3
from typing import List, Tuple

def get_db_version(conn: sqlite3.Connection) -> int:
    """Retorna a versão atual do banco de dados"""
    cur = conn.cursor()
    cur.execute("PRAGMA user_version")
    return cur.fetchone()[0]

def set_db_version(conn: sqlite3.Connection, version: int) -> None:
    """Define a versão do banco de dados"""
    conn.execute(f"PRAGMA user_version = {version}")

def column_exists(conn: sqlite3.Connection, table: str, column: str) -> bool:
    """Verifica se uma coluna existe em uma tabela"""
    try:
        conn.execute(f"SELECT {column} FROM {table} LIMIT 1")
        return True
    except sqlite3.OperationalError:
        return False

def run_migrations(conn: sqlite3.Connection) -> None:
    """Executa todas as migrações pendentes"""
    current_version = get_db_version(conn)

    # Lista de migrações: (versão, descrição, SQL)
    migrations: List[Tuple[int, str, str]] = [
        (1, "Criação inicial do banco de dados", """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                is_admin BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                service_type TEXT NOT NULL,
                date DATE NOT NULL,
                time TIME NOT NULL,
                status TEXT DEFAULT 'pending',
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
        """),

        (2, "Adiciona coluna de telefone aos usuários", """
            ALTER TABLE users ADD COLUMN phone TEXT;
        """),

        (3, "Adiciona coluna de endereço aos agendamentos", """
            ALTER TABLE appointments ADD COLUMN address TEXT;
        """),

        (4, "Adiciona coluna de preço aos agendamentos", """
            ALTER TABLE appointments ADD COLUMN price DECIMAL(10,2);
        """)
    ]

    for version, description, sql in migrations:
        if current_version < version:
            print(f"🔄 Executando migração {version}: {description}")
            try:
                # Verificar se a migração é um ALTER TABLE
                if "ALTER TABLE" in sql:
                    table = sql.split("ALTER TABLE")[1].split("ADD COLUMN")[0].strip()
                    column = sql.split("ADD COLUMN")[1].split()[0].strip()

                    # Se a coluna já existe, pular a migração
                    if column_exists(conn, table, column):
                        print(f"⚠️ Coluna {column} já existe na tabela {table}, pulando migração")
                        set_db_version(conn, version)
                        conn.commit()
                        continue

                conn.executescript(sql)
                set_db_version(conn, version)
                conn.commit()
                print(f"✅ Migração {version} concluída com sucesso")
            except sqlite3.Error as e:
                print(f"❌ Erro na migração {version}: {e}")
                conn.rollback()
                raise