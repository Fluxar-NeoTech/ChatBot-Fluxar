# Importações de bibliotecas padrão e de terceiros
import calendar
import json
from langchain.tools import tool
from pymongo import MongoClient
import psycopg
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
import pandas as pd
import os
from dotenv import load_dotenv
from bson import ObjectId
from bson import ObjectId
from app.gemini.tools.analista_tools import get_conn


load_dotenv()

# Define conexões com MongoDB e PostgreSQL
mongo_uri = os.getenv("MONGO_URI")
DATABASE_URL = os.getenv("DATABASE_URL")

# Função para criar conexão com PostgreSQL
def get_conn():
    return psycopg.connect(DATABASE_URL)



# ------------------------------------------------------ Relatórios -----------------------------------------------------
# Definição de modelo de entrada para gerar relatório mensal
class GerarRelatorioMensalArgs(BaseModel):
    user_id: int
    ano_mes: str  # formato "YYYY-MM"
    industria_id: Optional[int] = None
    unidade_id: Optional[int] = None
    setor_id: Optional[int] = None

# Ferramenta para gerar relatório mensal usando LangChain
@tool("gerar_relatorio_mensal", args_schema=GerarRelatorioMensalArgs)
def gerar_relatorio_mensal(user_id: int, ano_mes: str, 
                            industria_id: Optional[int] = None,
                            unidade_id: Optional[int] = None,
                            setor_id: Optional[int] = None) -> dict:
    """
    Gera relatório consolidado sob demanda e retorna no formato padrão.
    Consulta os dados com base apenas no mês/ano (YYYY-MM).
    """
    conn = get_conn()

    try:
        # Preparação dos filtros SQL com base nos parâmetros recebidos
        filters = [f"he.data::text LIKE '{ano_mes}%'"]
        if industria_id: filters.append(f"he.industria_id = {industria_id}")
        if unidade_id: filters.append(f"he.unidade_id = {unidade_id}")
        if setor_id: filters.append(f"he.setor_id = {setor_id}")
        where = " AND ".join(filters)

        # Consulta de movimentos de estoque
        query_mov = f"""
            SELECT
                he.industria_id,
                he.unidade_id,
                he.setor_id,
                SUM(CASE WHEN he.movimentacao = 'E' THEN he.volume_movimentado ELSE 0 END) AS entradas,
                SUM(CASE WHEN he.movimentacao = 'S' THEN he.volume_movimentado ELSE 0 END) AS saidas
            FROM historico_estoque he
            JOIN funcionario f 
                ON he.unidade_id = f.unidade_id AND he.setor_id = f.setor_id
            WHERE {where} AND f.id = {user_id}
            GROUP BY he.industria_id, he.unidade_id, he.setor_id;
        """
        df_mov = pd.read_sql(query_mov, conn)

        # Consulta de ocupação média
        query_ocp = f"""
            SELECT
                hc.industria_id,
                hc.unidade_id,
                p.setor_id,
                AVG(hc.porcentagem_ocupacao) AS ocupacao_media
            FROM historico_capacidade hc
            JOIN produto p ON hc.produto_id = p.id
            JOIN funcionario f ON p.setor_id = f.setor_id
            WHERE hc.data_completa::text LIKE '{ano_mes}%'
            AND f.id = {user_id}
            GROUP BY hc.industria_id, hc.unidade_id, p.setor_id;
        """
        df_ocp = pd.read_sql(query_ocp, conn)

        # Cálculos finais e definição de status operacional
        entradas = float(df_mov["entradas"].sum()) if not df_mov.empty else 0
        saidas = float(df_mov["saidas"].sum()) if not df_mov.empty else 0
        saldo = entradas - saidas
        ocupacao = float(df_ocp["ocupacao_media"].mean()) if not df_ocp.empty else 0.0

        if ocupacao >= 80:
            status_op = "Alto_Volume"
        elif ocupacao >= 50:
            status_op = "Operacional_Estável"
        else:
            status_op = "Baixo_Desempenho"

        # Retorna o relatório ou informa que não há dados
        if df_mov.empty and df_ocp.empty:
            return {
                "status": "vazio",
                "mes_referencia": ano_mes,
                "user_id": user_id,
                "mensagem": "Não há dados disponíveis para este período."
            }

        return {
            "status": "sucesso",
            "_id": ObjectId(),
            "mes_referencia": ano_mes,
            "gerado_em": datetime.utcnow().isoformat() + "Z",
            "user_id": user_id,
            "resumo_geral": {
                "entradas_total_volume": entradas,
                "saidas_total_volume": saidas,
                "saldo_final_volume": saldo,
                "porcentagem_ocupacao_media": ocupacao,
                "status_operacional": status_op
            }
        }

    except Exception as e:
        print("Erro ao gerar relatório sob demanda:", e)
        return {"status": "error", "message": str(e)}

    finally:
        conn.close()


# ------------------------------------------------------ Consulta -----------------------------------------------------
# Modelo para consultar relatório existente
class ConsultaRelatorioMensalArgs(BaseModel):
    mes_referencia: str
    user_id: int

# Ferramenta para consulta de relatório mensal
@tool("consulta_relatorio_mensal", args_schema=ConsultaRelatorioMensalArgs)
def consulta_relatorio_mensal(mes_referencia: str, user_id: int) -> dict:
    """
    Retorna um relatório se existir; caso contrário, informa que não há relatório.
    """
    # Converte nomes de mês para formato YYYY-MM se necessário
    try:
        dt = datetime.strptime(mes_referencia, "%B %Y")
        mes_referencia = dt.strftime("%Y-%m")
    except ValueError:
        pass

    client = MongoClient(mongo_uri)
    db = client["ChatBot"]
    col = db["relatorios_mensais"]
    
    # Consulta o relatório no mongo com o filtros necessários
    relatorio_real = col.find_one({
        "mes_referencia": mes_referencia,
        "user_id": user_id
    })
    client.close()

    # Retorna relatório ou mensagem de vazio
    if relatorio_real:
        return {
            "status": "sucesso",
            "mes_referencia": mes_referencia,
            "user_id": user_id,
            "relatorio": relatorio_real
        }
    else:
        return {
            "status": "vazio",
            "mes_referencia": mes_referencia,
            "user_id": user_id,
            "mensagem": f"Não há relatório cadastrado para {mes_referencia}."
        }

# ------------------------------------------------------ Registro Geral -----------------------------------------------------
# Lista com todas as ferramentas relacionadas a relatórios
TOOLS_RELATORIO = [
    gerar_relatorio_mensal,
    consulta_relatorio_mensal
]
