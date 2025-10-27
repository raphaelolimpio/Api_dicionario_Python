import sqlite3
from fastapi import FastAPI, HTTPException, Security, Depends
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv
from pathlib import Path

# --- NOVAS IMPORTAÇÕES ---
import psycopg2  # type: ignore[import]
from psycopg2.extras import RealDictCursor  # type: ignore[import]
# -------------------------
# Carrega variáveis de ambiente (como API_KEY)
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

# --- CONFIGURAÇÃO DAS VARIÁVEIS ---
# A API vai ler a URL do banco de dados do ambiente do Render
DATABASE_URL = os.getenv("DATABASE_URL")
API_KEY = os.getenv("API_KEY")
API_KEY_NAME = os.getenv("API_KEY_NAME", "X-API-Key")

API_KEY = API_KEY.strip(" '\"") if API_KEY else None
API_KEY_NAME = API_KEY_NAME.strip(" '\"") if API_KEY_NAME else "X-API-Key"

# (Modelos Pydantic 'Comando', 'ComandoComId', 'ComandoAgrupado' continuam os mesmos)
class Comando(BaseModel):
    topico: str
    nome: Optional[str] = None
    categoria: Optional[str] = None
    definicao: Optional[str] = None
    comando_exemplo: Optional[str] = None
    explicacao_pratica: Optional[str] = None
    dicas_de_uso: Optional[str] = None

class ComandoComId(Comando):
    id: int

class ComandoAgrupado(BaseModel):
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
    if api_key_header == API_KEY:
        return api_key_header
    else:
        raise HTTPException(
            status_code=401,
            detail="Chave de API inválida ou ausente.",
        )

# --- FUNÇÃO DE CONEXÃO ATUALIZADA ---
def get_db_connection():
    """Cria e retorna uma conexão com o banco de dados PostgreSQL."""
    try:
        conn = psycopg2.connect(DATABASE_URL)
        # RealDictCursor faz o psycopg2 retornar dicionários (como o 'sqlite3.Row')
        conn.cursor_factory = RealDictCursor 
        return conn
    except Exception as e:
        print(f"Erro ao conectar ao PostgreSQL: {e}")
        raise HTTPException(status_code=500, detail="Não foi possível conectar ao banco de dados.")

@app.get("/")
def get_root():
    return {"mensagem": "Bem-vindo à API de Comandos! Use /docs para ver a documentação."}


# --- ENDPOINTS ATUALIZADOS PARA PostgreSQL (usando %s) ---

@app.get("/comandos", response_model=list[ComandoComId])
def get_todos_comandos(nome: Optional[str] = None):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = "SELECT * FROM comandos"
        params = []
        if nome:
            query += " WHERE nome LIKE %s" # <-- Mudança de ? para %s
            params.append(f'%{nome}%')
        
        query += " ORDER BY topico, nome" # Boa prática adicionar ordenação

        cursor.execute(query, tuple(params)) # Passa params como tupla
        comandos_list = cursor.fetchall()
        
        cursor.close()
        conn.close()
        return comandos_list
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/comandos/topico/{nome_topico:path}", response_model=list[ComandoComId])
def get_comandos_por_topico(nome_topico: str, nome: Optional[str] = None):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        query = "SELECT * FROM comandos WHERE topico LIKE %s" # <-- Mudança
        params = [f'%{nome_topico}%']

        if nome:
            query += " AND nome LIKE %s" # <-- Mudança
            params.append(f'%{nome}%')

        cursor.execute(query, tuple(params))
        comandos_list = cursor.fetchall()
        
        # (Removi a checagem 404 para ser consistente com get_todos_comandos)

        cursor.close()
        conn.close()
        return comandos_list
    except Exception as e:
        if not isinstance(e, HTTPException):
            raise HTTPException(status_code=500, detail=str(e))
        raise e

@app.get("/topicos", response_model=list[str])
def get_topicos():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT topico FROM comandos ORDER BY topico")
        topicos_rows = cursor.fetchall()
        topicos_list = [row['topico'] for row in topicos_rows] # Acessa por chave
        
        cursor.close()
        conn.close()
        return topicos_list
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
  
@app.get("/comandos/agrupados", response_model=dict[str, list[ComandoAgrupado]])
def get_comandos_agrupados_por_topico():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM comandos ORDER BY topico, id")
        comandos_rows = cursor.fetchall()
        
        comandos_agrupados = {}
        for row in comandos_rows:
            comando_dict = dict(row) 
            topico_nome = comando_dict.pop('topico') 
            comando_item = ComandoAgrupado(**comando_dict)
            if topico_nome not in comandos_agrupados:
                comandos_agrupados[topico_nome] = []
            comandos_agrupados[topico_nome].append(comando_item)
        
        cursor.close()
        conn.close()
        return comandos_agrupados
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/comandos", response_model=ComandoComId, status_code=201)
def create_comando(comando: Comando, api_key: str = Depends(get_api_key)):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = """
            INSERT INTO comandos (topico, nome, categoria, definicao, comando_exemplo, explicacao_pratica, dicas_de_uso)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """ # <-- Mudança para %s e "RETURNING id"

        params = (comando.topico, comando.nome, comando.categoria, comando.definicao, comando.comando_exemplo, comando.explicacao_pratica, comando.dicas_de_uso)
        
        cursor.execute(query, params)
        novo_id_row = cursor.fetchone() # Pega o 'id' retornado
        novo_id = novo_id_row['id']
        
        conn.commit()
        cursor.close()
        conn.close()
        return {**comando.dict(), "id": novo_id}
    except Exception as e:
        conn.rollback() # Desfaz a transação em caso de erro
        raise HTTPException(status_code=500, detail=f"Erro ao criar comando: {e}")

@app.put("/comandos/{comando_id}", response_model=ComandoComId)
def update_comando(comando_id: int, comando: Comando, api_key: str = Depends(get_api_key)):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = """
            UPDATE comandos SET
                topico = %s, nome = %s, categoria = %s, definicao = %s,
                comando_exemplo = %s, explicacao_pratica = %s, dicas_de_uso = %s
            WHERE id = %s
            """ # <-- Mudança
            
        params = (comando.topico, comando.nome, comando.categoria, comando.definicao, comando.comando_exemplo, comando.explicacao_pratica, comando.dicas_de_uso, comando_id)

        cursor.execute(query, params)
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"Comando com ID {comando_id} não encontrado")
        
        conn.commit()
        cursor.close()
        conn.close()
        return {**comando.dict(), "id": comando_id}
    except Exception as e:
        conn.rollback()
        if not isinstance(e, HTTPException):
            raise HTTPException(status_code=500, detail=f"Erro ao atualizar comando: {e}")
        raise e

@app.delete("/comandos/{comando_id}")
def delete_comando(comando_id: int, api_key: str = Depends(get_api_key)):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM comandos WHERE id = %s", (comando_id,)) # <-- Mudança
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"Comando com ID {comando_id} não encontrado")
        
        conn.commit()
        cursor.close()
        conn.close()
        return {"mensagem": f"Comando com ID {comando_id} foi deletado com sucesso"}
    except Exception as e:
        conn.rollback()
        if not isinstance(e, HTTPException):
            raise HTTPException(status_code=500, detail=f"Erro ao deletar comando: {e}")
        raise e