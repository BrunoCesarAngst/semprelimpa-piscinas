import hashlib

def hash_pwd(password: str) -> str:
    """Gera um hash SHA-256 da senha fornecida."""
    return hashlib.sha256(password.encode()).hexdigest()

def check_pwd(hashed: str, password: str) -> bool:
    """Verifica se a senha fornecida corresponde ao hash armazenado."""
    return hashed == hash_pwd(password)