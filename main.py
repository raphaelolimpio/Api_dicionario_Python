import sqlite3
from fastapi import FastAPI

app = FastAPI()
DB_PATH = 'comandos.db'

def get_db_connection():
    """Cria uma conexão com o banco de dados"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn
@app.get("/comandos")
def get_todos_comandos():
    """Busca todos os comandos no banco de dados e os retorna."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM comandos")
        comandos = cursor.fetchall()

        conn.close()
        return {"comandos": comandos}

    except Exception as e:
        return {"erro": str(e)}, 500

@app.get("/comandos/topico/{nome_topico}")
def get_comandos_por_topico(nome_topico: str):
    """Busca comandos filtrando por um tópico específico."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM comandos WHERE topico LIKE ?", (f'%{nome_topico}%',))
        comandos = cursor.fetchall()

        conn.close()

        if not comandos:
            return {"mensagem": "Nenhum comando encontrado para este tópico"}, 404

        return {"comandos": comandos}

    except Exception as e:
        return {"erro": str(e)}, 500
    

    # comando para rodar a aplicação:
    # python -m uvicorn main:app --reload