from db_utils import get_db_connection

def check_and_update_user(username):
    conn = get_db_connection()
    try:
        # Verificar se o usuário existe
        user = conn.execute("""
            SELECT id, username, is_admin
            FROM users
            WHERE username = ?
        """, (username,)).fetchone()

        if not user:
            print(f"Usuário {username} não encontrado!")
            return

        print(f"Usuário encontrado: {user['username']}")
        print(f"Status atual de administrador: {user['is_admin']}")

        # Atualizar para administrador
        conn.execute("""
            UPDATE users
            SET is_admin = 1
            WHERE username = ?
        """, (username,))
        conn.commit()
        print(f"Usuário {username} agora é administrador!")

    except Exception as e:
        print(f"Erro: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    username = input("Digite o nome de usuário para verificar/atualizar: ")
    check_and_update_user(username)