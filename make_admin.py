from models import User
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from config import settings

def make_admin(username):
    # Configuração da conexão com o banco de dados
    engine = create_engine(f"sqlite:///{settings.DB_PATH}")
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Verificar se o usuário existe
        user = session.query(User).filter_by(username=username).first()
        if not user:
            print(f"Erro: Usuário '{username}' não encontrado!")
            return False

        # Verificar se já é administrador
        if user.is_admin:
            print(f"Usuário {username} já é administrador!")
            return True

        # Tornar administrador
        user.is_admin = True
        session.commit()
        print(f"Usuário {username} agora é administrador!")
        return True

    except Exception as e:
        print(f"Erro ao tornar {username} administrador: {e}")
        session.rollback()
        return False
    finally:
        session.close()

if __name__ == "__main__":
    print("=== Ferramenta de Administração ===")
    print("Esta ferramenta permite tornar um usuário em administrador do sistema.")
    print("Apenas usuários com acesso ao servidor podem executar esta operação.")
    print("=" * 40)

    username = input("Digite o nome de usuário para tornar administrador: ").strip()

    if not username:
        print("Erro: Nome de usuário não pode estar vazio!")
    else:
        make_admin(username)