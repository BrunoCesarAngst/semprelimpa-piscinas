import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import re
from dotenv import load_dotenv
from config import settings

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/monitor.log'),
        logging.StreamHandler()
    ]
)

# Carregar variáveis de ambiente
load_dotenv()

# Configurações
LOG_DIR = 'logs'
LOG_FILES = [
    'app.log',
    'monitor.log'
]
ERROR_PATTERNS = {
    'CRITICAL': [r'CRITICAL', r'Traceback'],
    'ERROR': [r'ERROR', r'Exception'],
    'WARNING': [r'WARNING', r'failed']
}
ALERT_EMAIL = settings.ALERT_EMAIL
SMTP_SERVER = settings.SMTP_SERVER
SMTP_PORT = settings.SMTP_PORT
SMTP_USER = settings.SMTP_USER
SMTP_PASS = settings.SMTP_PASS
CHECK_INTERVAL = 3600  # Verificar a cada 1 hora

def setup_logging():
    """Configura a estrutura de logs"""
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)

    # Rotação de logs (manter últimos 7 dias)
    for log_file in LOG_FILES:
        log_path = os.path.join(LOG_DIR, log_file)
        if os.path.exists(log_path):
            # Criar backup com timestamp
            backup_time = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_path = os.path.join(LOG_DIR, f'{log_file}.{backup_time}')
            os.rename(log_path, backup_path)

def send_alert(level, subject, message):
    """Envia alerta por email com nível de severidade"""
    if not all([ALERT_EMAIL, SMTP_SERVER, SMTP_USER, SMTP_PASS]):
        logging.warning('Configurações de email não completas, pulando envio de alerta')
        return

    try:
        msg = MIMEMultipart()
        msg['From'] = SMTP_USER
        msg['To'] = ALERT_EMAIL
        msg['Subject'] = f'[{level}] {subject}'

        msg.attach(MIMEText(message, 'plain'))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)
        server.quit()

        logging.info(f'Alerta {level} enviado: {subject}')

    except Exception as e:
        logging.error(f'Erro ao enviar alerta: {str(e)}')
        raise

def check_logs():
    """Verifica logs em busca de erros"""
    errors_found = {'CRITICAL': [], 'ERROR': [], 'WARNING': []}

    for log_file in LOG_FILES:
        log_path = os.path.join(LOG_DIR, log_file)
        if not os.path.exists(log_path):
            logging.warning(f'Arquivo de log não encontrado: {log_path}')
            continue

        try:
            # Ler apenas as últimas 24 horas de logs
            cutoff_time = datetime.now() - timedelta(hours=24)

            with open(log_path, 'r') as f:
                for line in f:
                    # Extrair timestamp do log
                    match = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
                    if match:
                        log_time = datetime.strptime(match.group(1), '%Y-%m-%d %H:%M:%S')
                        if log_time < cutoff_time:
                            continue

                    # Verificar padrões de erro por nível
                    for level, patterns in ERROR_PATTERNS.items():
                        if any(pattern in line for pattern in patterns):
                            errors_found[level].append(f'{log_file}: {line.strip()}')

        except Exception as e:
            logging.error(f'Erro ao ler arquivo de log {log_path}: {str(e)}')

    return errors_found

def main():
    """Função principal de monitoramento"""
    try:
        setup_logging()
        errors = check_logs()

        # Enviar alertas por nível de severidade
        for level, error_list in errors.items():
            if error_list:
                subject = f'{len(error_list)} {level}s encontrados nos logs'
                message = '\n'.join(error_list)
                send_alert(level, subject, message)

        logging.info('Verificação de logs concluída')

    except Exception as e:
        logging.error(f'Erro no processo de monitoramento: {str(e)}')
        raise

if __name__ == '__main__':
    main()