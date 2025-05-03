from db_utils import get_db_connection

def make_admin(username):
    conn = get_db_connection()
    try:
        conn.execute("UPDATE users SET is_admin = 1 WHERE username = ?", (username,))
        conn.commit()
        print(f"Usuário {username} agora é administrador!")
    except Exception as e:
        print(f"Erro ao tornar {username} administrador: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    username = input("Digite o nome de usuário para tornar administrador: ")
    make_admin(username)