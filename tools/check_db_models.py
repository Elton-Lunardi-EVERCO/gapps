import sys
import os
from sqlalchemy import exc
from flask_sqlalchemy import inspect

# improve this hack
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models import *

app = create_app(os.getenv("FLASK_CONFIG") or "default")


def should_we_create_models():
    """
    checks if the tables are defined in the database
    and if we should create the models
    will return 3 possible values: Yes, No, Error
    """
    with app.app_context():
        try:
            inspector = inspect(db.engine)

            # check if we have tables created
            created_tables = inspector.get_table_names()
            if len(created_tables) < 5:
                return "Sim"
            return "Não"
        except exc.SQLAlchemyError as e:
            print(f"[ERROR] Traceback ao consultar o modelo de banco de dados: {e}")
            return "Erro"
    return "Erro"


print(f"[INFO] Verificando se os modelos de banco de dados exigem criação")
result = should_we_create_models()
if result == "Sim":
    print(f"[WARNING] Não é possível consultar os modelos de banco de dados. Eles precisam ser criados")
    exit(1)
elif result == "Erro":
    print("[ERROR] Erro ao consultar modelos de banco de dados")
    exit(1)
elif result == "Não":
    print(f"[INFO] Consultou com sucesso os modelos de banco de dados")
exit(0)
