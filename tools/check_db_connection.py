import psycopg2
import os

SQLALCHEMY_DATABASE_URI = os.environ.get("SQLALCHEMY_DATABASE_URI")


def can_we_connect_to_postgres():
    try:
        connection = psycopg2.connect(SQLALCHEMY_DATABASE_URI)
        connection.close()
        return True
    except Exception as e:
        print(f"[ERROR] {e}".strip())
        return False


print(
    f"[INFO] Verificando se podemos nos conectar ao servidor de banco de dados: {SQLALCHEMY_DATABASE_URI}"
)
if not can_we_connect_to_postgres():
    print(f"[ERROR] Não é possível conectar-se ao servidor de banco de dados")
    exit(1)
print(f"[INFO] Conectado com sucesso ao servidor de banco de dados")
exit(0)
