import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
import re
from dotenv import load_dotenv

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('monitor.log'),
        logging.StreamHandler()
    ]
)

# Carregar variáveis de ambiente
load_dotenv()

# Configurações
LOG_FILES = [
    'app.log',
    'backup.log',
    'monitor.log'
]
ERROR_PATTERNS = [
    r'ERROR',
    r'Exception',
    r'Traceback',
    r'failed',
    r'error'
]
ALERT_EMAIL = os.getenv('ALERT_EMAIL')
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
SMTP_USER = os.getenv('SMTP_USER')
SMTP_PASS = os.getenv('SMTP_PASS')
CHECK_INTERVAL = 3600  # Verificar a cada 1 hora

def send_alert(subject, message):
    """Envia alerta por email"""
    if not all([ALERT_EMAIL, SMTP_SERVER, SMTP_USER, SMTP_PASS]):
        logging.warning('Configurações de email não completas, pulando envio de alerta')
        return

    try:
        msg = MIMEMultipart()
        msg['From'] = SMTP_USER
        msg['To'] = ALERT_EMAIL
        msg['Subject'] = f'[ALERTA] {subject}'

        msg.attach(MIMEText(message, 'plain'))

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)
        server.quit()

        logging.info(f'Alerta enviado: {subject}')

    except Exception as e:
        logging.error(f'Erro ao enviar alerta: {str(e)}')
        raise

def check_logs():
    """Verifica logs em busca de erros"""
    errors_found = []

    for log_file in LOG_FILES:
        if not os.path.exists(log_file):
            logging.warning(f'Arquivo de log não encontrado: {log_file}')
            continue

        try:
            # Ler apenas as últimas 24 horas de logs
            cutoff_time = datetime.now() - timedelta(hours=24)

            with open(log_file, 'r') as f:
                for line in f:
                    # Extrair timestamp do log
                    match = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
                    if match:
                        log_time = datetime.strptime(match.group(1), '%Y-%m-%d %H:%M:%S')
                        if log_time < cutoff_time:
                            continue

                    # Verificar padrões de erro
                    if any(pattern in line for pattern in ERROR_PATTERNS):
                        errors_found.append(f'{log_file}: {line.strip()}')

        except Exception as e:
            logging.error(f'Erro ao ler arquivo de log {log_file}: {str(e)}')

    return errors_found

def main():
    """Função principal de monitoramento"""
    try:
        errors = check_logs()

        if errors:
            subject = f'Erros encontrados em {len(errors)} logs'
            message = '\n'.join(errors)
            send_alert(subject, message)

        logging.info('Verificação de logs concluída')

    except Exception as e:
        logging.error(f'Erro no processo de monitoramento: {str(e)}')
        raise

if __name__ == '__main__':
    main()