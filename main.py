import sqlite3
from fastapi import FastAPI, HTTPException, Security, Depends
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware



from dotenv import load_dotenv
from pathlib import Path
import os

env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)



DB_PATH = os.getenv("DB_PATH", "comandos.db")
API_KEY = os.getenv("API_KEY")
API_KEY_NAME = os.getenv("API_KEY_NAME", "X-API-Key")

DB_PATH = DB_PATH.strip(" '\"") if DB_PATH else "comandos.db"
API_KEY = API_KEY.strip(" '\"") if API_KEY else None
API_KEY_NAME = API_KEY_NAME.strip(" '\"") if API_KEY_NAME else "X-API-Key"

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def get_api_key(api_key_header: str = Security(api_key_header)):
    """Verifica se a chave da API enviada no header é válida."""
    if api_key_header == API_KEY:
        return api_key_header
    else:
        raise HTTPException(
            status_code=401,
            detail="Chave de API inválida ou ausente. Forneça a chave no header 'X-API-Key'.",
        )

# --- Funções do Banco de Dados ---
def get_db_connection():
    """Cria e retorna uma conexão com o banco de dados."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# --- Endpoints da API (Operações CRUD) ---

@app.get("/")
def get_root():
    """Endpoint raiz com mensagem de boas-vindas."""
    return {"mensagem": "Bem-vindo à API de Comandos! Use /docs para ver a documentação."}

# --- READ (Ler - Público) ---

@app.get("/comandos", response_model=list[ComandoComId])
def get_todos_comandos():
    """Busca todos os comandos no banco de dados. (Público)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM comandos")
        
        # Converte o resultado em uma lista de dicionários
        comandos_rows = cursor.fetchall()
        comandos_list = [dict(row) for row in comandos_rows]
        
        conn.close()
        return comandos_list
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/comandos/topico/{nome_topico}", response_model=list[ComandoComId])
def get_comandos_por_topico(nome_topico: str):
    """Busca comandos filtrando por um tópico específico. (Público)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM comandos WHERE topico LIKE ?", (f'%{nome_topico}%',))
        
        # Converte o resultado em uma lista de dicionários
        comandos_rows = cursor.fetchall()
        if not comandos_rows:
            raise HTTPException(status_code=404, detail="Nenhum comando encontrado para este tópico")
        
        comandos_list = [dict(row) for row in comandos_rows]
        
        conn.close()
        return comandos_list
    except Exception as e:
        if not isinstance(e, HTTPException):
            raise HTTPException(status_code=500, detail=str(e))
        raise e

# --- CREATE (Criar - Protegido) ---

@app.post("/comandos", response_model=ComandoComId, status_code=201)
def create_comando(comando: Comando, api_key: str = Depends(get_api_key)):
    """Adiciona um novo comando ao banco de dados. (Protegido por API Key)"""
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

# --- UPDATE (Atualizar - Protegido) ---

@app.put("/comandos/{comando_id}", response_model=ComandoComId)
def update_comando(comando_id: int, comando: Comando, api_key: str = Depends(get_api_key)):
    """Atualiza um comando existente no banco de dados. (Protegido por API Key)"""
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

# --- DELETE (Excluir - Protegido) ---

@app.delete("/comandos/{comando_id}")
def delete_comando(comando_id: int, api_key: str = Depends(get_api_key)):
    """Exclui um comando do banco de dados. (Protegido por API Key)"""
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

