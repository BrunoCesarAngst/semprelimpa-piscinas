import streamlit as st
from streamlit_folium import folium_static
import folium
import pandas as pd
import requests
from datetime import datetime, timedelta
import os
import urllib.parse
import webbrowser
from feature_flags import feature_flags
from config import settings
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from models import User, Service, Appointment, Config, Gallery, Base, AuthToken
from utils import hash_pwd, check_pwd
import alembic.config
from alembic import command
from alembic.script import ScriptDirectory
from alembic.runtime.environment import EnvironmentContext
import shutil
import secrets
import json
import hmac
import hashlib
import base64
import subprocess
import sys
import extra_streamlit_components as stx

# Verificar e instalar dependências
def install_dependencies():
    try:
        import extra_streamlit_components as stx
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "extra-streamlit-components"])
        import extra_streamlit_components as stx

install_dependencies()

# ---------- FUNÇÕES DE GERENCIAMENTO DE TOKENS ----------
def generate_token():
    """Gera um token aleatório seguro."""
    return secrets.token_hex(32)

def create_auth_token(user_id, expiry_hours=10):
    """
    Cria um novo token de autenticação para o usuário.

    Args:
        user_id: ID do usuário
        expiry_hours: Horas até a expiração do token

    Returns:
        str: Token gerado
    """
    session = Session()
    try:
        # Limpar tokens expirados
        cleanup_expired_tokens()

        # Gerar novo token
        token = generate_token()
        now = datetime.now()
        expires_at = now + timedelta(hours=expiry_hours)

        # Salvar no banco de dados
        auth_token = AuthToken(
            user_id=user_id,
            token=token,
            created_at=now.isoformat(),
            expires_at=expires_at.isoformat()
        )
        session.add(auth_token)
        session.commit()

        # Criar cookie seguro
        cookie_value = create_secure_cookie(user_id, token)
        return cookie_value
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def validate_auth_token(cookie_value):
    """
    Valida um token de autenticação.

    Args:
        cookie_value: Valor do cookie

    Returns:
        int or None: ID do usuário se válido, None caso contrário
    """
    try:
        # Decodificar cookie
        user_id, token = decode_secure_cookie(cookie_value)
        if not user_id or not token:
            return None

        # Verificar no banco de dados
        session = Session()
        auth_token = session.query(AuthToken).filter_by(
            user_id=user_id,
            token=token
        ).first()
        session.close()

        if not auth_token:
            return None

        # Verificar expiração
        expires_at = datetime.fromisoformat(auth_token.expires_at)
        if datetime.now() > expires_at:
            # Token expirado, remover
            delete_auth_token(user_id, token)
            return None

        return user_id
    except Exception:
        return None

def delete_auth_token(user_id, token):
    """Remove um token específico do banco de dados."""
    session = Session()
    try:
        session.query(AuthToken).filter_by(
            user_id=user_id,
            token=token
        ).delete()
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def cleanup_expired_tokens():
    """Remove todos os tokens expirados do banco de dados."""
    session = Session()
    try:
        now = datetime.now().isoformat()
        session.query(AuthToken).filter(
            AuthToken.expires_at < now
        ).delete()
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def logout_user(cookie_value):
    """
    Realiza o logout do usuário removendo o token.

    Args:
        cookie_value: Valor do cookie

    Returns:
        bool: True se logout bem-sucedido, False caso contrário
    """
    try:
        user_id, token = decode_secure_cookie(cookie_value)
        if user_id and token:
            delete_auth_token(user_id, token)
            return True
        return False
    except Exception:
        return False

def create_secure_cookie(user_id, token, secret_key=None):
    """
    Cria um cookie seguro com HMAC para verificação de integridade.

    Args:
        user_id: ID do usuário
        token: Token de autenticação
        secret_key: Chave secreta para assinatura (opcional)

    Returns:
        str: Valor codificado do cookie
    """
    if secret_key is None:
        secret_key = settings.ADMIN_SECRET

    payload = json.dumps({"user_id": user_id, "token": token})
    payload_b64 = base64.b64encode(payload.encode()).decode()

    # Criar assinatura HMAC
    signature = hmac.new(
        secret_key.encode(),
        payload_b64.encode(),
        hashlib.sha256
    ).hexdigest()

    # Combinar payload e assinatura
    return f"{payload_b64}.{signature}"

def decode_secure_cookie(cookie_value, secret_key=None):
    """
    Decodifica e verifica um cookie seguro.

    Args:
        cookie_value: Valor do cookie
        secret_key: Chave secreta para verificação (opcional)

    Returns:
        tuple: (user_id, token) se válido, (None, None) caso contrário
    """
    if secret_key is None:
        secret_key = settings.ADMIN_SECRET

    try:
        # Separar payload e assinatura
        payload_b64, signature = cookie_value.split(".")

        # Verificar assinatura
        expected_signature = hmac.new(
            secret_key.encode(),
            payload_b64.encode(),
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(signature, expected_signature):
            return None, None

        # Decodificar payload
        payload = json.loads(base64.b64decode(payload_b64).decode())
        return payload["user_id"], payload["token"]
    except Exception:
        return None, None

# ---------- CONFIGURAÇÕES ----------
ENVIRONMENT = settings.ENVIRONMENT
ADMIN_SECRET = settings.ADMIN_SECRET
DB_PATH = settings.DB_PATH
WEATHER_API_KEY = settings.WEATHER_API_KEY
WHATSAPP_LINK = settings.WHATSAPP_LINK

# Inicializar engine e Session
engine = create_engine(f"sqlite:///{DB_PATH}")
Session = sessionmaker(bind=engine)

# Dicionário de tradução do tempo
WEATHER_TRANSLATIONS = {
    'clear sky': 'céu limpo',
    'few clouds': 'poucas nuvens',
    'scattered clouds': 'nuvens dispersas',
    'broken clouds': 'nuvens quebradas',
    'overcast clouds': 'nublado',
    'light rain': 'chuva leve',
    'moderate rain': 'chuva moderada',
    'heavy intensity rain': 'chuva forte',
    'very heavy rain': 'chuva muito forte',
    'extreme rain': 'chuva extrema',
    'freezing rain': 'chuva congelante',
    'light intensity shower rain': 'chuva leve',
    'shower rain': 'chuva',
    'heavy intensity shower rain': 'chuva forte',
    'ragged shower rain': 'chuva irregular',
    'light snow': 'neve leve',
    'snow': 'neve',
    'heavy snow': 'neve forte',
    'sleet': 'granizo',
    'light shower sleet': 'granizo leve',
    'shower sleet': 'granizo',
    'light rain and snow': 'chuva e neve leve',
    'rain and snow': 'chuva e neve',
    'light shower snow': 'neve leve',
    'shower snow': 'neve',
    'heavy shower snow': 'neve forte',
    'mist': 'névoa',
    'smoke': 'fumaça',
    'haze': 'neblina',
    'sand/dust whirls': 'redemoinhos de areia/poeira',
    'fog': 'névoa',
    'sand': 'areia',
    'dust': 'poeira',
    'volcanic ash': 'cinza vulcânica',
    'squalls': 'rajadas',
    'tornado': 'tornado',
    'thunderstorm with light rain': 'trovoada com chuva leve',
    'thunderstorm with rain': 'trovoada com chuva',
    'thunderstorm with heavy rain': 'trovoada com chuva forte',
    'light thunderstorm': 'trovoada leve',
    'thunderstorm': 'trovoada',
    'heavy thunderstorm': 'trovoada forte',
    'ragged thunderstorm': 'trovoada irregular',
    'thunderstorm with light drizzle': 'trovoada com garoa leve',
    'thunderstorm with drizzle': 'trovoada com garoa',
    'thunderstorm with heavy drizzle': 'trovoada com garoa forte'
}

# ---------- FUNÇÕES AUXILIARES ----------
def create_default_services():
    """Cria os serviços padrão se não existirem"""
    session = Session()
    default_services = [
        (
            "Pacote Anual",
            "Manutenção completa da piscina durante todo o ano, incluindo limpeza semanal, controle químico e manutenção do equipamento. Ideal para quem quer manter sua piscina sempre em perfeitas condições.",
            1200.00
        ),
        (
            "Manutenção Semanal",
            "Limpeza semanal da piscina, incluindo aspiração, escovação, tratamento da água e verificação do pH. Garante a qualidade da água e o bom funcionamento do sistema.",
            150.00
        ),
        (
            "Limpeza Pesada",
            "Limpeza profunda da piscina, incluindo aspiração, escovação, tratamento de algas, limpeza de bordas e verificação completa do sistema. Indicado para piscinas que precisam de uma limpeza mais intensa.",
            300.00
        ),
        (
            "Controle Químico",
            "Análise e ajuste dos parâmetros químicos da água (pH, cloro, alcalinidade, etc). Garante a qualidade da água e a saúde dos usuários.",
            80.00
        )
    ]
    created = False
    try:
        for name, description, price in default_services:
            existing = session.query(Service).filter_by(name=name).first()
            if not existing:
                new_service = Service(
                    name=name,
                    description=description,
                    price=price,
                    active=1
                )
                session.add(new_service)
                created = True

        session.commit()
        if created:
            if 'show_success_services' not in st.session_state:
                st.session_state['show_success_services'] = True
            if st.session_state['show_success_services']:
                st.success("Serviços padrão criados com sucesso!")
                if st.button("Fechar mensagem", key="close_success_services"):
                    st.session_state['show_success_services'] = False
                    st.experimental_rerun()
    except Exception as e:
        session.rollback()
        st.error(f"Erro ao criar serviços padrão: {str(e)}")
    finally:
        session.close()

def backup_db():
    """
    Cria um backup do banco de dados atual.

    Returns:
        str: Caminho do arquivo de backup ou None em caso de erro
    """
    if not os.path.exists(DB_PATH):
        return None

    try:
        # Criar diretório de backup se não existir
        backup_dir = os.path.join(os.path.dirname(DB_PATH), "backups")
        os.makedirs(backup_dir, exist_ok=True)

        # Nome do arquivo de backup com timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(backup_dir, f"db_backup_{timestamp}.sqlite")

        # Copiar o arquivo do banco de dados
        shutil.copy2(DB_PATH, backup_file)

        # Manter apenas os 5 backups mais recentes
        backups = sorted([os.path.join(backup_dir, f) for f in os.listdir(backup_dir)])
        if len(backups) > 5:
            for old_backup in backups[:-5]:
                os.remove(old_backup)

        return backup_file
    except Exception as e:
        print(f"Erro ao criar backup: {str(e)}")
        return None

def run_alembic_migrations():
    """
    Executa automaticamente as migrações pendentes do Alembic.
    Deve ser chamado durante a inicialização do aplicativo.

    Returns:
        tuple: (success, message)
    """
    try:
        # Configurar o Alembic
        alembic_cfg = alembic.config.Config("alembic.ini")
        script = ScriptDirectory.from_config(alembic_cfg)
        # Salvar o script no próprio config
        alembic_cfg.attributes['script'] = script

        # Verificar se há migrações pendentes
        with EnvironmentContext(
            alembic_cfg,
            script,
            fn=lambda rev, _: script.get_revisions(rev)
        ) as env:
            env.configure(connection=engine.connect(), target_metadata=Base.metadata)
            context = env.get_context()
            current_rev = context.get_current_revision()
            head_rev = script.get_current_head()

            if current_rev != head_rev:
                # Há migrações pendentes, criar backup antes de aplicar
                backup_file = backup_db()

                # Executar migrações
                command.upgrade(alembic_cfg, "head")

                return True, f"Banco de dados atualizado para a revisão {head_rev}"
            else:
                return True, "Banco de dados já está na versão mais recente"

    except Exception as e:
        return False, f"Erro ao executar migrações: {str(e)}"

def init_db():
    """Inicializa o banco de dados"""
    if not DB_PATH:
        print("ERRO CRÍTICO: DB_PATH não está definido nas configurações. A inicialização do banco de dados foi abortada.")
        st.error("Erro crítico: A configuração do caminho do banco de dados (DB_PATH) não foi encontrada. O aplicativo não pode iniciar corretamente.")
        return

    # Garante que o diretório do banco de dados exista
    db_dir = os.path.dirname(DB_PATH)
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

    # Executar migrações Alembic
    success, message = run_alembic_migrations()
    if not success:
        st.warning(message)

    # Criar serviços padrão se necessário
    create_default_services()

def get_weather():
    # Previsão atual
    url_current = f"http://api.openweathermap.org/data/2.5/weather?q=Arroio do Sal,BR&units=metric&appid={WEATHER_API_KEY}&lang=pt_br"
    resp_current = requests.get(url_current).json()

    # Previsão para 8 dias
    url_forecast = f"http://api.openweathermap.org/data/2.5/forecast?q=Arroio do Sal,BR&units=metric&appid={WEATHER_API_KEY}&lang=pt_br"
    resp_forecast = requests.get(url_forecast).json()

    # Dados atuais
    current_data = {
        'description': WEATHER_TRANSLATIONS.get(resp_current['weather'][0]['description'].lower(), resp_current['weather'][0]['description']),
        'temp': round(resp_current['main']['temp']),
        'rain': round(resp_current.get('rain', {}).get('1h', 0), 1)
    }

    # Previsão para os próximos dias
    forecast_data = []
    for item in resp_forecast['list']:
        date = datetime.fromtimestamp(item['dt']).strftime('%d/%m %H:%M')
        forecast_data.append({
            'date': date,
            'description': WEATHER_TRANSLATIONS.get(item['weather'][0]['description'].lower(), item['weather'][0]['description']),
            'temp': round(item['main']['temp']),
            'rain': round(item.get('rain', {}).get('3h', 0), 1)
        })

    return current_data, forecast_data

# ---------- PÁGINAS PÚBLICAS ----------
def homepage():
    if os.path.exists("logo.png"):
        st.image("logo.png", width=200)
    st.title("Sempre Limpa Piscinas")

    session = Session()
    if feature_flags.is_enabled('GALERIA_FOTOS'):
        st.header("Antes & Depois")
        gallery = session.query(Gallery).all()
        for item in gallery:
            cols = st.columns(2)
            cols[0].image(item.before_path, caption=f"{item.caption} (Antes)")
            cols[1].image(item.after_path, caption=f"{item.caption} (Depois)")

    st.header("Serviços")
    services = session.query(Service).filter_by(active=1).all()
    for srv in services:
        st.subheader(srv.name)
        st.write(srv.description)
    session.close()

    # WhatsApp link
    wa_link = WHATSAPP_LINK
    st.markdown(
        f"<a href='{wa_link}' target='_blank'><img src='https://cdn-icons-png.flaticon.com/512/733/733585.png' width='24'/> Fale conosco pelo WhatsApp</a>",
        unsafe_allow_html=True
    )

    # Instagram link
    st.markdown(
        "<a href='https://www.instagram.com/semprelimpa_piscinas/?hl=pt-br' target='_blank'><img src='https://cdn-icons-png.flaticon.com/512/733/733558.png' width='24'/> Siga-nos no Instagram</a>",
        unsafe_allow_html=True
    )

def mapa_tempo():
    if not feature_flags.is_enabled('PREVISAO_TEMPO'):
        st.warning("A previsão do tempo está temporariamente indisponível.")
        return

    st.title("Área de Cobertura & Previsão do Tempo")

    # Coordenadas exatas de Arroio do Sal
    ARROIO_DO_SAL_LAT = -29.55083
    ARROIO_DO_SAL_LON = -49.88889

    # Mapa
    m = folium.Map(location=[ARROIO_DO_SAL_LAT, ARROIO_DO_SAL_LON], zoom_start=12)
    folium.Circle(
        location=[ARROIO_DO_SAL_LAT, ARROIO_DO_SAL_LON],
        radius=15000,  # 15km de raio
        color='#A7D8F0',
        fill=True,
        fill_opacity=0.1,
        popup="Área de Cobertura (15km)"
    ).add_to(m)

    folium.Marker(
        location=[ARROIO_DO_SAL_LAT, ARROIO_DO_SAL_LON],
        popup="Arroio do Sal<br>Litoral Norte do RS<br>Altitude: 6m",
        icon=folium.Icon(color='blue', icon='info-sign')
    ).add_to(m)

    # Adicionar cidades próximas
    folium.Marker(
        location=[-29.3333, -49.7333],  # Torres
        popup="Torres (30km ao norte)",
        icon=folium.Icon(color='green', icon='info-sign')
    ).add_to(m)

    folium.Marker(
        location=[-29.7333, -50.0167],  # Capão da Canoa
        popup="Capão da Canoa (30km ao sul)",
        icon=folium.Icon(color='green', icon='info-sign')
    ).add_to(m)

    folium_static(m)

    # Previsão do tempo
    st.subheader("Previsão do Tempo")
    current, forecast = get_weather()

    # Condições atuais
    st.markdown("### 🌡️ Condições Atuais")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Temperatura", f"{current['temp']}°C")
    with col2:
        st.metric("Condição", current['description'])
    with col3:
        st.metric("Chuva", f"{current['rain']} mm/h")

    # Previsão para os próximos dias
    st.markdown("### 📅 Previsão para os Próximos Dias")

    # Agrupar previsões por dia
    daily_forecast = {}
    for day in forecast:
        date = day['date'].split()[0]  # Pega apenas a data
        if date not in daily_forecast:
            daily_forecast[date] = []
        daily_forecast[date].append(day)

    # Dias da semana em português
    dias_semana = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']

    # Exibir previsão por dia
    for date, forecasts in daily_forecast.items():
        # Converter data para dia da semana
        try:
            # Adicionar o ano atual à data
            data_completa = f"{date}/{datetime.now().year}"
            data_obj = datetime.strptime(data_completa, '%d/%m/%Y')
            dia_semana = dias_semana[data_obj.weekday()]
        except:
            dia_semana = ""

        with st.expander(f"📅 {date} - {dia_semana}", expanded=True):
            cols = st.columns(len(forecasts))
            for i, forecast in enumerate(forecasts):
                with cols[i]:
                    st.markdown(f"**{forecast['date'].split()[1]}**")  # Hora
                    st.markdown(f"🌡️ {forecast['temp']}°C")
                    st.markdown(f"☁️ {forecast['description']}")
                    if forecast['rain'] > 0:
                        st.markdown(f"🌧️ {forecast['rain']} mm")
                    else:
                        st.markdown("🌧️ 0 mm")

def contato():
    st.title("Solicitar Orçamento")

    # Verificar se existem serviços disponíveis
    session = Session()
    services = session.query(Service).filter_by(active=1).all()
    session.close()

    if not services:
        st.warning("""
            No momento não temos serviços disponíveis para agendamento online.
            Por favor, entre em contato conosco pelo WhatsApp para verificar a disponibilidade.
        """)

        # Link do WhatsApp
        wa_link = WHATSAPP_LINK
        st.markdown(
            f"<a href='{wa_link}' target='_blank' style='display: inline-block; padding: 10px 20px; background-color: #25D366; color: white; text-decoration: none; border-radius: 5px;'>"
            f"<img src='https://cdn-icons-png.flaticon.com/512/733/733585.png' width='24' style='vertical-align: middle; margin-right: 8px;'/>"
            f"Fale conosco pelo WhatsApp</a>",
            unsafe_allow_html=True
        )
        return

    if feature_flags.is_enabled('NOVO_SISTEMA_AGENDAMENTO'):
        novo_sistema_agendamento()
    else:
        sistema_antigo_agendamento()

def novo_sistema_agendamento():
    """Implementação do novo sistema de agendamento"""
    st.info("Novo sistema de agendamento em beta!")

    # Verificar se o usuário está logado
    if not st.session_state.get('logged_in'):
        st.warning("Por favor, faça login ou cadastre-se para solicitar um orçamento.")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Login"):
                st.session_state['current_page'] = "Login"
                st.rerun()
        with col2:
            if st.button("Cadastro"):
                st.session_state['current_page'] = "Cadastro"
                st.rerun()
        return

    # Verificar se existem serviços disponíveis
    session = Session()
    services = session.query(Service).filter_by(active=1).all()
    if not services:
        st.warning("No momento não temos serviços disponíveis para agendamento. Por favor, entre em contato conosco pelo WhatsApp.")
        wa_link = WHATSAPP_LINK
        st.markdown(
            f"<a href='{wa_link}' target='_blank'><img src='https://cdn-icons-png.flaticon.com/512/733/733585.png' width='24'/> Fale conosco pelo WhatsApp</a>",
            unsafe_allow_html=True
        )
        return

    # Novo sistema com calendário visual
    st.subheader("Selecione a data e horário")
    col1, col2 = st.columns(2)

    with col1:
        date = st.date_input("Data desejada", format="DD/MM/YYYY")

    with col2:
        time = st.time_input("Horário desejado")

    # Verificar disponibilidade
    wd = date.weekday()
    max_appt = session.query(Config).filter_by(weekday=wd).first().max_appointments
    count = session.query(Appointment).filter_by(date=date.isoformat()).count()

    if max_appt and count >= max_appt:
        st.error("Dia cheio, escolha outra data.")
        return

    # Seleção de serviço
    st.subheader("Selecione o serviço")
    svc_dict = {s.name: (s.id, s.price) for s in services}
    svc = st.selectbox("Serviço", options=list(svc_dict.keys()))
    service_id, price = svc_dict[svc]

    # Pagamento online se disponível
    if feature_flags.is_enabled('PAGAMENTO_ONLINE'):
        st.markdown(f"**Valor do serviço:** R$ {price:,.2f}".replace(',', '_').replace('.', ',').replace('_', '.'))
        if st.checkbox("Pagar online (10% de desconto)"):
            price = price * 0.9
            st.markdown(f"**Valor com desconto:** R$ {price:,.2f}".replace(',', '_').replace('.', ',').replace('_', '.'))

    # Formulário de agendamento
    with st.form("novo_agendamento"):
        # Obter dados do usuário logado
        user = session.query(User).filter_by(id=st.session_state['user_id']).first()

        name = st.text_input("Nome", value=user.name)
        contact = st.text_input("Telefone", value=user.phone)
        address = st.text_input("Endereço da piscina", value=user.address)
        image = st.file_uploader("Foto da piscina (opcional)", type=['png','jpg','jpeg'])
        submitted = st.form_submit_button("Confirmar Agendamento")

        if submitted:
            img_path = None
            if image:
                os.makedirs("uploads", exist_ok=True)
                img_path = os.path.join("uploads", image.name)
                with open(img_path, "wb") as f:
                    f.write(image.getbuffer())

            new_appointment = Appointment(
                name=name,
                contact=contact,
                address=address,
                date=date.isoformat(),
                time=time.strftime("%H:%M"),
                service_id=service_id,
                status='novo',
                image_path=img_path,
                user_id=st.session_state['user_id']
            )
            session.add(new_appointment)
            session.commit()

            st.success("Agendamento realizado com sucesso!")

            # Integração com WhatsApp se disponível
            if feature_flags.is_enabled('INTEGRACAO_WHATSAPP'):
                wa_message = f"Olá! Seu agendamento foi confirmado para {date.strftime('%d/%m/%Y')} às {time.strftime('%H:%M')}. Valor: R$ {price:,.2f}"
                wa_link = f"{WHATSAPP_LINK}&text={urllib.parse.quote(wa_message)}"
                st.markdown(f"[Clique aqui para enviar mensagem no WhatsApp]({wa_link})")

def sistema_antigo_agendamento():
    """Implementação do sistema antigo de agendamento"""
    # Verificar se o usuário está logado
    if not st.session_state.get('logged_in'):
        st.warning("Por favor, faça login ou cadastre-se para solicitar um orçamento.")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Login"):
                st.session_state['current_page'] = "Login"
                st.rerun()
        with col2:
            if st.button("Cadastro"):
                st.session_state['current_page'] = "Cadastro"
                st.rerun()
        return

    # Verificar se existem serviços disponíveis
    session = Session()
    services = session.query(Service).filter_by(active=1).all()
    if not services:
        st.warning("No momento não temos serviços disponíveis para agendamento. Por favor, entre em contato conosco pelo WhatsApp.")
        wa_link = WHATSAPP_LINK
        st.markdown(
            f"<a href='{wa_link}' target='_blank'><img src='https://cdn-icons-png.flaticon.com/512/733/733585.png' width='24'/> Fale conosco pelo WhatsApp</a>",
            unsafe_allow_html=True
        )
        return

    svc_dict = {s.name: (s.id, s.price) for s in services}

    # Selectbox para escolher o serviço (fora do formulário)
    svc = st.selectbox("Serviço", options=list(svc_dict.keys()))
    service_id, price = svc_dict[svc]
    st.markdown(f"**Valor do serviço:** R$ {price:,.2f}".replace(',', '_').replace('.', ',').replace('_', '.'))

    with st.form("orcamento"):
        # Obter dados do usuário logado
        user = session.query(User).filter_by(id=st.session_state['user_id']).first()

        name = st.text_input("Nome", value=user.name)
        contact = st.text_input("Telefone", value=user.phone)
        address = st.text_input("Endereço da piscina", value=user.address)
        date = st.date_input("Data desejada", format="DD/MM/YYYY")
        time = st.time_input("Horário desejado")
        image = st.file_uploader("Foto da piscina (opcional)", type=['png','jpg','jpeg'])
        submitted = st.form_submit_button("Enviar")

        if submitted:
            wd = date.weekday()
            max_appt = session.query(Config).filter_by(weekday=wd).first().max_appointments
            count = session.query(Appointment).filter_by(date=date.isoformat()).count()

            if max_appt and count >= max_appt:
                st.error("Dia cheio, escolha outra data.")
            else:
                img_path = None
                if image:
                    os.makedirs("uploads", exist_ok=True)
                    img_path = os.path.join("uploads", image.name)
                    with open(img_path, "wb") as f:
                        f.write(image.getbuffer())

                new_appointment = Appointment(
                    user_id=st.session_state['user_id'],
                    service_id=service_id,
                    date=date,
                    time=time,
                    status='novo',
                    address=address,
                    price=price,
                    image_path=img_path,
                    created_at=datetime.now().isoformat()
                )
                session.add(new_appointment)
                st.success("Recebemos seu pedido! Entraremos em contato em breve.")
            session.commit()
            session.close()

def cadastro():
    import extra_streamlit_components as stx
    cookie_manager = stx.CookieManager()
    st.title("Cadastro de Usuário")
    st.write("ADMIN_SECRET usado para admin:", ADMIN_SECRET)  # Depuração
    with st.form("cadastro_form"):
        username = st.text_input("Nome de usuário")
        password = st.text_input("Senha", type="password")
        confirm_password = st.text_input("Confirmar senha", type="password")
        name = st.text_input("Nome completo")
        email = st.text_input("Email")
        phone = st.text_input("Telefone")
        address = st.text_input("Endereço")
        remember_me = st.checkbox("Manter conectado")
        admin_code = st.text_input("Código de Administrador (opcional)", type="password")
        submitted = st.form_submit_button("Cadastrar")

        if submitted:
            # Validações
            if not all([username, password, confirm_password, name, email, phone, address]):
                st.error("Por favor, preencha todos os campos.")
                return
            if password != confirm_password:
                st.error("As senhas não coincidem.")
                return
            if len(password) < 6:
                st.error("A senha deve ter pelo menos 6 caracteres.")
                return
            session = Session()
            existing_user = session.query(User).filter(
                (User.username == username) | (User.email == email)
            ).first()
            if existing_user:
                st.error("Nome de usuário ou email já cadastrado.")
                session.close()
                return
            try:
                password_hash = hash_pwd(password)
                is_admin = int(admin_code == ADMIN_SECRET)
                new_user = User(
                    username=username,
                    password=password_hash,
                    name=name,
                    email=email,
                    phone=phone,
                    address=address,
                    is_admin=is_admin
                )
                session.add(new_user)
                session.commit()
                if remember_me:
                    try:
                        cookie_value = create_auth_token(new_user.id)
                        cookie_manager.set(
                            "auth_token",
                            cookie_value,
                            max_age=36000,  # 10 horas
                            path="/",
                            secure=False   # True em produção
                        )
                        st.session_state['auth_token'] = cookie_value
                        st.session_state['logged_in'] = True
                        st.session_state['user_id'] = new_user.id
                        st.session_state['username'] = new_user.username
                        st.session_state['is_admin'] = new_user.is_admin
                        if new_user.is_admin:
                            st.session_state['current_page'] = "Agendamentos"
                        else:
                            st.session_state['current_page'] = "Home"
                    except Exception as e:
                        st.error(f"Erro ao criar token: {str(e)}")
                        st.session_state['current_page'] = "Login"
                else:
                    st.session_state['current_page'] = "Login"
                st.success("Cadastro realizado com sucesso!")
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao cadastrar: {str(e)}")
            finally:
                session.close()

# ---------- FUNÇÕES DE LOGIN ----------
def login_usuario():
    import extra_streamlit_components as stx
    cookie_manager = stx.CookieManager()
    st.title("Login de Usuário")
    with st.form("login_form"):
        username = st.text_input("Nome de usuário")
        password = st.text_input("Senha", type="password")
        remember_me = st.checkbox("Manter conectado")
        submitted = st.form_submit_button("Entrar")

        if submitted:
            if not username or not password:
                st.error("Por favor, preencha todos os campos.")
                return

            session = Session()
            user = session.query(User).filter_by(username=username).first()
            session.close()

            if user and check_pwd(user.password, password):
                if remember_me:
                    try:
                        cookie_value = create_auth_token(user.id)
                        cookie_manager.set(
                            "auth_token",
                            cookie_value,
                            max_age=36000,  # 10 horas
                            path="/",
                            secure=False   # True em produção
                        )
                        st.session_state['auth_token'] = cookie_value
                        st.session_state['logged_in'] = True
                        st.session_state['user_id'] = user.id
                        st.session_state['username'] = user.username
                        st.session_state['is_admin'] = False
                        st.success(f"Bem-vindo, {user.name}!")
                        st.session_state['current_page'] = "Home"
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao criar token: {str(e)}")
                else:
                    st.session_state['logged_in'] = True
                    st.session_state['user_id'] = user.id
                    st.session_state['username'] = user.username
                    st.session_state['is_admin'] = False
                    st.success(f"Bem-vindo, {user.name}!")
                    st.session_state['current_page'] = "Home"
                    st.rerun()
            else:
                st.error("Credenciais inválidas.")

def login_admin():
    import extra_streamlit_components as stx
    cookie_manager = stx.CookieManager()
    st.title("Login Administrativo")
    with st.form("admin_login_form"):
        username = st.text_input("Usuário Administrador")
        password = st.text_input("Senha", type="password")
        remember_me = st.checkbox("Manter conectado")
        submitted = st.form_submit_button("Entrar")

        if submitted:
            if not username or not password:
                st.error("Por favor, preencha todos os campos.")
                return

            session = Session()
            admin = session.query(User).filter_by(username=username, is_admin=True).first()
            session.close()

            if admin and check_pwd(admin.password, password):
                if remember_me:
                    try:
                        cookie_value = create_auth_token(admin.id)
                        cookie_manager.set(
                            "auth_token",
                            cookie_value,
                            max_age=36000,  # 10 horas
                            path="/",
                            secure=False   # True em produção
                        )
                        st.session_state['auth_token'] = cookie_value
                        st.session_state['logged_in'] = True
                        st.session_state['user_id'] = admin.id
                        st.session_state['username'] = admin.username
                        st.session_state['is_admin'] = True
                        st.success(f"Bem-vindo, {admin.username}! 🚀")
                        st.session_state['current_page'] = "Agendamentos"
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao criar token: {str(e)}")
                else:
                    st.session_state['logged_in'] = True
                    st.session_state['user_id'] = admin.id
                    st.session_state['username'] = admin.username
                    st.session_state['is_admin'] = True
                    st.success(f"Bem-vindo, {admin.username}! 🚀")
                    st.session_state['current_page'] = "Agendamentos"
                    st.rerun()
            else:
                st.error("Credenciais inválidas ou sem permissão de administrador.")

def logout():
    import extra_streamlit_components as stx
    cookie_manager = stx.CookieManager()
    cookie_value = cookie_manager.get("auth_token")
    if cookie_value is not None:
        cookie_manager.delete("auth_token")
    if 'auth_token' in st.session_state:
        logout_user(st.session_state['auth_token'])
        del st.session_state['auth_token']
    st.session_state['logged_in'] = False
    st.session_state['user_id'] = None
    st.session_state['username'] = None
    st.session_state['is_admin'] = False
    st.session_state['current_page'] = "Home"

# ---------- AUTENTICAÇÃO & PÁGINAS ADMIN ----------
def admin_agendamentos():
    st.subheader("Agendamentos")
    session = Session()
    agendamentos = (
        session.query(Appointment, User, Service)
        .join(User, Appointment.user_id == User.id)
        .join(Service, Appointment.service_id == Service.id)
        .order_by(
            Appointment.date, Appointment.time
        )
        .all()
    )
    usuarios = session.query(User).all()
    servicos = session.query(Service).filter_by(active=1).all()
    session.close()

    # Botão para novo agendamento
    if st.button("Novo Agendamento", key="novo_agendamento_admin"):
        st.session_state['edit_agendamento_id'] = None
        st.session_state['show_agendamento_form'] = True

    # Formulário de novo/edição de agendamento
    if st.session_state.get('show_agendamento_form', False):
        session = Session()
        agendamento = None
        if st.session_state.get('edit_agendamento_id'):
            agendamento = session.query(Appointment).filter_by(id=st.session_state['edit_agendamento_id']).first()
        st.markdown("### Formulário de Agendamento")
        with st.form("form_agendamento_admin"):
            user_options = {f"{u.name} ({u.email})": u.id for u in usuarios}
            service_options = {s.name: s.id for s in servicos}
            status_options = ["novo", "pendente", "confirmado", "feito", "não feito", "rejeitado"]
            user_id = st.selectbox("Cliente", options=list(user_options.keys()), index=list(user_options.values()).index(agendamento.user_id) if agendamento else 0)
            service_id = st.selectbox("Serviço", options=list(service_options.keys()), index=list(service_options.values()).index(agendamento.service_id) if agendamento else 0)
            date = st.date_input("Data", value=agendamento.date if agendamento and agendamento.date else datetime.now().date())
            time = st.time_input("Horário", value=agendamento.time if agendamento and agendamento.time else datetime.now().time().replace(second=0, microsecond=0))
            # Corrigir status para aceitar qualquer valor existente
            status_value = agendamento.status if agendamento and agendamento.status in status_options else status_options[0]
            status = st.selectbox("Status", options=status_options, index=status_options.index(status_value))
            address = st.text_input("Endereço", value=agendamento.address if agendamento else "")
            notes = st.text_area("Comentários", value=agendamento.notes if agendamento else "")
            submitted = st.form_submit_button("Salvar")
            if submitted:
                if agendamento:
                    agendamento.user_id = user_options[user_id]
                    agendamento.service_id = service_options[service_id]
                    agendamento.date = date
                    agendamento.time = time
                    agendamento.status = status
                    agendamento.address = address
                    agendamento.notes = notes
                else:
                    novo = Appointment(
                        user_id=user_options[user_id],
                        service_id=service_options[service_id],
                        date=date,
                        time=time,
                        status=status,
                        address=address,
                        notes=notes,
                        created_at=datetime.now().isoformat()
                    )
                    session.add(novo)
                session.commit()
                session.close()
                st.success("Agendamento salvo com sucesso!")
                st.session_state['show_agendamento_form'] = False
                st.session_state['edit_agendamento_id'] = None
                st.rerun()
        session.close()
        st.button("Cancelar", key="cancelar_form_agendamento", on_click=lambda: st.session_state.update({'show_agendamento_form': False, 'edit_agendamento_id': None}))
        st.markdown("---")

    if not agendamentos:
        st.info("Nenhum agendamento encontrado.")
        return

    # Estilo CSS para os cards
    st.markdown("""
        <style>
        .card {
            background-color: white;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 15px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        .card.confirmado {
            border-left: 5px solid #4CAF50;
        }
        .card.novo {
            border-left: 5px solid #2196F3;
        }
        .card.rejeitado {
            border-left: 5px solid #F44336;
        }
        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        .card-title {
            font-size: 1.2em;
            font-weight: bold;
            color: #333;
        }
        .card-status {
            padding: 5px 10px;
            border-radius: 15px;
            font-size: 0.9em;
            font-weight: bold;
        }
        .status-confirmado {
            background-color: #E8F5E9;
            color: #2E7D32;
        }
        .status-novo {
            background-color: #E3F2FD;
            color: #1565C0;
        }
        .status-rejeitado {
            background-color: #FFEBEE;
            color: #C62828;
        }
        .card-content {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 10px;
        }
        .card-item {
            margin-bottom: 5px;
        }
        .card-label {
            font-size: 0.8em;
            color: #666;
        }
        .card-value {
            font-size: 1em;
            color: #333;
        }
        </style>
    """, unsafe_allow_html=True)

    for _, (appointment, user, service) in enumerate(agendamentos):
        # Formatar data e hora para padrão brasileiro
        try:
            data_hora = datetime.strptime(f"{appointment.date} {appointment.time}", "%Y-%m-%d %H:%M")
            data_hora_br = data_hora.strftime("%d/%m/%Y %H:%M")
        except Exception:
            data_hora_br = f"{appointment.date} {appointment.time}"

        # Determinar a classe de status
        status_class = {
            'confirmado': 'status-confirmado',
            'rejeitado': 'status-rejeitado',
            'novo': 'status-novo'
        }.get(appointment.status, 'status-novo')

        # Determinar o texto do status
        status_text = {
            'confirmado': 'Confirmado',
            'rejeitado': 'Rejeitado',
            'novo': 'Em Análise'
        }.get(appointment.status, 'Em Análise')

        # Criar o card
        st.markdown(f"""
            <div class="card {appointment.status}">
                <div class="card-header">
                    <div class="card-title">#{appointment.id} - {service.name}</div>
                    <div class="card-status {status_class}">{status_text}</div>
                </div>
                <div class="card-content">
                    <div class="card-item">
                        <div class="card-label">Data e Hora</div>
                        <div class="card-value">{data_hora_br}</div>
                    </div>
                    <div class="card-item">
                        <div class="card-label">Endereço</div>
                        <div class="card-value">{appointment.address}</div>
                    </div>
                    <div class="card-item">
                        <div class="card-label">Cliente</div>
                        <div class="card-value">{user.name}</div>
                    </div>
                    <div class="card-item">
                        <div class="card-label">Telefone</div>
                        <div class="card-value">{user.phone}</div>
                    </div>
                    <div class="card-item">
                        <div class="card-label">Valor</div>
                        <div class="card-value">R$ {appointment.price:,.2f}</div>
                    </div>
                    {(f'<div class="card-item"><div class="card-label">Comentário do Administrador</div><div class="card-value">{appointment.notes}</div></div>' if appointment.notes else '')}
                </div>
            </div>
        """, unsafe_allow_html=True)

        # Exibir imagem se existir
        if appointment.image_path and isinstance(appointment.image_path, str) and appointment.image_path.strip() != "None":
            st.image(appointment.image_path, width=200, caption="Foto da piscina")

        # Botões de ação
        col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 2, 1])
        with col1:
            if appointment.status == 'novo':
                if st.button("Confirmar", key=f"conf_{appointment.id}"):
                    session = Session()
                    appt = session.query(Appointment).filter_by(id=appointment.id).first()
                    if appt:
                        appt.status = 'confirmado'
                        session.commit()
                    session.close()
                    st.success("Agendamento confirmado!")
                    st.rerun()
        with col2:
            if appointment.status == 'novo':
                if st.button("Rejeitar", key=f"rej_{appointment.id}"):
                    session = Session()
                    appt = session.query(Appointment).filter_by(id=appointment.id).first()
                    if appt:
                        appt.status = 'rejeitado'
                        session.commit()
                    session.close()
                    st.warning("Agendamento rejeitado!")
                    st.rerun()
        with col3:
            if st.button("🗑️ Deletar", key=f"del_{appointment.id}"):
                if st.session_state.get('confirm_delete') == appointment.id:
                    session = Session()
                    appt = session.query(Appointment).filter_by(id=appointment.id).first()
                    if appt:
                        session.delete(appt)
                        session.commit()
                    session.close()
                    st.error(f"Agendamento #{appointment.id} deletado com sucesso!")
                    st.session_state['confirm_delete'] = None
                    st.rerun()
                else:
                    st.session_state['confirm_delete'] = appointment.id
                    st.warning(f"Clique novamente em '🗑️ Deletar' para confirmar a exclusão do agendamento #{appointment.id}")
        with col4:
            if appointment.image_path and isinstance(appointment.image_path, str) and appointment.image_path.strip() != "None":
                st.image(appointment.image_path, width=200, caption="Foto da piscina")
        with col5:
            if st.button("Editar", key=f"edit_{appointment.id}"):
                st.session_state['edit_agendamento_id'] = appointment.id
                st.session_state['show_agendamento_form'] = True
                st.rerun()

def admin_services():
    st.subheader("Gerenciamento de Serviços")

    # Criar duas abas: Lista e Adicionar/Editar
    tab1, tab2 = st.tabs(["Lista de Serviços", "Adicionar/Editar Serviço"])

    with tab1:
        # Lista de serviços em formato de tabela
        session = Session()
        services = session.query(Service).all()

        if not services:
            st.info("Nenhum serviço cadastrado.")
        else:
            # Criar DataFrame para exibição
            df = pd.DataFrame({
                'ID': [s.id for s in services],
                'Nome': [s.name for s in services],
                'Descrição': [s.description for s in services],
                'Preço': [f'R$ {s.price:,.2f}'.replace(',', '_').replace('.', ',').replace('_', '.') for s in services],
                'Status': ['Ativo' if s.active else 'Inativo' for s in services]
            })

            # Exibir tabela
            st.dataframe(
                df,
                use_container_width=True,
                hide_index=True
            )

        session.close()

    with tab2:
        # Formulário para adicionar/editar serviço
        session = Session()

        # Selecionar serviço existente ou novo
        services_list = [s.name for s in session.query(Service).all()]
        services_list.insert(0, "Novo Serviço")
        selected_service = st.selectbox(
            "Selecione um serviço para editar ou 'Novo Serviço' para criar",
            options=services_list
        )

        # Campos do formulário
        if selected_service == "Novo Serviço":
            service = Service(
                name="",
                description="",
                price=0.0,
                active=1
            )
        else:
            service = session.query(Service).filter_by(name=selected_service).first()

        # Formulário
        with st.form("service_form"):
            col1, col2 = st.columns(2)

            with col1:
                name = st.text_input("Nome do Serviço", value=service.name)
                price = st.number_input(
                    "Preço (R$)",
                    min_value=0.0,
                    step=1.0,
                    value=float(service.price)
                )

            with col2:
                active = st.checkbox("Serviço Ativo", value=bool(service.active))
                description = st.text_area(
                    "Descrição",
                    value=service.description,
                    height=100
                )

            # Botões de ação
            col1, col2, col3 = st.columns(3)
            with col1:
                if st.form_submit_button("Salvar"):
                    if not name:
                        st.error("O nome do serviço é obrigatório!")
                    else:
                        service.name = name
                        service.description = description
                        service.price = price
                        service.active = int(active)

                        if selected_service == "Novo Serviço":
                            session.add(service)

                        session.commit()
                        st.success("Serviço salvo com sucesso!")
                        st.rerun()

            with col2:
                if st.form_submit_button("Cancelar"):
                    st.rerun()

            with col3:
                if selected_service != "Novo Serviço" and st.form_submit_button("Excluir"):
                    session.delete(service)
                    session.commit()
                    st.success("Serviço excluído com sucesso!")
                    st.rerun()

        session.close()

def admin_config():
    st.subheader("Configurar Limites Diários")

    # Dias da semana em português
    dias_semana = ['Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']

    # Criar ou atualizar configurações para cada dia
    session = Session()
    for dia in range(7):
        config = session.query(Config).filter_by(weekday=dia).first()

        # Se não existir configuração para este dia, criar uma nova
        if not config:
            config = Config(weekday=dia, max_appointments=5)
            session.add(config)

        # Interface para edição
        col1, col2 = st.columns([1, 3])
        with col1:
            st.markdown(f"**{dias_semana[dia]}**")
        with col2:
            novo_limite = st.number_input(
                "Limite de agendamentos",
                min_value=0,
                value=config.max_appointments,
                key=f"limite_{dia}"
            )
            config.max_appointments = novo_limite

    # Botão para salvar todas as alterações
    if st.button("Salvar Configurações"):
        session.commit()
        st.success("Limites atualizados com sucesso!")

    session.close()

def admin_gallery():
    st.subheader("Galeria Antes & Depois")
    with st.expander("Adicionar Par de Fotos"):
        before = st.file_uploader("Imagem Antes", type=['png','jpg'], key="bef")
        after = st.file_uploader("Imagem Depois", type=['png','jpg'], key="aft")
        cap = st.text_input("Legenda")
        if st.button("Adicionar"):
            if before and after and cap:
                os.makedirs("gallery", exist_ok=True)
                before_path = os.path.join("gallery", before.name)
                after_path = os.path.join("gallery", after.name)
                with open(before_path, "wb") as f:
                    f.write(before.getbuffer())
                with open(after_path, "wb") as f:
                    f.write(after.getbuffer())
                session = Session()
                new_gallery = Gallery(
                    before_path=before_path,
                    after_path=after_path,
                    caption=cap
                )
                session.add(new_gallery)
                session.commit()
                session.close()
                st.success("Fotos adicionadas à galeria!")
            else:
                st.error("Preencha todos os campos!")

def admin_database():
    """Interface administrativa para gerenciamento do banco de dados."""
    st.title("Gerenciamento do Banco de Dados")

    # Verificar se o usuário é administrador
    if not st.session_state.get('is_admin', False):
        st.error("Acesso negado. Esta página é restrita a administradores.")
        return

    # Informações do banco de dados
    st.subheader("Informações do Banco de Dados")

    # Obter informações do Alembic
    alembic_cfg = alembic.config.Config("alembic.ini")
    script = ScriptDirectory.from_config(alembic_cfg)

    with EnvironmentContext(
        alembic_cfg,
        script,
        fn=lambda rev, _: script.get_revisions(rev)
    ) as env:
        env.configure(connection=engine.connect(), target_metadata=Base.metadata)
        context = env.get_context()
        current_rev = context.get_current_revision()

    head_rev = script.get_current_head()

    st.info(f"Revisão atual: {current_rev}")
    st.info(f"Revisão mais recente disponível: {head_rev}")

    if current_rev != head_rev:
        st.warning("O banco de dados não está na versão mais recente.")
        if st.button("Atualizar para a versão mais recente"):
            # Criar backup antes de atualizar
            backup_file = backup_db()
            if backup_file:
                st.success(f"Backup criado: {os.path.basename(backup_file)}")

                try:
                    # Executar migrações
                    command.upgrade(alembic_cfg, "head")
                    st.success("Banco de dados atualizado com sucesso!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao atualizar o banco de dados: {str(e)}")

    # Histórico de migrações
    st.subheader("Histórico de Migrações")

    history = []
    for rev in script.walk_revisions():
        history.append({
            "revision": rev.revision,
            "down_revision": rev.down_revision,
            "description": rev.doc,
            "is_current": rev.revision == current_rev
        })

    # Exibir histórico em ordem cronológica
    for rev_info in reversed(history):
        status = "✅ (atual)" if rev_info["is_current"] else "✅" if rev_info["revision"] < current_rev else "⏳"
        st.markdown(f"**{status} {rev_info['revision']}**: {rev_info['description']}")

    # Backup e restauração
    st.subheader("Backup e Restauração")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Criar Backup Manual"):
            backup_file = backup_db()
            if backup_file:
                st.success(f"Backup criado com sucesso: {os.path.basename(backup_file)}")

    # Listar backups disponíveis
    backup_dir = os.path.join(os.path.dirname(DB_PATH), "backups")
    if os.path.exists(backup_dir):
        backups = sorted([f for f in os.listdir(backup_dir) if f.startswith("db_backup_")])

        if backups:
            st.subheader("Backups Disponíveis")
            selected_backup = st.selectbox("Selecione um backup para restaurar:", backups)

            if st.button("Restaurar Backup Selecionado"):
                if "confirm_restore" not in st.session_state:
                    st.session_state["confirm_restore"] = False

                if not st.session_state["confirm_restore"]:
                    st.warning("⚠️ ATENÇÃO: A restauração substituirá todos os dados atuais. Esta ação não pode ser desfeita.")
                    if st.button("Confirmar Restauração"):
                        st.session_state["confirm_restore"] = True
                        backup_path = os.path.join(backup_dir, selected_backup)

                        # Fechar todas as conexões
                        if engine:
                            engine.dispose()

                        # Restaurar o backup
                        shutil.copy2(backup_path, DB_PATH)
                        st.success("Backup restaurado com sucesso! O aplicativo será reiniciado.")
                        st.rerun()

    # Operações avançadas do Alembic
    st.subheader("Operações Avançadas")

    # Downgrade para uma revisão específica
    st.markdown("#### Downgrade para Revisão Específica")
    st.warning("⚠️ Esta operação pode resultar em perda de dados. Use com cautela.")

    target_revisions = [(rev.revision, rev.doc) for rev in script.walk_revisions()]
    target_options = [f"{rev[0]}: {rev[1]}" for rev in target_revisions]

    selected_target = st.selectbox("Selecione a revisão alvo:", target_options)
    target_rev = selected_target.split(":")[0].strip() if selected_target else None

    if target_rev and st.button("Executar Downgrade"):
        if "confirm_downgrade" not in st.session_state:
            st.session_state["confirm_downgrade"] = False

        if not st.session_state["confirm_downgrade"]:
            st.error("⚠️ ATENÇÃO: O downgrade pode resultar em perda permanente de dados. Esta ação não pode ser desfeita.")
            if st.button("Confirmar Downgrade"):
                st.session_state["confirm_downgrade"] = True

                # Criar backup antes do downgrade
                backup_file = backup_db()
                if backup_file:
                    st.success(f"Backup criado: {os.path.basename(backup_file)}")

                    try:
                        # Executar downgrade
                        command.downgrade(alembic_cfg, target_rev)
                        st.success(f"Banco de dados revertido para a revisão {target_rev}!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao reverter o banco de dados: {str(e)}")

def detectar_dispositivo():
    """Detecta o tipo de dispositivo que está acessando o aplicativo"""
    user_agent = st.session_state.get('user_agent', '')

    # Detectar dispositivo móvel
    if 'Mobile' in user_agent or 'Android' in user_agent or 'iPhone' in user_agent:
        return 'mobile'
    # Detectar tablet
    elif 'iPad' in user_agent or 'Tablet' in user_agent:
        return 'tablet'
    # Se não for nenhum dos acima, considera como desktop
    else:
        return 'desktop'

def meus_agendamentos():
    st.title("Meus Agendamentos")

    # Obter agendamentos do usuário
    session = Session()
    agendamentos = (
        session.query(Appointment, Service)
        .join(Service, Appointment.service_id == Service.id)
        .filter(Appointment.user_id == st.session_state['user_id'])
        .order_by(Appointment.date.desc(), Appointment.time.desc())
        .all()
    )
    session.close()

    if not agendamentos:
        st.info("Você ainda não tem agendamentos.")
        return

    # Estilo CSS para os cards
    st.markdown("""
        <style>
        .card {
            background-color: white;
            border-radius: 10px;
            padding: 20px;
            margin-bottom: 15px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        .card.confirmado {
            border-left: 5px solid #4CAF50;
        }
        .card.novo {
            border-left: 5px solid #2196F3;
        }
        .card.rejeitado {
            border-left: 5px solid #F44336;
        }
        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }
        .card-title {
            font-size: 1.2em;
            font-weight: bold;
            color: #333;
        }
        .card-status {
            padding: 5px 10px;
            border-radius: 15px;
            font-size: 0.9em;
            font-weight: bold;
        }
        .status-confirmado {
            background-color: #E8F5E9;
            color: #2E7D32;
        }
        .status-novo {
            background-color: #E3F2FD;
            color: #1565C0;
        }
        .status-rejeitado {
            background-color: #FFEBEE;
            color: #C62828;
        }
        .card-content {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 10px;
        }
        .card-item {
            margin-bottom: 5px;
        }
        .card-label {
            font-size: 0.8em;
            color: #666;
        }
        .card-value {
            font-size: 1em;
            color: #333;
        }
        </style>
    """, unsafe_allow_html=True)

    for _, (appointment, service) in enumerate(agendamentos):
        # Obter dados do usuário relacionado ao agendamento
        session = Session()
        user = session.query(User).filter_by(id=appointment.user_id).first()
        session.close()

        # Formatar data e hora para padrão brasileiro
        try:
            data_hora = datetime.strptime(f"{appointment.date} {appointment.time}", "%Y-%m-%d %H:%M")
            data_hora_br = data_hora.strftime("%d/%m/%Y %H:%M")
        except Exception:
            data_hora_br = f"{appointment.date} {appointment.time}"

        # Determinar a classe de status
        status_class = {
            'confirmado': 'status-confirmado',
            'rejeitado': 'status-rejeitado',
            'novo': 'status-novo'
        }.get(appointment.status, 'status-novo')

        # Determinar o texto do status
        status_text = {
            'confirmado': 'Confirmado',
            'rejeitado': 'Rejeitado',
            'novo': 'Em Análise'
        }.get(appointment.status, 'Em Análise')

        # Criar o card
        st.markdown(f"""
            <div class="card {appointment.status}">
                <div class="card-header">
                    <div class="card-title">#{appointment.id} - {service.name}</div>
                    <div class="card-status {status_class}">{status_text}</div>
                </div>
                <div class="card-content">
                    <div class="card-item">
                        <div class="card-label">Data e Hora</div>
                        <div class="card-value">{data_hora_br}</div>
                    </div>
                    <div class="card-item">
                        <div class="card-label">Endereço</div>
                        <div class="card-value">{appointment.address}</div>
                    </div>
                    <div class="card-item">
                        <div class="card-label">Contato</div>
                        <div class="card-value">{user.phone}</div>
                    </div>
                    {(f'<div class="card-item"><div class="card-label">Comentário do Administrador</div><div class="card-value">{appointment.notes}</div></div>' if appointment.notes else '')}
                </div>
            </div>
        """, unsafe_allow_html=True)

        # Exibir imagem se existir
        if appointment.image_path and isinstance(appointment.image_path, str) and appointment.image_path.strip() != "None":
            st.image(appointment.image_path, width=200, caption="Foto da piscina")

# Função para checar autenticação por cookie
def check_authentication():
    import extra_streamlit_components as stx
    cookie_manager = stx.CookieManager()
    cookie_value = cookie_manager.get("auth_token")
    user_id = validate_auth_token(cookie_value) if cookie_value else None
    if user_id:
        st.session_state['logged_in'] = True
        st.session_state['user_id'] = user_id
        st.session_state['auth_token'] = cookie_value
    else:
        st.session_state['logged_in'] = False
        st.session_state['user_id'] = None
        st.session_state.pop('auth_token', None)

# --- Página de administração de usuários ---
def admin_usuarios():
    st.subheader("Gerenciamento de Usuários")
    session = Session()

    # --- Formulário para criar novo usuário ---
    with st.expander("Cadastrar novo usuário"):
        new_username = st.text_input("Novo nome de usuário", key="admin_new_username")
        new_password = st.text_input("Nova senha", type="password", key="admin_new_password")
        new_name = st.text_input("Nome completo", key="admin_new_name")
        new_email = st.text_input("Email", key="admin_new_email")
        new_phone = st.text_input("Telefone", key="admin_new_phone")
        new_address = st.text_input("Endereço", key="admin_new_address")
        new_is_admin = st.checkbox("Administrador?", key="admin_new_is_admin")
        if st.button("Criar usuário", key="admin_create_user"):
            if not all([new_username, new_password, new_name, new_email]):
                st.error("Preencha todos os campos obrigatórios!")
            elif session.query(User).filter((User.username == new_username) | (User.email == new_email)).first():
                st.error("Nome de usuário ou email já cadastrado.")
            else:
                password_hash = hash_pwd(new_password)
                novo = User(
                    username=new_username,
                    password=password_hash,
                    name=new_name,
                    email=new_email,
                    phone=new_phone,
                    address=new_address,
                    is_admin=new_is_admin
                )
                session.add(novo)
                session.commit()
                st.success("Usuário criado com sucesso!")
                st.experimental_rerun()

    # --- Tabela e gerenciamento de usuários ---
    usuarios = session.query(User).all()
    df = pd.DataFrame([{
        "ID": u.id,
        "Usuário": u.username,
        "Nome": u.name,
        "Email": u.email,
        "Telefone": u.phone,
        "Admin": "Sim" if u.is_admin else "Não"
    } for u in usuarios])

    st.dataframe(df, use_container_width=True, hide_index=True)

    # Seleção para editar/promover/remover
    user_ids = [u.id for u in usuarios]
    user_names = [f"{u.name} ({u.username})" for u in usuarios]
    if not user_names:
        st.info("Nenhum usuário cadastrado.")
        session.close()
        return
    selected = st.selectbox("Selecione um usuário para gerenciar", user_names)
    user = usuarios[user_names.index(selected)]

    st.markdown(f"**Usuário:** {user.username} | **Admin:** {'Sim' if user.is_admin else 'Não'}")

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("Promover a Admin", disabled=user.is_admin):
            user.is_admin = True
            session.commit()
            st.success("Usuário promovido a administrador!")
            st.rerun()
    with col2:
        if st.button("Remover Admin", disabled=not user.is_admin):
            user.is_admin = False
            session.commit()
            st.success("Permissão de administrador removida!")
            st.rerun()
    with col3:
        if st.button("Excluir Usuário"):
            session.delete(user)
            session.commit()
            st.success("Usuário excluído!")
            st.rerun()

    session.close()

# ---------- FUNÇÃO PRINCIPAL ----------
def main():
    # Inicializar banco de dados
    init_db()

    # Verificar autenticação por cookie no início
    if 'logged_in' not in st.session_state:
        check_authentication()

    # Configuração inicial
    if 'current_page' not in st.session_state:
        st.session_state['current_page'] = "Home"
    if 'user_id' not in st.session_state:
        st.session_state['user_id'] = None
    if 'username' not in st.session_state:
        st.session_state['username'] = None
    if 'is_admin' not in st.session_state:
        st.session_state['is_admin'] = False

    # Verificar token de autenticação
    if 'auth_token' in st.session_state:
        try:
            user_id = validate_auth_token(st.session_state['auth_token'])
            if user_id:
                session = Session()
                user = session.query(User).filter_by(id=user_id).first()
                session.close()

                if user:
                    st.session_state['logged_in'] = True
                    st.session_state['user_id'] = user.id
                    st.session_state['username'] = user.username
                    st.session_state['is_admin'] = user.is_admin
                    if user.is_admin:
                        st.session_state['current_page'] = "Agendamentos"
                    else:
                        st.session_state['current_page'] = "Home"
        except Exception as e:
            st.error(f"Erro ao validar token: {str(e)}")
            logout()

    # Menu lateral
    with st.sidebar:
        # Definir menu_items padrão
        menu_items = {
            "Home": homepage,
            "Área de Cobertura": mapa_tempo,
            "Contato": contato,
            "Galeria": admin_gallery
        }

        # Exibir informações do usuário logado
        if st.session_state.get('logged_in'):
            usuario = st.session_state.get('username', 'Usuário')
            admin = st.session_state.get('is_admin', False)
            tipo = "Administrador" if admin else "Usuário"
            device = detectar_dispositivo()
            st.markdown(f"""
            <div style='padding:10px; border-radius:8px; background:#222; margin-bottom:10px; color:#fff;'>
                <b>Logado como:</b> {usuario}<br>
                <b>Tipo:</b> {tipo}<br>
                <b>Dispositivo:</b> {device}
            </div>
            """, unsafe_allow_html=True)

        # Atualizar menu_items baseado no tipo de usuário
        if st.session_state['logged_in']:
            if st.session_state['is_admin']:
                menu_items = {
                    "Agendamentos": admin_agendamentos,
                    "Serviços": admin_services,
                    "Configurações": admin_config,
                    "Galeria": admin_gallery,
                    "Banco de Dados": admin_database,
                    "Usuários": admin_usuarios
                }
            else:
                menu_items = {
                    "Home": homepage,
                    "Área de Cobertura": mapa_tempo,
                    "Contato": contato,
                    "Meus Agendamentos": meus_agendamentos,
                    "Galeria": admin_gallery
                }
        else:
            menu_items = {
                "Home": homepage,
                "Área de Cobertura": mapa_tempo,
                "Contato": contato,
                "Galeria": admin_gallery,
                "Login": login_usuario,
                "Login Administrativo": login_admin,
                "Cadastro": cadastro
            }

        # Garantir que current_page é válido
        if 'current_page' not in st.session_state or st.session_state['current_page'] not in menu_items:
            st.session_state['current_page'] = list(menu_items.keys())[0]

        # Menu e botão logout SEM esconder o selectbox
        selected = st.selectbox(
            "Menu",
            list(menu_items.keys()),
            index=list(menu_items.keys()).index(st.session_state['current_page'])
        )
        if selected != st.session_state['current_page']:
            st.session_state['current_page'] = selected

        if st.session_state['logged_in'] and st.button("Logout"):
            logout()
            st.rerun()

        # Painel de debug para desenvolvimento
        if ENVIRONMENT == "development":
            st.markdown("---")
            st.markdown("### [DEBUG] Informações do Sistema")
            st.write("Usuário logado:", st.session_state.get('username'))
            st.write("ID do usuário:", st.session_state.get('user_id'))
            st.write("Admin:", st.session_state.get('is_admin'))
            st.write("Token:", st.session_state.get('auth_token'))
            st.write("Ambiente:", ENVIRONMENT)
            st.write("DB_PATH:", DB_PATH)
            st.write("User-Agent:", st.session_state.get('user_agent'))
            try:
                st.write("Feature Flags:", feature_flags.flags)
            except Exception:
                st.write("Feature Flags: erro ao acessar")

    # Sempre renderiza a página atual
    if st.session_state['current_page'] in menu_items:
        menu_items[st.session_state['current_page']]()

if __name__ == "__main__":
    main()
