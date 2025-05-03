import pytest
import sqlite3
import os
from migrations import run_migrations, get_db_version, set_db_version
from streamlit_app import get_db_connection, hash_pwd, check_pwd

@pytest.fixture
def test_db():
    """Cria um banco de dados temporário para testes"""
    db_path = "data/test_database.db"
    os.makedirs("data", exist_ok=True)

    # Remover banco de dados existente
    if os.path.exists(db_path):
        os.remove(db_path)

    # Criar novo banco
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Configurar ambiente de teste
    os.environ['ENVIRONMENT'] = 'test'

    yield conn

    # Limpeza após os testes
    conn.close()
    if os.path.exists(db_path):
        os.remove(db_path)

def test_migrations(test_db):
    """Testa se as migrações são aplicadas corretamente"""
    # Versão inicial deve ser 0
    assert get_db_version(test_db) == 0

    # Executar migrações
    run_migrations(test_db)

    # Verificar versão final
    assert get_db_version(test_db) == 4

    # Verificar se as tabelas foram criadas
    cursor = test_db.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    assert 'users' in tables
    assert 'appointments' in tables

    # Verificar se as colunas foram adicionadas
    cursor.execute("PRAGMA table_info(users)")
    columns = [row[1] for row in cursor.fetchall()]
    assert 'phone' in columns

    cursor.execute("PRAGMA table_info(appointments)")
    columns = [row[1] for row in cursor.fetchall()]
    assert 'address' in columns
    assert 'price' in columns

def test_password_hashing():
    """Testa as funções de hash de senha"""
    password = "test123"
    hashed = hash_pwd(password)

    # Verificar se o hash é consistente
    assert hashed == hash_pwd(password)

    # Verificar se senhas diferentes geram hashes diferentes
    assert hashed != hash_pwd("test124")

    # Verificar se a função de verificação funciona
    assert check_pwd(hashed, password)
    assert not check_pwd(hashed, "wrong_password")

def test_db_connection():
    """Testa a conexão com o banco de dados"""
    # Configurar ambiente de teste
    os.environ['ENVIRONMENT'] = 'test'

    # Testar conexão
    conn = get_db_connection()
    assert conn is not None
    conn.close()