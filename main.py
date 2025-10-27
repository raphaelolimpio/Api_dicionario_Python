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

class ComandoAgrupado(BaseModel):
    """Modelo para o comando dentro da lista agrupada (sem o tópico e com id)."""
    id: int
    nome: Optional[str] = None
    categoria: Optional[str] = None
    definicao: Optional[str] = None
    comando_exemplo: Optional[str] = None
    explicacao_pratica: Optional[str] = None
    dicas_de_uso: Optional[str] = None

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

def get_db_connection():
    """Cria e retorna uma conexão com o banco de dados."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@app.get("/")
def get_root():
    """Endpoint raiz com mensagem de boas-vindas."""
    return {"mensagem": "Bem-vindo à API de Comandos! Use /docs para ver a documentação."}


# ---ENDPOINT PARA LISTAR TODOS OS COMANDOS ---
@app.get("/comandos", response_model=list[ComandoComId])
def get_todos_comandos(nome: Optional[str] = None):
    """Busca todos os comandos no banco de dados. (Público)
    poder ser filtrado por nome com o query param ?nome=...
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = "SELECT * FROM comandos"
        params = []
        if nome:
            query += "WHERE nome LIKE ?"
            params.append(f'%{nome}%')

        cursor.execute(query, params)
        comandos_rows = cursor.fetchall()
        comandos_list = [dict(row) for row in comandos_rows]
        
        conn.close()
        return comandos_list
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
# ---ENDPOINT PARA FILTRAR COMANDOS POR TÓPICO ---
@app.get("/comandos/topico/{nome_topico:path}", response_model=list[ComandoComId])
def get_comandos_por_topico(nome_topico: str, nome: Optional[str] = None):
    """Busca comandos filtrando por um tópico específico. (Público)
        Pode ser filtrado *tambem* por nome com o query param ?nome=...
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = "SELECT * FROM comandos WHERE topico LIKE ?"
        params = [f'%{nome_topico}%']

        if nome:
            query += " AND nome LIKE ?"
            params.append(f'%{nome}%')

        cursor.execute(query, params)
        comandos_rows = cursor.fetchall()
        comandos_list = [dict(row) for row in comandos_rows]
        if not comandos_rows:
            raise HTTPException(status_code=404, detail="Nenhum comando encontrado para este tópico")
        
        comandos_list = [dict(row) for row in comandos_rows]
        
        conn.close()
        return comandos_list
    except Exception as e:
        if not isinstance(e, HTTPException):
            raise HTTPException(status_code=500, detail=str(e))
        raise e
# ---ENDPOINT PARA LISTA DE TÓPICOS ---
@app.get("/topicos", response_model=list[str])
def get_topicos():
    """Busca todos os nomes de tópicos únicos no banco de dados."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT topico FROM comandos ORDER BY topico")
        topicos_rows = cursor.fetchall()
        topicos_list = [row[0] for row in topicos_rows]
        
        conn.close()
        return topicos_list
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
# ---ENDPOINT PARA COMANDOS AGRUPADOS ---   
@app.get("/comandos/agrupados", response_model=dict[str, list[ComandoAgrupado]])
def get_comandos_agrupados_por_topico():
    """Busca todos os comandos e os retorna agrupados por tópico."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM comandos ORDER BY topico, id")
        comandos_rows = cursor.fetchall()
        conn.close()
        comandos_agrupados = {}

        for row in comandos_rows:
            comando_dict = dict(row) 
            topico_nome = comando_dict.pop('topico') 
            comando_item = ComandoAgrupado(**comando_dict)
            if topico_nome not in comandos_agrupados:
                comandos_agrupados[topico_nome] = []
            comandos_agrupados[topico_nome].append(comando_item)
        
        return comandos_agrupados
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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

