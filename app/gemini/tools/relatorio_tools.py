from langchain.tools import tool
from pymongo import MongoClient
import psycopg
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
import datetime
import pandas as pd
import os
from dotenv import load_dotenv
from bson import ObjectId

load_dotenv()

mongo_uri = os.getenv("MONGO_URI")
DATABASE_URL = os.getenv("DATABASE_URL")

def get_conn():
    return psycopg.connect(DATABASE_URL)

# ------------------------------------------------------ Sugestões -----------------------------------------------------
class SugestoesEstoqueArgs(BaseModel):
    entradas_total_volume: float
    saidas_total_volume: float
    saldo_final_volume: float
    porcentagem_ocupacao_media: float
    user_id: int

@tool("gerar_sugestoes_estoque", args_schema=SugestoesEstoqueArgs)
def gerar_sugestoes_estoque(
    entradas_total_volume: float,
    saidas_total_volume: float,
    saldo_final_volume: float,
    porcentagem_ocupacao_media: float,
    user_id: int
) -> Dict[str, any]:
    """
    Gera até 3 sugestões de melhoria e otimização do estoque.
    Retorna no formato padrão de relatório, sem salvar no banco.
    """
    from app.gemini.modelos.orquestrador import chamada_agente

    prompt = f"""
    Com base nos seguintes dados do estoque:
    Entradas: {entradas_total_volume}
    Saídas: {saidas_total_volume}
    Saldo: {saldo_final_volume}
    Ocupação média: {porcentagem_ocupacao_media}%
    
    Gere até 3 sugestões de melhoria e otimização do estoque.
    """

    respostas = chamada_agente(prompt, user_id=user_id)

    if isinstance(respostas, str):
        sugestoes_texto = respostas
    elif isinstance(respostas, dict) and "sugestoes" in respostas:
        sugestoes_texto = "; ".join(respostas["sugestoes"])
    elif isinstance(respostas, list):
        sugestoes_texto = "; ".join(respostas)
    else:
        sugestoes_texto = "Nenhuma sugestão disponível."

    documento = {
        "_id": ObjectId(),
        "mes_referencia": "sob demanda",
        "gerado_em": datetime.datetime.utcnow().isoformat() + "Z",
        "origem": "ChatBot sob demanda",
        "user_id": user_id,
        "resumo_geral": {
            "entradas_total_volume": entradas_total_volume,
            "saidas_total_volume": saidas_total_volume,
            "saldo_final_volume": saldo_final_volume,
            "porcentagem_ocupacao_media": porcentagem_ocupacao_media,
            "sugestoes_agente": sugestoes_texto,
            "status_operacional": None
        }
    }

    return documento


# ------------------------------------------------------ Relatórios -----------------------------------------------------
class GerarRelatorioPeriodoArgs(BaseModel):
    inicio: str
    fim: str
    user_id: int
    industria_id: Optional[int] = None
    unidade_id: Optional[int] = None
    setor_id: Optional[int] = None


@tool("gerar_relatorio_periodo", args_schema=GerarRelatorioPeriodoArgs)
def gerar_relatorio_periodo(inicio: str, fim: str, user_id: int,
                            industria_id: Optional[int] = None,
                            unidade_id: Optional[int] = None,
                            setor_id: Optional[int] = None) -> dict:
    """
    Gera relatório consolidado sob demanda e retorna no formato padrão (sem salvar no banco).
    """
    conn = get_conn()

    try:
        filters = [f"data >= '{inicio}' AND data < '{fim}'"]
        if industria_id: filters.append(f"industria_id = {industria_id}")
        if unidade_id: filters.append(f"unidade_id = {unidade_id}")
        if setor_id: filters.append(f"setor_id = {setor_id}")
        where = " AND ".join(filters)

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

        query_ocp = f"""
            SELECT
                hc.industria_id,
                hc.unidade_id,
                p.setor_id,
                AVG(hc.porcentagem_ocupacao) AS ocupacao_media
            FROM historico_capacidade hc
            JOIN produto p ON hc.produto_id = p.id
            JOIN funcionario f ON p.setor_id = f.setor_id
            WHERE hc.data_completa >= '{inicio}'
            AND hc.data_completa < '{fim}' AND f.id = {user_id}
            GROUP BY hc.industria_id, hc.unidade_id, p.setor_id;
        """
        df_ocp = pd.read_sql(query_ocp, conn)

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

        if df_mov.empty and df_ocp.empty:
            return {
                "status": "vazio",
                "mes_referencia": f"{inicio} a {fim}",
                "user_id": user_id,
                "mensagem": "Não há dados disponíveis para este período."
            }
        else:
            return {
                "status": "sucesso",
                "_id": ObjectId(),
                "mes_referencia": f"{inicio} a {fim}",
                "gerado_em": datetime.datetime.utcnow().isoformat() + "Z",
                "origem": "ChatBot sob demanda",
                "user_id": user_id,
                "resumo_geral": {
                    "entradas_total_volume": entradas,
                    "saidas_total_volume": saidas,
                    "saldo_final_volume": saldo,
                    "porcentagem_ocupacao_media": ocupacao,
                    "sugestoes_agente": None,
                    "status_operacional": status_op
                }
            }

    except Exception as e:
        print("Erro ao gerar relatório sob demanda:", e)
        return {"status": "error", "message": str(e)}

    finally:
        conn.close()


# ------------------------------------------------------ Comparação -----------------------------------------------------
class CompararRelatoriosMensaisArgs(BaseModel):
    relatorio_a: dict
    relatorio_b: dict
@tool("comparar_relatorios_mensais", args_schema=CompararRelatoriosMensaisArgs)
def comparar_relatorios_mensais(relatorio_a: dict, relatorio_b: dict) -> dict:
    """
    Compara dois relatórios no formato padrão (dicionários retornados por consulta_relatorio_mensal).
    Retorna um documento com as diferenças.
    """
    try:
        a = relatorio_a.get("resumo_geral", {})
        b = relatorio_b.get("resumo_geral", {})

        dif = {
            "entradas_total_volume": round(b.get("entradas_total_volume", 0) - a.get("entradas_total_volume", 0), 2),
            "saidas_total_volume": round(b.get("saidas_total_volume", 0) - a.get("saidas_total_volume", 0), 2),
            "saldo_final_volume": round(b.get("saldo_final_volume", 0) - a.get("saldo_final_volume", 0), 2),
            "porcentagem_ocupacao_media": round(b.get("porcentagem_ocupacao_media", 0) - a.get("porcentagem_ocupacao_media", 0), 2),
        }

        if relatorio_a.get("status") == "vazio" or relatorio_b.get("status") == "vazio":
            return {
                "status": "vazio",
                "mensagem": "Não é possível comparar: um dos relatórios não existe.",
                "relatorio_a": relatorio_a,
                "relatorio_b": relatorio_b
            }
        else:
            documento = {
                "_id": ObjectId(),
                "mes_referencia": f"Comparação: {relatorio_a.get('mes_referencia')} → {relatorio_b.get('mes_referencia')}",
                "gerado_em": datetime.datetime.utcnow().isoformat() + "Z",
                "origem": "ChatBot sob demanda",
                "user_id": relatorio_a.get("user_id"),  # opcional
                "resumo_geral": {
                    **dif,
                    "sugestoes_agente": "Analisar variações de desempenho entre os períodos.",
                    "status_operacional": "Comparativo"
                }
            }

            return documento
    except Exception as e:
        print("Erro ao comparar relatórios:", e)
        return {"status": "error", "message": str(e)}


# ------------------------------------------------------ Consulta (Mock) -----------------------------------------------------
class ConsultaRelatorioMensalArgs(BaseModel):
    mes_referencia: str
    user_id: int

@tool("consulta_relatorio_mensal", args_schema=ConsultaRelatorioMensalArgs)
def consulta_relatorio_mensal(mes_referencia: str, user_id: int) -> dict:
    """
    Retorna um relatório se existir; caso contrário, informa que não há relatório.
    O mes_referencia deve estar no formato YYYY-MM.
    """
    # Converte para YYYY-MM caso o usuário passe "Agosto 2025"
    try:
        dt = datetime.datetime.strptime(mes_referencia, "%B %Y")
        mes_referencia = dt.strftime("%Y-%m")  # Ex: "2025-08"
    except ValueError:
        # Assume que já está no formato correto YYYY-MM
        pass

    client = MongoClient(mongo_uri)
    db = client["ChatBot"]
    col = db["relatorios_mensais"]
    
    relatorio_real = col.find_one({
        "mes_referencia": mes_referencia,
        "user_id": user_id
    })
    client.close()

  
    print(relatorio_real)
    print(mes_referencia, user_id, relatorio_real)

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
TOOLS_RELATORIO = [
    gerar_sugestoes_estoque,
    gerar_relatorio_periodo,
    comparar_relatorios_mensais,
    consulta_relatorio_mensal
]
