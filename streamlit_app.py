import streamlit as st
from streamlit_folium import folium_static
import folium
import sqlite3
import pandas as pd
import requests
from datetime import datetime
import os
import hashlib
from dotenv import load_dotenv
import urllib.parse

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# ---------- CONFIGURAÇÕES ----------
# Configuração do banco de dados baseada no ambiente
ENVIRONMENT = os.getenv('ENVIRONMENT', 'production')
DB_PATH = os.path.join('data', f'database_{ENVIRONMENT}.db')
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
def hash_pwd(pwd: str) -> str:
    return hashlib.sha256(pwd.encode()).hexdigest()

def check_pwd(hashval: str, pwd: str) -> bool:
    return hashval == hashlib.sha256(pwd.encode()).hexdigest()

def get_db_connection():
    """Retorna uma conexão com o banco de dados apropriado para o ambiente atual"""
    # Garantir que o diretório data existe
    os.makedirs('data', exist_ok=True)

    # Criar conexão com o banco de dados
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def gerar_agendamentos_teste():
    """Gera agendamentos de teste APENAS em ambiente de desenvolvimento"""
    # Verificar se estamos em ambiente de desenvolvimento
    if not os.getenv('ENVIRONMENT') == 'development':
        return

    conn = get_db_connection()
    c = conn.cursor()

    # Obter o número de WhatsApp de desenvolvimento
    whatsapp_dev = os.getenv('WHATSAPP_LINK_DEV', '51999999999')  # Número padrão caso não esteja configurado

    # Dados de teste
    agendamentos_teste = [
        ("João Silva", "51999999999", "Rua das Flores, 123", "2024-05-01", "09:00", 1, "confirmado", None),
        ("Maria Santos", "51988888888", "Av. Principal, 456", "2024-05-02", "14:30", 2, "novo", None),
        ("Pedro Oliveira", "51977777777", "Rua do Sol, 789", "2024-05-03", "10:00", 3, "novo", None),
        ("Ana Costa", "51966666666", "Rua da Praia, 101", "2024-05-04", "15:00", 4, "novo", None),
        ("Carlos Pereira", "51955555555", "Av. Beira Mar, 202", "2024-05-05", "11:30", 1, "novo", None),
        ("Bruno Angst", whatsapp_dev, "Av. Beira Mar, 202", "2024-05-05", "11:30", 1, "novo", None),
    ]

    # Inserir agendamentos
    c.executemany(
        "INSERT INTO appointments (name, contact, address, date, time, service_id, status, image_path) VALUES (?,?,?,?,?,?,?,?)",
        agendamentos_teste
    )

    conn.commit()
    conn.close()

def init_db():
    """Inicializa o banco de dados apropriado para o ambiente atual"""
    # Garantir que o diretório data existe
    os.makedirs('data', exist_ok=True)

    # Criar conexão com o banco de dados
    conn = get_db_connection()
    c = conn.cursor()

    # Tabelas
    c.execute('''
        CREATE TABLE IF NOT EXISTS services (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            description TEXT,
            price REAL,
            active INTEGER DEFAULT 1
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS config (
            weekday INTEGER PRIMARY KEY,
            max_appointments INTEGER
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            contact TEXT,
            address TEXT,
            date TEXT,
            time TEXT,
            service_id INTEGER,
            status TEXT,
            image_path TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password_hash TEXT,
            is_dev INTEGER DEFAULT 0
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS gallery (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            before_path TEXT,
            after_path TEXT,
            caption TEXT
        )
    ''')

    # Verificar se a coluna is_dev existe, se não, adicionar
    try:
        c.execute("SELECT is_dev FROM users LIMIT 1")
    except sqlite3.OperationalError:
        c.execute("ALTER TABLE users ADD COLUMN is_dev INTEGER DEFAULT 0")

    # Usuário padrão (apenas em produção)
    if ENVIRONMENT == 'production':
        c.execute("SELECT COUNT(*) FROM users")
        if c.fetchone()[0] == 0:
            default_hash = hash_pwd("senha123")
            c.execute("INSERT INTO users(username,password_hash,is_dev) VALUES (?,?,?)", ("piscineiro", default_hash, 0))

    # Usuário de desenvolvimento (apenas em desenvolvimento)
    if ENVIRONMENT == 'development':
        dev_hash = hash_pwd("a")
        c.execute("INSERT OR IGNORE INTO users(username,password_hash,is_dev) VALUES (?,?,?)", ("dev", dev_hash, 1))

    # Configuração padrão (0 = ilimitado)
    for wd in range(7):
        c.execute("INSERT OR IGNORE INTO config(weekday,max_appointments) VALUES (?,?)", (wd, 0))

    # Serviços padrão
    c.execute("SELECT COUNT(*) FROM services")
    if c.fetchone()[0] == 0:
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
        for name, desc, price in default_services:
            c.execute(
                "INSERT INTO services (name, description, price, active) VALUES (?,?,?,?)",
                (name, desc, price, 1)
            )

    conn.commit()
    conn.close()

    # Gerar agendamentos de teste apenas em desenvolvimento
    if ENVIRONMENT == 'development':
        gerar_agendamentos_teste()

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
        name = st.text_input("Nome")
        contact = st.text_input("Telefone ou Email")
        address = st.text_input("Endereço da piscina")
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
                    "INSERT INTO appointments (name, contact, address, date, time, service_id, status, image_path) VALUES (?,?,?,?,?,?,?,?)",
                    (name, contact, address, date.isoformat(), time.strftime("%H:%M"), service_id, 'novo', img_path)
                )
                conn.commit()
                st.success("Recebemos seu pedido! Entraremos em contato em breve.")
            conn.close()

# ---------- AUTENTICAÇÃO & PÁGINAS ADMIN ----------
def login():
    st.title("Login Administrativo")
    username = st.text_input("Usuário")
    password = st.text_input("Senha", type='password')
    if st.button("Entrar"):
        conn = get_db_connection()
        row = conn.execute("SELECT password_hash, is_dev FROM users WHERE username=?", (username,)).fetchone()
        conn.close()
        if row and check_pwd(row['password_hash'], password):
            st.session_state['logged_in'] = True
            st.session_state['is_dev'] = bool(row['is_dev'])
            if row['is_dev']:
                st.success("Bem-vindo, Desenvolvedor! 🚀")
            st.rerun()
        else:
            st.error("Credenciais inválidas.")

def enviar_mensagem_whatsapp(contato, nome, data, hora, servico, status):
    """Envia uma mensagem via WhatsApp para o cliente sobre o status do agendamento"""
    try:
        # Formatar e validar o número de telefone
        contato = ''.join(filter(str.isdigit, contato))

        # Se o número começar com 'wa.me' ou 'https', extrair apenas os dígitos
        if 'wa.me' in str(contato) or 'https' in str(contato):
            contato = ''.join(filter(str.isdigit, contato.split('/')[-1]))

        # Verificar se o número tem o formato correto
        if len(contato) < 10 or len(contato) > 13:
            print(f"❌ Erro: Número de telefone inválido: {contato}")
            st.error("Número de telefone inválido. Deve ter entre 10 e 13 dígitos.")
            return False

        # Adicionar código do país se necessário
        if not contato.startswith("55"):
            contato = "55" + contato

        # Verificar se o DDD é válido
        if not contato[2:4].isdigit():
            print(f"❌ Erro: DDD inválido no número: {contato}")
            st.error("DDD inválido no número de telefone.")
            return False

        # Formatar a mensagem baseada no status
        if status == 'confirmado':
            mensagem = f"""
Olá {nome}! 👋

Seu agendamento foi confirmado! 🎉

📅 Data: {data}
⏰ Horário: {hora}
🛠️ Serviço: {servico}

Estamos ansiosos para atendê-lo! Se precisar de qualquer alteração, entre em contato conosco.

Atenciosamente,
Equipe Sempre Limpa Piscinas
"""
        else:  # rejeitado
            mensagem = f"""
Olá {nome}! 👋

Infelizmente não conseguimos atender seu agendamento. 😔

📅 Data solicitada: {data}
⏰ Horário: {hora}
🛠️ Serviço: {servico}

Por favor, entre em contato conosco para tentarmos encontrar uma data alternativa.

Atenciosamente,
Equipe Sempre Limpa Piscinas
"""

        # Codificar a mensagem para URL
        mensagem_codificada = urllib.parse.quote(mensagem)

        # Criar o link do WhatsApp
        whatsapp_link = f"https://wa.me/{contato}?text={mensagem_codificada}"

        # Log para debug
        print(f"🔍 Debug - Número formatado: {contato}")
        print(f"🔍 Debug - Status: {status}")
        print(f"🔍 Debug - Link gerado: {whatsapp_link}")

        # Exibir botão para enviar mensagem
        st.markdown(
            f'<a href="{whatsapp_link}" target="_blank">'
            f'<button style="padding:10px 20px; font-size:16px; background-color:{"#4CAF50" if status == "confirmado" else "#f44336"}; color:white; border:none; border-radius:5px;">'
            f'{"📲 Enviar Confirmação" if status == "confirmado" else "📲 Enviar Rejeição"}'
            f'</button></a>',
            unsafe_allow_html=True
        )

        return True

    except Exception as e:
        print(f"❌ Erro ao gerar link do WhatsApp: {str(e)}")
        st.error(f"Erro ao gerar link do WhatsApp: {str(e)}")
        return False

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
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            if row['status'] == 'novo':
                if st.button("Confirmar", key=f"conf_{row['id']}"):
                    conn = get_db_connection()
                    conn.execute("UPDATE appointments SET status='confirmado' WHERE id=?", (row['id'],))
                    conn.commit()
                    conn.close()

                    # Formatar data para o padrão brasileiro
                    data_formatada = datetime.strptime(row['date'], "%Y-%m-%d").strftime("%d/%m/%Y")

                    # Exibir botão para enviar mensagem de confirmação
                    st.success("Agendamento confirmado!")
                    enviar_mensagem_whatsapp(row['contact'], row['name'], data_formatada, row['time'], row['service'], 'confirmado')

                    st.rerun()
        with col2:
            if row['status'] == 'novo':
                if st.button("Rejeitar", key=f"rej_{row['id']}"):
                    conn = get_db_connection()
                    conn.execute("UPDATE appointments SET status='rejeitado' WHERE id=?", (row['id'],))
                    conn.commit()
                    conn.close()

                    # Formatar data para o padrão brasileiro
                    data_formatada = datetime.strptime(row['date'], "%Y-%m-%d").strftime("%d/%m/%Y")

                    # Exibir botão para enviar mensagem de rejeição
                    st.warning("Agendamento rejeitado!")
                    enviar_mensagem_whatsapp(row['contact'], row['name'], data_formatada, row['time'], row['service'], 'rejeitado')

                    st.rerun()
        with col3:
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

# ---------- ROTEAMENTO ----------
def main():
    # Inicializar banco de dados
    init_db()

    # Menu lateral
    st.sidebar.title("Menu")
    if 'logged_in' not in st.session_state:
        st.session_state['logged_in'] = False

    if st.session_state['logged_in']:
        page = st.sidebar.radio(
            "Navegação",
            ["Agendamentos", "Serviços", "Configurações", "Galeria", "Logout"]
        )
        if page == "Logout":
            st.session_state['logged_in'] = False
            st.rerun()
        elif page == "Agendamentos":
            admin_agendamentos()
        elif page == "Serviços":
            admin_services()
        elif page == "Configurações":
            admin_config()
        elif page == "Galeria":
            admin_gallery()
    else:
        page = st.sidebar.radio(
            "Navegação",
            ["Home", "Área de Cobertura", "Contato", "Login"]
        )
        if page == "Home":
            homepage()
        elif page == "Área de Cobertura":
            mapa_tempo()
        elif page == "Contato":
            contato()
        elif page == "Login":
            login()

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
