import os
from pathlib import Path
from dotenv import load_dotenv

def load_env():
    ENV = os.getenv("ENVIRONMENT", "development")
    dotenv_path = Path(f".env.{ENV}")

    # 1. Tenta carregar o .env local (para dev/staging/produção local)
    if dotenv_path.exists():
        load_dotenv(dotenv_path)
    # 2. Se estiver no Streamlit Cloud, usa st.secrets
    else:
        try:
            import streamlit as st
            for key, val in st.secrets.items():
                os.environ.setdefault(key, str(val))
        except ModuleNotFoundError:
            raise FileNotFoundError(f"Arquivo {dotenv_path} não encontrado e st.secrets não disponível.")

load_env()

class Settings:
    ENVIRONMENT     = os.getenv("ENVIRONMENT", "production")
    DB_PATH         = os.getenv("DB_PATH")
    ADMIN_SECRET    = os.getenv("ADMIN_SECRET")
    WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
    WHATSAPP_LINK   = os.getenv("WHATSAPP_LINK")

# Configurações de email para monitoramento
ALERT_EMAIL = "mbcangst@gmail.com"  # Email que receberá os alertas
SMTP_SERVER = "smtp.gmail.com"  # Servidor SMTP
SMTP_PORT = 587  # Porta SMTP
SMTP_USER = "mbcangst@gmail.com"  # Email de envio
SMTP_PASS = os.getenv("GMAIL_APP_PASSWORD")  # Senha de aplicativo do Gmail

settings = Settings()