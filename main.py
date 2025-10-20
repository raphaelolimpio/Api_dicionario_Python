import sqlite3
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional


class Comando(BaseModel):
    """Modelo para receber dados ao criar ou atualizar um comando."""
    topico: str
    nome: Optional[str] = None
    categoria: Optional[str] = None
    definicao: Optional[str] = None
    comando_exemplo: Optional[str] = None
    explicacao_pratica: Optional[str] = None
    dicas_de_uso: Optional[str] = None

class ComandoComId(Comando):
    """Modelo para retornar um comando que já existe no banco (com ID)."""
    id: int

app = FastAPI()
DB_PATH = 'comandos.db'

def get_db_connection():
    """Cria e retorna uma conexão com o banco de dados."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@app.get("/")
def get_root():
    """Endpoint raiz com mensagem de boas-vindas."""
    return {"mensagem": "Bem-vindo à API de Comandos! Use /docs para ver a documentação."}

@app.get("/comandos", response_model=list[ComandoComId])
def get_todos_comandos():
    """Busca todos os comandos no banco de dados."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM comandos")
        comandos = cursor.fetchall()
        conn.close()
        return comandos
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/comandos/topico/{nome_topico}", response_model=list[ComandoComId])
def get_comandos_por_topico(nome_topico: str):
    """Busca comandos filtrando por um tópico específico."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM comandos WHERE topico LIKE ?", (f'%{nome_topico}%',))
        comandos = cursor.fetchall()
        conn.close()
        if not comandos:
            raise HTTPException(status_code=404, detail="Nenhum comando encontrado para este tópico")
        return comandos
    except Exception as e:
        if not isinstance(e, HTTPException):
            raise HTTPException(status_code=500, detail=str(e))
        raise e

@app.post("/comandos", response_model=ComandoComId, status_code=201)
def create_comando(comando: Comando):
    """Adiciona um novo comando ao banco de dados."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO comandos (topico, nome, categoria, definicao, comando_exemplo, explicacao_pratica, dicas_de_uso)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (comando.topico, comando.nome, comando.categoria, comando.definicao, comando.comando_exemplo, comando.explicacao_pratica, comando.dicas_de_uso)
        )
        novo_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return {**comando.dict(), "id": novo_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao criar comando: {e}")

@app.put("/comandos/{comando_id}", response_model=ComandoComId)
def update_comando(comando_id: int, comando: Comando):
    """Atualiza um comando existente no banco de dados pelo seu ID."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE comandos SET
                topico = ?, nome = ?, categoria = ?, definicao = ?,
                comando_exemplo = ?, explicacao_pratica = ?, dicas_de_uso = ?
            WHERE id = ?
            """,
            (comando.topico, comando.nome, comando.categoria, comando.definicao, comando.comando_exemplo, comando.explicacao_pratica, comando.dicas_de_uso, comando_id)
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"Comando com ID {comando_id} não encontrado")

        conn.commit()
        conn.close()
        return {**comando.dict(), "id": comando_id}
    except Exception as e:
        if not isinstance(e, HTTPException):
            raise HTTPException(status_code=500, detail=f"Erro ao atualizar comando: {e}")
        raise e

@app.delete("/comandos/{comando_id}")
def delete_comando(comando_id: int):
    """Exclui um comando do banco de dados pelo seu ID."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM comandos WHERE id = ?", (comando_id,))

        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"Comando com ID {comando_id} não encontrado")

        conn.commit()
        conn.close()
        return {"mensagem": f"Comando com ID {comando_id} foi deletado com sucesso"}
    except Exception as e:
        if not isinstance(e, HTTPException):
            raise HTTPException(status_code=500, detail=f"Erro ao deletar comando: {e}")
        raise e
