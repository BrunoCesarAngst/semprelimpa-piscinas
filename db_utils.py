import sqlite3
import os
import hashlib
from dotenv import load_dotenv

# Carregar variáveis de ambiente
load_dotenv()

def get_db_connection():
    """Retorna uma conexão com o banco de dados apropriado para o ambiente atual"""
    # Garantir que o diretório data existe
    os.makedirs('data', exist_ok=True)

    # Criar conexão com o banco de dados
    conn = sqlite3.connect(os.getenv('DB_PATH', 'data/database_production.db'))
    conn.row_factory = sqlite3.Row
    return conn

def hash_pwd(pwd: str) -> str:
    """Gera um hash SHA-256 da senha"""
    return hashlib.sha256(pwd.encode()).hexdigest()

def check_pwd(hashval: str, pwd: str) -> bool:
    """Verifica se a senha corresponde ao hash"""
    return hashval == hashlib.sha256(pwd.encode()).hexdigest()