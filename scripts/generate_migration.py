#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
import shutil
import alembic.config
from alembic import command
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Adicionar diretório raiz ao PYTHONPATH
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, root_dir)

# Agora podemos importar os módulos do projeto
from config import settings
from models import User, Service, Appointment, Base

# Configurações do banco de dados
DB_PATH = settings.DB_PATH
engine = create_engine(f"sqlite:///{DB_PATH}")
Session = sessionmaker(bind=engine)

def verify_database_integrity():
    """
    Verifica a integridade do banco de dados após migrações.

    Returns:
        tuple: (integrity_ok, issues)
    """
    session = Session()
    issues = []

    try:
        # Verificar tabelas principais
        try:
            user_count = session.query(User).count()
        except Exception as e:
            issues.append(f"Erro ao acessar tabela User: {str(e)}")

        try:
            service_count = session.query(Service).count()
        except Exception as e:
            issues.append(f"Erro ao acessar tabela Service: {str(e)}")

        try:
            appointment_count = session.query(Appointment).count()
        except Exception as e:
            issues.append(f"Erro ao acessar tabela Appointment: {str(e)}")

        # Verificar relacionamentos
        if not issues:
            try:
                # Verificar relacionamento User-Appointment
                if appointment_count > 0:
                    appointment_with_user = session.query(Appointment).join(User).first()
            except Exception as e:
                issues.append(f"Erro no relacionamento User-Appointment: {str(e)}")

            try:
                # Verificar relacionamento Service-Appointment
                if appointment_count > 0:
                    appointment_with_service = session.query(Appointment).join(Service).first()
            except Exception as e:
                issues.append(f"Erro no relacionamento Service-Appointment: {str(e)}")

        return len(issues) == 0, issues

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

def safe_run_migrations():
    """
    Executa migrações com tratamento de erros e restauração automática.

    Returns:
        tuple: (success, message)
    """
    # Criar backup antes de migrar
    backup_file = backup_db()
    if not backup_file:
        return False, "Falha ao criar backup antes da migração"

    try:
        # Configurar o Alembic
        alembic_cfg = alembic.config.Config("alembic.ini")

        # Executar migrações
        command.upgrade(alembic_cfg, "head")

        # Verificar integridade após migração
        integrity_ok, issues = verify_database_integrity()
        if not integrity_ok:
            raise Exception(f"Problemas de integridade detectados:\n" + "\n".join(issues))

        return True, "Migrações executadas com sucesso"

    except Exception as e:
        # Restaurar backup em caso de erro
        if engine:
            engine.dispose()

        if os.path.exists(backup_file):
            shutil.copy2(backup_file, DB_PATH)
            return False, f"Erro durante migração, backup restaurado: {str(e)}"
        else:
            return False, f"Erro durante migração, falha ao restaurar backup: {str(e)}"

def generate_migration(message):
    """
    Gera uma nova migração Alembic com base nas alterações nos modelos.

    Args:
        message: Mensagem descritiva para a migração
    """
    try:
        # Configurar o Alembic
        alembic_cfg = alembic.config.Config("alembic.ini")

        # Gerar migração
        command.revision(alembic_cfg, message=message, autogenerate=True)
        print(f"Migração gerada com sucesso: {message}")

        # Perguntar se deseja aplicar a migração
        if input("Deseja aplicar a migração agora? (s/N): ").lower() == 's':
            success, msg = safe_run_migrations()
            if success:
                print("✅ " + msg)
            else:
                print("❌ " + msg)
                sys.exit(1)

    except Exception as e:
        print(f"❌ Erro ao gerar migração: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python generate_migration.py 'Mensagem da migração'")
        sys.exit(1)

    message = sys.argv[1]
    generate_migration(message)