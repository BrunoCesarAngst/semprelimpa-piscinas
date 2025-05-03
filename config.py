import os
from pathlib import Path
from dotenv import load_dotenv

ENV = os.getenv("ENVIRONMENT", "development")

dotenv_path = Path(f".env.{ENV}")
if dotenv_path.exists():
    load_dotenv(dotenv_path)
else:
    raise FileNotFoundError(f"Arquivo {dotenv_path} não encontrado")

# Se for produção, carrega também o secrets.toml do Streamlit
if ENV == "production":
    try:
        import streamlit as st
        for key, val in st.secrets.items():
            os.environ.setdefault(key, val)
    except ModuleNotFoundError:
        pass

class Settings:
    ENVIRONMENT     = ENV
    DB_PATH         = os.getenv("DB_PATH")
    WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
    WHATSAPP_LINK   = os.getenv("WHATSAPP_LINK")
    ADMIN_SECRET    = os.getenv("ADMIN_SECRET")

settings = Settings()