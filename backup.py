import os
import sqlite3
import shutil
import boto3
from datetime import datetime
import logging
from dotenv import load_dotenv

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('backup.log'),
        logging.StreamHandler()
    ]
)

# Carregar variáveis de ambiente
load_dotenv()

# Configurações
DB_PATH = os.getenv('DB_PATH', 'data/database_production.db')
BACKUP_DIR = 'backups'
S3_BUCKET = os.getenv('S3_BUCKET')
S3_PREFIX = 'db_backups'
RETENTION_DAYS = 7  # Manter backups dos últimos 7 dias

def create_backup():
    """Cria um backup do banco de dados"""
    try:
        # Criar diretório de backups se não existir
        os.makedirs(BACKUP_DIR, exist_ok=True)

        # Nome do arquivo de backup com timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = f'{BACKUP_DIR}/db_backup_{timestamp}.db'

        # Criar conexão com o banco de dados
        conn = sqlite3.connect(DB_PATH)

        # Criar backup
        backup_conn = sqlite3.connect(backup_file)
        conn.backup(backup_conn)

        # Fechar conexões
        backup_conn.close()
        conn.close()

        logging.info(f'Backup criado com sucesso: {backup_file}')
        return backup_file

    except Exception as e:
        logging.error(f'Erro ao criar backup: {str(e)}')
        raise

def upload_to_s3(backup_file):
    """Upload do backup para o S3"""
    if not S3_BUCKET:
        logging.warning('Bucket S3 não configurado, pulando upload')
        return

    try:
        s3 = boto3.client('s3')
        s3_key = f'{S3_PREFIX}/{os.path.basename(backup_file)}'

        s3.upload_file(backup_file, S3_BUCKET, s3_key)
        logging.info(f'Backup enviado para S3: {s3_key}')

    except Exception as e:
        logging.error(f'Erro ao enviar backup para S3: {str(e)}')
        raise

def cleanup_old_backups():
    """Remove backups antigos"""
    try:
        # Listar arquivos de backup
        backup_files = [f for f in os.listdir(BACKUP_DIR) if f.startswith('db_backup_')]

        # Ordenar por data (mais recente primeiro)
        backup_files.sort(reverse=True)

        # Manter apenas os backups dos últimos RETENTION_DAYS dias
        for old_file in backup_files[RETENTION_DAYS:]:
            file_path = os.path.join(BACKUP_DIR, old_file)
            os.remove(file_path)
            logging.info(f'Backup antigo removido: {old_file}')

    except Exception as e:
        logging.error(f'Erro ao limpar backups antigos: {str(e)}')
        raise

def restore_backup(backup_file):
    """Restaura um backup do banco de dados"""
    try:
        # Criar backup do banco atual antes de restaurar
        current_backup = create_backup()
        logging.info(f'Backup do banco atual criado: {current_backup}')

        # Restaurar backup
        conn = sqlite3.connect(DB_PATH)
        backup_conn = sqlite3.connect(backup_file)
        backup_conn.backup(conn)

        # Fechar conexões
        backup_conn.close()
        conn.close()

        logging.info(f'Backup restaurado com sucesso: {backup_file}')

    except Exception as e:
        logging.error(f'Erro ao restaurar backup: {str(e)}')
        raise

def main():
    """Função principal de backup"""
    try:
        # Criar backup
        backup_file = create_backup()

        # Upload para S3
        upload_to_s3(backup_file)

        # Limpar backups antigos
        cleanup_old_backups()

        logging.info('Processo de backup concluído com sucesso')

    except Exception as e:
        logging.error(f'Erro no processo de backup: {str(e)}')
        raise

if __name__ == '__main__':
    main()