import sqlite3
import psycopg2 # type: ignore[import]
import os
from dotenv import load_dotenv

def migrate_data():
    """
    Script para migrar dados de um banco SQLite ('comandos.db')
    para um banco de dados PostgreSQL (definido na DATABASE_URL).
    Este script LIMPA a tabela de destino antes de inserir.
    """
    
    load_dotenv()
    DATABASE_URL = os.getenv("DATABASE_URL")
    SQLITE_DB_PATH = "comandos.db" 

    if not DATABASE_URL:
        print("Erro: A variável de ambiente 'DATABASE_URL' não foi encontrada.")
        print("Certifique-se que seu arquivo .env está correto.")
        return

    # --- 1. EXTRAIR DADOS DO SQLITE ---
    print(f"Conectando ao banco SQLite em '{SQLITE_DB_PATH}'...")
    try:
        sqlite_conn = sqlite3.connect(SQLITE_DB_PATH)
        sqlite_conn.row_factory = sqlite3.Row
        sqlite_cursor = sqlite_conn.cursor()
        sqlite_cursor.execute("SELECT * FROM comandos")
        rows = sqlite_cursor.fetchall()
        
        data_to_migrate = [dict(row) for row in rows]
        
        sqlite_conn.close()
        
        if not data_to_migrate:
            print("Banco SQLite está vazio. Nenhuma migração necessária.")
            return
            
        print(f"Encontrados {len(data_to_migrate)} termos no SQLite. Prontos para migrar.")

    except Exception as e:
        print(f"Erro ao LER do banco SQLite: {e}")
        return

    # --- 2. CARREGAR DADOS NO POSTGRESQL ---
    pg_conn = None
    try:
        print("Conectando ao banco de dados PostgreSQL no Render...")
        pg_conn = psycopg2.connect(DATABASE_URL)
        pg_cursor = pg_conn.cursor()
        print("Limpando a tabela 'comandos' no PostgreSQL (TRUNCATE)...")
        pg_cursor.execute("TRUNCATE TABLE comandos RESTART IDENTITY")
        print("Tabela limpa. Iniciando inserção dos dados...")

        count = 0
        for item in data_to_migrate:
            query = """
                INSERT INTO comandos 
                (topico, nome, categoria, definicao, comando_exemplo, explicacao_pratica, dicas_de_uso)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            values = (
                item['topico'],
                item['nome'],
                item['categoria'],
                item['definicao'],
                item['comando_exemplo'],
                item['explicacao_pratica'],
                item['dicas_de_uso']
            )
            
            pg_cursor.execute(query, values)
            count += 1
        
        pg_conn.commit()
        print(f"Sucesso! Migrados {count} termos para o PostgreSQL.")

    except Exception as e:
        if pg_conn:
            pg_conn.rollback() 
        print(f"Erro ao ESCREVER no PostgreSQL: {e}")
    
    finally:
        if pg_cursor:
            pg_cursor.close()
        if pg_conn:
            pg_conn.close()
        print("Conexão com PostgreSQL fechada.")

if __name__ == "__main__":
    migrate_data()