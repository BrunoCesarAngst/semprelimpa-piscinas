import os
from dotenv import load_dotenv

# Detectar ambiente
env = os.getenv("ENVIRONMENT", "development")

# Selecionar arquivo de ambiente
if env == "production":
    env_file = ".env.production"
elif env == "staging":
    env_file = ".env.staging"
elif env == "development":
    env_file = ".env.development"
else:
    env_file = ".env"

# Carregar o arquivo de ambiente
load_dotenv(env_file)

class Settings:
    def __init__(self):
        # Configurações padrão
        self.ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
        self.DB_PATH = os.getenv("DB_PATH", "test.db")
        self.ADMIN_SECRET = os.getenv("ADMIN_SECRET", "admin_secret")
        self.WEATHER_API_KEY = os.getenv("WEATHER_API_KEY", "")
        self.WHATSAPP_LINK = os.getenv("WHATSAPP_LINK", "")

        # Tentar carregar variáveis de ambiente do arquivo .env
        self.load_env()

    def load_env(self):
        """Carrega variáveis de ambiente do arquivo .env"""
        # Atualizar configurações após carregar o .env
        self.ENVIRONMENT = os.getenv("ENVIRONMENT", self.ENVIRONMENT)
        self.DB_PATH = os.getenv("DB_PATH", self.DB_PATH)
        self.ADMIN_SECRET = os.getenv("ADMIN_SECRET", self.ADMIN_SECRET)
        self.WEATHER_API_KEY = os.getenv("WEATHER_API_KEY", self.WEATHER_API_KEY)
        self.WHATSAPP_LINK = os.getenv("WHATSAPP_LINK", self.WHATSAPP_LINK)

        # Tentar carregar configurações do Streamlit apenas se não estiver em um ambiente de migração
        if not os.environ.get("ALEMBIC_MIGRATION"):
            try:
                import streamlit as st
                for key, val in st.secrets.items():
                    os.environ[key] = str(val)
                    # Atualizar configurações com valores do Streamlit
                    if hasattr(self, key.upper()):
                        setattr(self, key.upper(), str(val))
            except (ImportError, FileNotFoundError):
                # Ignorar erros do Streamlit durante migrações
                pass

# Instância global das configurações
settings = Settings()

# Configurações de email para monitoramento
ALERT_EMAIL = "mbcangst@gmail.com"  # Email que receberá os alertas
SMTP_SERVER = "smtp.gmail.com"  # Servidor SMTP
SMTP_PORT = 587  # Porta SMTP
SMTP_USER = "mbcangst@gmail.com"  # Email de envio
SMTP_PASS = os.getenv("GMAIL_APP_PASSWORD")  # Senha de aplicativo do Gmail

if not settings.DB_PATH:
    print("ALERTA CRÍTICO: A variável de ambiente DB_PATH não está definida! O aplicativo pode não funcionar corretamente.")