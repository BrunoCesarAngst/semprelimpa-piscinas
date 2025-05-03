import schedule
import time
import subprocess
import logging
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scheduler.log'),
        logging.StreamHandler()
    ]
)

def run_backup():
    """Executa o script de backup"""
    try:
        logging.info('Iniciando backup...')
        subprocess.run(['python', 'backup.py'], check=True)
        logging.info('Backup concluído com sucesso')
    except subprocess.CalledProcessError as e:
        logging.error(f'Erro ao executar backup: {str(e)}')

def run_monitor():
    """Executa o script de monitoramento"""
    try:
        logging.info('Iniciando monitoramento...')
        subprocess.run(['python', 'monitor.py'], check=True)
        logging.info('Monitoramento concluído com sucesso')
    except subprocess.CalledProcessError as e:
        logging.error(f'Erro ao executar monitoramento: {str(e)}')

def main():
    """Função principal do agendador"""
    # Agendar backup diário às 2h da manhã
    schedule.every().day.at("02:00").do(run_backup)

    # Agendar monitoramento a cada hora
    schedule.every().hour.do(run_monitor)

    logging.info('Agendador iniciado')

    while True:
        try:
            schedule.run_pending()
            time.sleep(60)  # Verificar a cada minuto
        except Exception as e:
            logging.error(f'Erro no agendador: {str(e)}')
            time.sleep(300)  # Esperar 5 minutos em caso de erro

if __name__ == '__main__':
    main()