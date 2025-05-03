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

settings = Settings()