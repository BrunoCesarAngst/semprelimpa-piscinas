import os
import sys
import subprocess

def run_app(environment):
    """Executa a aplicação no ambiente especificado"""
    env = os.environ.copy()
    env['ENVIRONMENT'] = environment

    print(f"🚀 Iniciando aplicação no ambiente: {environment}")
    print(f"📁 Banco de dados: data/database_{environment}.db")

    try:
        subprocess.run(['streamlit', 'run', 'streamlit_app.py'], env=env)
    except KeyboardInterrupt:
        print("\n👋 Aplicação encerrada pelo usuário")
    except Exception as e:
        print(f"❌ Erro ao executar a aplicação: {e}")

if __name__ == "__main__":
    if len(sys.argv) != 2 or sys.argv[1] not in ['development', 'staging', 'production']:
        print("Uso: python run.py [development|staging|production]")
        sys.exit(1)

    run_app(sys.argv[1])