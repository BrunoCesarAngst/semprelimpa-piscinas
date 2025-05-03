import pytest
import os
import sqlite3
from migrations import run_migrations, get_db_version
from db_utils import get_db_connection, hash_pwd, check_pwd

# Configurar variáveis de ambiente para teste
os.environ['TESTING'] = 'true'
os.environ['DB_PATH'] = 'data/test_database.db'

@pytest.fixture
def test_db():
    """Fixture para criar um banco de dados temporário para testes"""
    # Garantir que o diretório data existe
    os.makedirs('data', exist_ok=True)

    # Criar banco de dados temporário
    conn = sqlite3.connect(os.environ['DB_PATH'])
    conn.row_factory = sqlite3.Row

    # Aplicar migrações
    run_migrations(conn)

    yield conn

    # Limpar após os testes
    conn.close()
    os.remove(os.environ['DB_PATH'])

def test_migrations(test_db):
    """Testa se as migrações foram aplicadas corretamente"""
    cursor = test_db.cursor()

    # Verificar versão atual do banco
    version = get_db_version(test_db)
    assert version > 0

    # Verificar se as tabelas necessárias existem
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row['name'] for row in cursor.fetchall()]
    assert 'users' in tables
    assert 'appointments' in tables

def test_password_hashing():
    """Testa as funções de hash de senha"""
    password = "test123"
    hashed = hash_pwd(password)

    # Verificar se o hash é diferente da senha original
    assert hashed != password

    # Verificar se a verificação funciona
    assert check_pwd(hashed, password)
    assert not check_pwd(hashed, "wrong_password")

def test_db_connection():
    """Testa a conexão com o banco de dados"""
    conn = get_db_connection()
    assert conn is not None

    # Verificar se é possível executar uma consulta
    cursor = conn.cursor()
    cursor.execute("SELECT 1")
    result = cursor.fetchone()
    assert result[0] == 1

    conn.close()