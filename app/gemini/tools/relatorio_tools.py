from langchain.tools import tool
import psycopg2
from pydantic import BaseModel, Field
from typing import List, Dict
import datetime 
from typing import Optional 
import pandas as pd
import os
from dotenv import load_dotenv
from pymongo import MongoClient


load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")  

def get_conn():
    return psycopg2.connect(DATABASE_URL)

# ---------------------------------------------- Sugestões de Melhorias -----------------------------------------------
class SugestoesEstoqueArgs(BaseModel):
    entradas_total_volume: float = Field(..., description="Total de entradas do estoque no período")
    saidas_total_volume: float = Field(..., description="Total de saídas do estoque no período")
    saldo_final_volume: float = Field(..., description="Saldo final de estoque no período")
    porcentagem_ocupacao_media: float = Field(..., description="Porcentagem média de ocupação do estoque")
    user_id: str = Field(..., description="ID do usuário para sessão do agente")  # adiciona user_id

@tool("gerar_sugestoes_estoque", args_schema=SugestoesEstoqueArgs)
def gerar_sugestoes_estoque(
    entradas_total_volume: float,
    saidas_total_volume: float,
    saldo_final_volume: float,
    porcentagem_ocupacao_media: float,
    user_id: str
) -> Dict[str, List[str]]:
    """
    Recebe os valores principais do resumo do estoque e retorna até 3 sugestões do agente.
    """
    prompt = f"""
    Com base nos seguintes dados do estoque:
    Entradas: {entradas_total_volume}
    Saídas: {saidas_total_volume}
    Saldo: {saldo_final_volume}
    Ocupação média: {porcentagem_ocupacao_media}%
    
    Gere até 3 sugestões de melhoria e otimização do estoque.
    """
    from app.gemini.modelos.orquestrador import chamada_agente

    # Chama a função de agente já existente
    respostas = chamada_agente(prompt, user_id=user_id)

    # Se o agente retornar uma string simples, transforma em lista
    if isinstance(respostas, str):
        respostas = [respostas]

    # Se retornar dict com 'sugestoes', usa
    elif isinstance(respostas, dict):
        respostas = respostas.get("sugestoes", [])

    return {"sugestoes": respostas}





# -------------------------------------- Geração de Relatórios Pelo ChatBot -------------------------------------------
class GerarRelatorioPeriodoArgs(BaseModel):
    inicio: str = Field(..., description="Data inicial do período (YYYY-MM-DD)")
    fim: str = Field(..., description="Data final do período (YYYY-MM-DD)")
    industria_id: Optional[int] = Field(None, description="Filtrar por ID da indústria (opcional)")
    unidade_id: Optional[int] = Field(None, description="Filtrar por ID da unidade (opcional)")
    setor_id: Optional[int] = Field(None, description="Filtrar por ID do setor (opcional)")


@tool("gerar_relatorio_periodo", args_schema=GerarRelatorioPeriodoArgs)
def gerar_relatorio_periodo(
    inicio: str,
    fim: str,
    industria_id: Optional[int] = None,
    unidade_id: Optional[int] = None,
    setor_id: Optional[int] = None,
) -> dict:
    """
    Gera um relatório de movimentação e ocupação de estoque por período.
    NÃO salva no MongoDB — apenas retorna os dados consolidados para o chat.
    """
    conn = get_conn()

    try:
        filters = [f"data >= '{inicio}' AND data < '{fim}'"]
        if industria_id:
            filters.append(f"industria_id = {industria_id}")
        if unidade_id:
            filters.append(f"unidade_id = {unidade_id}")
        if setor_id:
            filters.append(f"setor_id = {setor_id}")
        where = " AND ".join(filters)

        # Movimentação de estoque
        query_mov = f"""
            SELECT
                industria_id, unidade_id, setor_id, produto_id,
                SUM(CASE WHEN movimentacao = 'E' THEN volume_movimentado ELSE 0 END) AS entradas,
                SUM(CASE WHEN movimentacao = 'S' THEN volume_movimentado ELSE 0 END) AS saidas
            FROM historico_estoque
            WHERE {where}
            GROUP BY industria_id, unidade_id, setor_id, produto_id;
        """
        df_mov = pd.read_sql(query_mov, conn)

        # Ocupação média
        query_ocp = f"""
            SELECT
                hc.industria_id,
                hc.unidade_id,
                p.setor_id,
                AVG(hc.porcentagem_ocupacao) AS ocupacao_media
            FROM historico_capacidade hc
            JOIN produto p ON hc.produto_id = p.id
            WHERE hc.data_completa >= '{inicio}'
            AND hc.data_completa < '{fim}'
            GROUP BY
                hc.industria_id,
                hc.unidade_id,
                p.setor_id;
    """
        df_ocp = pd.read_sql(query_ocp, conn)

        # Merge final
        df_completo = pd.merge(df_mov, df_ocp, on=["industria_id", "unidade_id", "setor_id"], how="left")

        resumo_geral = {
            "entradas_total_volume": float(df_mov["entradas"].sum()),
            "saidas_total_volume": float(df_mov["saidas"].sum()),
            "saldo_final_volume": float(df_mov["entradas"].sum() - df_mov["saidas"].sum()),
            "porcentagem_ocupacao_media": float(df_ocp["ocupacao_media"].mean()) if not df_ocp.empty else 0.0,
        }

        documento = {
            "mes_referencia": f"{inicio} a {fim}",
            "gerado_em": datetime.datetime.now().isoformat(),
            "origem": "Chatbot sob demanda",
            "resumo_geral": resumo_geral,
            "sugestoes_agente": None,
            "metricas_mensais": {"por_industria": df_completo.to_dict(orient="records")},
        }

        return {"status": "ok", "relatorio": documento}

    except Exception as e:
        print("Erro ao gerar relatório sob demanda:", e)
        return {"status": "error", "message": str(e)}

    finally:
        conn.close()





# ------------------------------------------------- Comparação Relatórios ------------------------------------------

load_dotenv()
mongo_uri = os.getenv("MONGO_URI")



class CompararRelatoriosMensaisArgs(BaseModel):
    mes_a: str = Field(..., description="Mês de referência A (ex: junho)")
    mes_b: str = Field(..., description="Mês de referência B (ex: julho)")


@tool("comparar_relatorios_mensais", args_schema=CompararRelatoriosMensaisArgs)
def comparar_relatorios_mensais(mes_a: str, mes_b: str) -> dict:
    """
    Compara dois relatórios mensais armazenados no MongoDB.
    Retorna diferenças em volume, ocupação e saldo.
    """
    client = MongoClient(mongo_uri)
    db = client["NeoTechTest"]
    col = db["test"]

    try:
        rel_a = col.find_one({"mes_referencia": mes_a})
        rel_b = col.find_one({"mes_referencia": mes_b})

        if not rel_a or not rel_b:
            return {"status": "error", "message": "Um ou ambos os relatórios não foram encontrados no banco."}

        dif = {
            "entradas_total_volume": round(rel_b["resumo_geral"]["entradas_total_volume"] - rel_a["resumo_geral"]["entradas_total_volume"], 2),
            "saidas_total_volume": round(rel_b["resumo_geral"]["saidas_total_volume"] - rel_a["resumo_geral"]["saidas_total_volume"], 2),
            "saldo_final_volume": round(rel_b["resumo_geral"]["saldo_final_volume"] - rel_a["resumo_geral"]["saldo_final_volume"], 2),
            "porcentagem_ocupacao_media": round(rel_b["resumo_geral"]["porcentagem_ocupacao_media"] - rel_a["resumo_geral"]["porcentagem_ocupacao_media"], 2),
        }

        return {
            "status": "ok",
            "comparacao": {
                "periodo_a": mes_a,
                "periodo_b": mes_b,
                "diferencas": dif,
                "gerado_em": datetime.datetime.now().isoformat(),
            },
        }

    except Exception as e:
        print("Erro ao comparar relatórios:", e)
        return {"status": "error", "message": str(e)}

    finally:
        client.close()




class ConsultaRelatorioMensalArgs(BaseModel):
    mes_referencia: Optional[str] = Field(None, description="Mês de referência, ex: 'junho'")

@tool("consulta_relatorio_mensal", args_schema=ConsultaRelatorioMensalArgs)
def consulta_relatorio_mensal(
    mes_referencia: str,
) -> dict:
    """
    Consulta um relatório mensal armazenado no banco de dados MongoDB.

    - Só pode ser consultado por `mes_referencia` (ex: 'junho').
    - Retorna o documento completo com resumo, métricas e sugestões do agente.
    - Apenas leitura, sem comparação.
    """


    MONGO_URI = os.getenv("MONGO_URI")
    

    try:
        client = MongoClient(MONGO_URI)
        db = client["NeoTechTest"]
        collection = db["test"]

        filtro = {}
        if mes_referencia:
            filtro["mes_referencia"] = mes_referencia
        else:
            return {"status": "error", "message": "Informe 'mes_referencia' ou 'report_id'."}

        documento = collection.find_one(filtro, {"_id": 0})

        if not documento:

            return {"status": "not_found", "message": "Nenhum relatório encontrado para o filtro informado."}

        return {
            "status": "ok",
            "mensagem": f"Relatório mensal encontrado para {mes_referencia}.",
            "relatorio": documento
        }

    except Exception as e:
        print(e)
        return {"status": "error", "message": str(e)}
        

    finally:
        client.close()



TOOLS_RELATORIO = [gerar_sugestoes_estoque, gerar_relatorio_periodo, comparar_relatorios_mensais, consulta_relatorio_mensal]