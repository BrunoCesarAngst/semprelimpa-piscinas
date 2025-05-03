import streamlit as st
from streamlit_folium import folium_static
import folium
import pandas as pd
import requests
from datetime import datetime
import os
import urllib.parse
import webbrowser
from migrations import run_migrations
from feature_flags import feature_flags
from db_utils import get_db_connection, hash_pwd, check_pwd
from dotenv import load_dotenv

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# ---------- CONFIGURAÇÕES ----------
# Configuração do banco de dados baseada no ambiente
ENVIRONMENT = os.getenv('ENVIRONMENT', 'production')
DB_PATH = os.path.join('data', f'database_{ENVIRONMENT}.db')

# Configurações do ambiente
if os.getenv('TESTING', 'false').lower() == 'true':
    # Modo de teste - usar variáveis de ambiente
    WEATHER_API_KEY = os.getenv('WEATHER_API_KEY', 'test_key')
    WHATSAPP_LINK = os.getenv('WHATSAPP_LINK', 'https://wa.me/test')
else:
    # Modo normal - usar secrets do Streamlit
    WEATHER_API_KEY = st.secrets["WEATHER_API_KEY"]
    WHATSAPP_LINK = st.secrets["WHATSAPP_LINK"]

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

    if feature_flags.is_enabled('GALERIA_FOTOS'):
        st.header("Antes & Depois")
        conn = get_db_connection()
        gallery = conn.execute("SELECT * FROM gallery").fetchall()
        conn.close()
        for item in gallery:
            cols = st.columns(2)
            cols[0].image(item['before_path'], caption=item['caption'] + " (Antes)")
            cols[1].image(item['after_path'], caption=item['caption'] + " (Depois)")

    st.header("Serviços")
    conn = get_db_connection()
    services = conn.execute("SELECT * FROM services WHERE active=1").fetchall()
    conn.close()
    for srv in services:
        st.subheader(srv['name'])
        st.write(srv['description'])

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

    if feature_flags.is_enabled('NOVO_SISTEMA_AGENDAMENTO'):
        # Novo sistema de agendamento
        novo_sistema_agendamento()
    else:
        # Sistema antigo de agendamento
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
    conn = get_db_connection()
    services = conn.execute("SELECT id, name, price FROM services WHERE active=1").fetchall()
    conn.close()

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
    conn = get_db_connection()
    wd = date.weekday()
    max_appt = conn.execute("SELECT max_appointments FROM config WHERE weekday=?", (wd,)).fetchone()[0]
    count = conn.execute("SELECT COUNT(*) FROM appointments WHERE date=?", (date.isoformat(),)).fetchone()[0]
    conn.close()

    if max_appt and count >= max_appt:
        st.error("Dia cheio, escolha outra data.")
        return

    # Seleção de serviço
    st.subheader("Selecione o serviço")
    svc_dict = {s['name']: (s['id'], s['price']) for s in services}
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
        conn = get_db_connection()
        user = conn.execute("SELECT name, phone, address FROM users WHERE id = ?",
                          (st.session_state['user_id'],)).fetchone()
        conn.close()

        name = st.text_input("Nome", value=user['name'])
        contact = st.text_input("Telefone", value=user['phone'])
        address = st.text_input("Endereço da piscina", value=user['address'])
        image = st.file_uploader("Foto da piscina (opcional)", type=['png','jpg','jpeg'])
        submitted = st.form_submit_button("Confirmar Agendamento")

        if submitted:
            img_path = None
            if image:
                os.makedirs("uploads", exist_ok=True)
                img_path = os.path.join("uploads", image.name)
                with open(img_path, "wb") as f:
                    f.write(image.getbuffer())

            conn = get_db_connection()
            conn.execute(
                "INSERT INTO appointments (name, contact, address, date, time, service_id, status, image_path, user_id) VALUES (?,?,?,?,?,?,?,?,?)",
                (name, contact, address, date.isoformat(), time.strftime("%H:%M"), service_id, 'novo', img_path, st.session_state['user_id'])
            )
            conn.commit()

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
    conn = get_db_connection()
    services = conn.execute("SELECT id, name, price FROM services WHERE active=1").fetchall()
    conn.close()

    if not services:
        st.warning("No momento não temos serviços disponíveis para agendamento. Por favor, entre em contato conosco pelo WhatsApp.")
        wa_link = WHATSAPP_LINK
        st.markdown(
            f"<a href='{wa_link}' target='_blank'><img src='https://cdn-icons-png.flaticon.com/512/733/733585.png' width='24'/> Fale conosco pelo WhatsApp</a>",
            unsafe_allow_html=True
        )
        return

    svc_dict = {s['name']: (s['id'], s['price']) for s in services}

    # Selectbox para escolher o serviço (fora do formulário)
    svc = st.selectbox("Serviço", options=list(svc_dict.keys()))
    service_id, price = svc_dict[svc]
    st.markdown(f"**Valor do serviço:** R$ {price:,.2f}".replace(',', '_').replace('.', ',').replace('_', '.'))

    with st.form("orcamento"):
        # Obter dados do usuário logado
        conn = get_db_connection()
        user = conn.execute("SELECT name, phone, address FROM users WHERE id = ?",
                          (st.session_state['user_id'],)).fetchone()
        conn.close()

        name = st.text_input("Nome", value=user['name'])
        contact = st.text_input("Telefone", value=user['phone'])
        address = st.text_input("Endereço da piscina", value=user['address'])
        date = st.date_input("Data desejada", format="DD/MM/YYYY")
        time = st.time_input("Horário desejado")
        image = st.file_uploader("Foto da piscina (opcional)", type=['png','jpg','jpeg'])
        submitted = st.form_submit_button("Enviar")

        if submitted:
            wd = date.weekday()
            conn = get_db_connection()
            max_appt = conn.execute("SELECT max_appointments FROM config WHERE weekday=?", (wd,)).fetchone()[0]
            count = conn.execute("SELECT COUNT(*) FROM appointments WHERE date=?", (date.isoformat(),)).fetchone()[0]

            if max_appt and count >= max_appt:
                st.error("Dia cheio, escolha outra data.")
            else:
                img_path = None
                if image:
                    os.makedirs("uploads", exist_ok=True)
                    img_path = os.path.join("uploads", image.name)
                    with open(img_path, "wb") as f:
                        f.write(image.getbuffer())
                conn.execute(
                    "INSERT INTO appointments (name, contact, address, date, time, service_id, status, image_path, user_id) VALUES (?,?,?,?,?,?,?,?,?)",
                    (name, contact, address, date.isoformat(), time.strftime("%H:%M"), service_id, 'novo', img_path, st.session_state['user_id'])
                )
                st.success("Recebemos seu pedido! Entraremos em contato em breve.")
            conn.close()

def cadastro():
    st.title("Cadastro de Usuário")

    with st.form("cadastro_form"):
        username = st.text_input("Nome de usuário")
        password = st.text_input("Senha", type="password")
        confirm_password = st.text_input("Confirmar senha", type="password")
        name = st.text_input("Nome completo")
        email = st.text_input("Email")
        phone = st.text_input("Telefone")
        address = st.text_input("Endereço")

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

            # Verificar se o usuário já existe
            conn = get_db_connection()
            existing_user = conn.execute("SELECT id FROM users WHERE username = ? OR email = ?",
                                       (username, email)).fetchone()
            if existing_user:
                st.error("Nome de usuário ou email já cadastrado.")
                conn.close()
                return

            # Criar novo usuário
            try:
                password_hash = hash_pwd(password)
                conn.execute("""
                    INSERT INTO users (username, password_hash, name, email, phone, address)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (username, password_hash, name, email, phone, address))
                conn.commit()
                st.success("Cadastro realizado com sucesso! Faça login para continuar.")
                st.session_state['current_page'] = "Login"
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao cadastrar: {str(e)}")
            finally:
                conn.close()

def login_usuario():
    st.title("Login de Usuário")

    with st.form("login_form"):
        username = st.text_input("Nome de usuário")
        password = st.text_input("Senha", type="password")
        submitted = st.form_submit_button("Entrar")

        if submitted:
            if not username or not password:
                st.error("Por favor, preencha todos os campos.")
                return

            conn = get_db_connection()
            user = conn.execute("""
                SELECT id, username, password_hash, name, email, phone, address
                FROM users
                WHERE username = ? AND is_dev = 0
            """, (username,)).fetchone()
            conn.close()

            if user and check_pwd(user['password_hash'], password):
                st.session_state['logged_in'] = True
                st.session_state['user_id'] = user['id']
                st.session_state['username'] = user['username']
                st.session_state['is_admin'] = False
                st.success(f"Bem-vindo, {user['name']}!")
                st.session_state['current_page'] = "Home"
                st.rerun()
            else:
                st.error("Credenciais inválidas.")

def login_admin():
    st.title("Login Administrativo")

    with st.form("admin_login_form"):
        username = st.text_input("Usuário Administrador")
        password = st.text_input("Senha", type="password")
        submitted = st.form_submit_button("Entrar")

        if submitted:
            if not username or not password:
                st.error("Por favor, preencha todos os campos.")
                return

            conn = get_db_connection()
            admin = conn.execute("""
                SELECT id, username, password_hash, name, is_dev
                FROM users
                WHERE username = ? AND is_dev = 1
            """, (username,)).fetchone()
            conn.close()

            if admin and check_pwd(admin['password_hash'], password):
                st.session_state['logged_in'] = True
                st.session_state['user_id'] = admin['id']
                st.session_state['username'] = admin['username']
                st.session_state['is_admin'] = True
                st.success(f"Bem-vindo, {admin['name']}! 🚀")
                st.session_state['current_page'] = "Agendamentos"
                st.rerun()
            else:
                st.error("Credenciais inválidas ou sem permissão de administrador.")

# ---------- AUTENTICAÇÃO & PÁGINAS ADMIN ----------
def admin_agendamentos():
    st.subheader("Agendamentos")
    conn = get_db_connection()
    df = pd.read_sql("""
        SELECT a.id, a.name, a.contact, a.address, a.date, a.time, s.name as service, a.status, a.image_path
        FROM appointments a
        JOIN services s ON a.service_id=s.id
        ORDER BY
            CASE WHEN a.status = 'confirmado' THEN 0
                 WHEN a.status = 'rejeitado' THEN 2
                 ELSE 1 END,
            a.date,
            a.time
    """, conn)
    conn.close()

    if df.empty:
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

    for _, row in df.iterrows():
        # Formatar data e hora para padrão brasileiro
        try:
            data_hora = datetime.strptime(f"{row['date']} {row['time']}", "%Y-%m-%d %H:%M")
            data_hora_br = data_hora.strftime("%d/%m/%Y %H:%M")
        except Exception:
            data_hora_br = f"{row['date']} {row['time']}"

        # Determinar a classe de status
        status_class = {
            'confirmado': 'status-confirmado',
            'rejeitado': 'status-rejeitado',
            'novo': 'status-novo'
        }.get(row['status'], 'status-novo')

        # Criar o card
        st.markdown(f"""
            <div class="card {row['status']}">
                <div class="card-header">
                    <div class="card-title">#{row['id']} - {row['name']}</div>
                    <div class="card-status {status_class}">{row['status'].capitalize()}</div>
                </div>
                <div class="card-content">
                    <div class="card-item">
                        <div class="card-label">Contato</div>
                        <div class="card-value">{row['contact']}</div>
                    </div>
                    <div class="card-item">
                        <div class="card-label">Endereço</div>
                        <div class="card-value">{row['address']}</div>
                    </div>
                    <div class="card-item">
                        <div class="card-label">Data e Hora</div>
                        <div class="card-value">{data_hora_br}</div>
                    </div>
                    <div class="card-item">
                        <div class="card-label">Serviço</div>
                        <div class="card-value">{row['service']}</div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        # Botões de ação e imagem (se existir)
        col1, col2, col3, col4 = st.columns([1, 1, 1, 2])
        with col1:
            if row['status'] == 'novo':
                if st.button("Confirmar", key=f"conf_{row['id']}"):
                    conn = get_db_connection()
                    conn.execute("UPDATE appointments SET status='confirmado' WHERE id=?", (row['id'],))
                    conn.commit()
                    conn.close()
                    st.success("Agendamento confirmado!")
                    st.rerun()
        with col2:
            if row['status'] == 'novo':
                if st.button("Rejeitar", key=f"rej_{row['id']}"):
                    conn = get_db_connection()
                    conn.execute("UPDATE appointments SET status='rejeitado' WHERE id=?", (row['id'],))
                    conn.commit()
                    conn.close()
                    st.warning("Agendamento rejeitado!")
                    st.rerun()
        with col3:
            if st.button("🗑️ Deletar", key=f"del_{row['id']}"):
                # Confirmar a exclusão
                if st.session_state.get('confirm_delete') == row['id']:
                    conn = get_db_connection()
                    conn.execute("DELETE FROM appointments WHERE id=?", (row['id'],))
                    conn.commit()
                    conn.close()
                    st.error(f"Agendamento #{row['id']} deletado com sucesso!")
                    st.session_state['confirm_delete'] = None
                    st.rerun()
                else:
                    st.session_state['confirm_delete'] = row['id']
                    st.warning(f"Clique novamente em '🗑️ Deletar' para confirmar a exclusão do agendamento #{row['id']}")
        with col4:
            if row['image_path'] and isinstance(row['image_path'], str) and row['image_path'].strip() != "None":
                st.image(row['image_path'], width=200, caption="Foto da piscina")

def admin_services():
    st.subheader("Gerenciamento de Serviços")

    # Tabela de serviços
    conn = get_db_connection()
    df = pd.read_sql("SELECT id, name, description, price, active FROM services", conn)
    conn.close()

    # Renomear colunas para português
    df = df.rename(columns={
        'id': 'ID',
        'name': 'Nome',
        'description': 'Descrição',
        'price': 'Preço (R$)',
        'active': 'Ativo'
    })

    # Converter valores booleanos para Sim/Não
    df['Ativo'] = df['Ativo'].map({1: 'Sim', 0: 'Não'})

    # Formatar preço como moeda brasileira
    df['Preço (R$)'] = df['Preço (R$)'].map(lambda x: f'R$ {x:,.2f}'.replace(',', '_').replace('.', ',').replace('_', '.'))

    # Exibir tabela
    st.dataframe(df, use_container_width=True)

    # Formulário de edição
    with st.expander("Adicionar/Editar Serviço"):
        # Selecionar serviço existente para edição
        services_list = df['Nome'].tolist()
        services_list.insert(0, "Novo Serviço")
        selected_service = st.selectbox("Selecione um serviço para editar ou 'Novo Serviço' para criar", options=services_list)

        if selected_service == "Novo Serviço":
            sid = 0
            name = ""
            desc = ""
            price = 0.0
            active = True
        else:
            conn = get_db_connection()
            service = conn.execute(
                "SELECT id, name, description, price, active FROM services WHERE name=?",
                (selected_service,)
            ).fetchone()
            conn.close()

            sid = service['id']
            name = service['name']
            desc = service['description']
            price = service['price']
            active = bool(service['active'])

        # Campos do formulário
        name = st.text_input("Nome do Serviço", value=name)
        desc = st.text_area("Descrição", value=desc)
        price = st.number_input("Preço (R$)", min_value=0.0, step=1.0, value=price)
        active = st.checkbox("Serviço Ativo", value=active)

        if st.button("Salvar Serviço"):
            if not name or not desc:
                st.error("Nome e descrição são obrigatórios!")
            else:
                conn = get_db_connection()
                if sid:
                    conn.execute(
                        "UPDATE services SET name=?, description=?, price=?, active=? WHERE id=?",
                        (name, desc, price, int(active), sid)
                    )
                else:
                    conn.execute(
                        "INSERT INTO services (name, description, price, active) VALUES (?,?,?,?)",
                        (name, desc, price, int(active))
                    )
                conn.commit()
                conn.close()
                st.success("Serviço salvo com sucesso!")
                st.rerun()

def admin_config():
    st.subheader("Configurar Limites Diários")
    conn = get_db_connection()
    cfg = conn.execute("SELECT * FROM config ORDER BY weekday").fetchall()
    for row in cfg:
        wd_name = ['Seg','Ter','Qua','Qui','Sex','Sáb','Dom'][row['weekday']]
        val = st.number_input(f"{wd_name}", min_value=0, value=row['max_appointments'], key=f"cfg_{row['weekday']}")
        conn.execute("UPDATE config SET max_appointments=? WHERE weekday=?", (val, row['weekday']))
    conn.commit()
    conn.close()
    if st.button("Salvar Configurações"):
        st.success("Limites atualizados.")

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
                conn = get_db_connection()
                conn.execute(
                    "INSERT INTO gallery (before_path, after_path, caption) VALUES (?,?,?)",
                    (before_path, after_path, cap)
                )
                conn.commit()
                conn.close()
                st.success("Fotos adicionadas à galeria!")
            else:
                st.error("Preencha todos os campos!")

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
    conn = get_db_connection()
    df = pd.read_sql("""
        SELECT a.id, a.name, a.contact, a.address, a.date, a.time, s.name as service, a.status, a.image_path
        FROM appointments a
        JOIN services s ON a.service_id = s.id
        WHERE a.user_id = ?
        ORDER BY a.date DESC, a.time DESC
    """, conn, params=(st.session_state['user_id'],))
    conn.close()

    if df.empty:
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

    for _, row in df.iterrows():
        # Formatar data e hora para padrão brasileiro
        try:
            data_hora = datetime.strptime(f"{row['date']} {row['time']}", "%Y-%m-%d %H:%M")
            data_hora_br = data_hora.strftime("%d/%m/%Y %H:%M")
        except Exception:
            data_hora_br = f"{row['date']} {row['time']}"

        # Determinar a classe de status
        status_class = {
            'confirmado': 'status-confirmado',
            'rejeitado': 'status-rejeitado',
            'novo': 'status-novo'
        }.get(row['status'], 'status-novo')

        # Determinar o texto do status
        status_text = {
            'confirmado': 'Confirmado',
            'rejeitado': 'Rejeitado',
            'novo': 'Em Análise'
        }.get(row['status'], 'Em Análise')

        # Criar o card
        st.markdown(f"""
            <div class="card {row['status']}">
                <div class="card-header">
                    <div class="card-title">#{row['id']} - {row['service']}</div>
                    <div class="card-status {status_class}">{status_text}</div>
                </div>
                <div class="card-content">
                    <div class="card-item">
                        <div class="card-label">Data e Hora</div>
                        <div class="card-value">{data_hora_br}</div>
                    </div>
                    <div class="card-item">
                        <div class="card-label">Endereço</div>
                        <div class="card-value">{row['address']}</div>
                    </div>
                    <div class="card-item">
                        <div class="card-label">Contato</div>
                        <div class="card-value">{row['contact']}</div>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        # Exibir imagem se existir
        if row['image_path'] and isinstance(row['image_path'], str) and row['image_path'].strip() != "None":
            st.image(row['image_path'], width=200, caption="Foto da piscina")

# ---------- ROTEAMENTO ----------
def main():
    # Inicializar banco de dados
    init_db()

    # Inicializar estados da sessão
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False
    if 'current_page' not in st.session_state:
        st.session_state['current_page'] = "Home"
    if 'user_agent' not in st.session_state:
        st.session_state['user_agent'] = st.query_params.get('user_agent', [''])[0]
    if 'is_admin' not in st.session_state:
        st.session_state['is_admin'] = False

    # Detectar dispositivo
    dispositivo = detectar_dispositivo()

    # Menu lateral
    st.sidebar.title("Menu")

    if st.session_state['logged_in']:
        # Obter informações do usuário
        conn = get_db_connection()
        if st.session_state['is_admin']:
            user = conn.execute("SELECT name, is_dev FROM users WHERE id = ?",
                              (st.session_state['user_id'],)).fetchone()
            user_type = "Administrador"
        else:
            user = conn.execute("SELECT name FROM users WHERE id = ?",
                              (st.session_state['user_id'],)).fetchone()
            user_type = "Usuário"
        conn.close()

        # Exibir informações do usuário no menu lateral
        st.sidebar.markdown("---")
        st.sidebar.markdown(f"**Usuário:** {user['name']}")
        st.sidebar.markdown(f"**Tipo:** {user_type}")
        st.sidebar.markdown(f"**Dispositivo:** {dispositivo.upper()}")

        if st.session_state['is_admin']:
            # Menu para administradores
            st.session_state['current_page'] = st.sidebar.radio(
                "Navegação",
                ["Agendamentos", "Serviços", "Configurações", "Galeria", "Logout"],
                key="nav_admin"
            )

            if st.session_state['current_page'] == "Logout":
                st.session_state['logged_in'] = False
                st.session_state['is_admin'] = False
                st.session_state['current_page'] = "Home"
                st.rerun()
            elif st.session_state['current_page'] == "Agendamentos":
                admin_agendamentos()
            elif st.session_state['current_page'] == "Serviços":
                admin_services()
            elif st.session_state['current_page'] == "Configurações":
                admin_config()
            elif st.session_state['current_page'] == "Galeria":
                admin_gallery()
        else:
            # Menu para usuários comuns
            st.session_state['current_page'] = st.sidebar.radio(
                "Navegação",
                ["Home", "Área de Cobertura", "Contato", "Meus Agendamentos", "Logout"],
                key="nav_user"
            )

            if st.session_state['current_page'] == "Logout":
                st.session_state['logged_in'] = False
                st.session_state['current_page'] = "Home"
                st.rerun()
            elif st.session_state['current_page'] == "Home":
                homepage()
            elif st.session_state['current_page'] == "Área de Cobertura":
                mapa_tempo()
            elif st.session_state['current_page'] == "Contato":
                contato()
            elif st.session_state['current_page'] == "Meus Agendamentos":
                meus_agendamentos()
    else:
        # Menu para usuários não logados
        st.session_state['current_page'] = st.sidebar.radio(
            "Navegação",
            ["Home", "Área de Cobertura", "Login", "Cadastro", "Admin"],
            key="nav_not_logged_in"
        )

        if st.session_state['current_page'] == "Home":
            homepage()
        elif st.session_state['current_page'] == "Área de Cobertura":
            mapa_tempo()
        elif st.session_state['current_page'] == "Login":
            login_usuario()
        elif st.session_state['current_page'] == "Cadastro":
            cadastro()
        elif st.session_state['current_page'] == "Admin":
            login_admin()

    # Ocultar barra superior, rodapé e header do Streamlit
    hide_streamlit_style = """
        <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;} # para habilitar o header, basta mudar para "visible"
        </style>
    """
    st.markdown(hide_streamlit_style, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
