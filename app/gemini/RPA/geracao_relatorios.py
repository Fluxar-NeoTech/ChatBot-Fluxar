import datetime

from matplotlib.dates import relativedelta
from app.gemini.tools.analista_tools import get_conn
import pandas as pd
import os
from pymongo import MongoClient
from dotenv import load_dotenv

from app.gemini.tools.relatorio_tools import gerar_sugestoes_estoque


# Dotenv
load_dotenv() 
mongo_uri = os.getenv("MONGO_URI")



# Perguntar se é melhor pegar do banco direto ou chamar o chatbot

# Busca no SQL os dados de movimentação de estoque filtrando pela data passada, industria, unidade, setor e produto
def buscar_dados_movimentacao(inicio, fim):
    conn = get_conn()
    query = f"""
        SELECT
            industria_id,
            unidade_id,
            setor_id,
            produto_id,
            SUM(CASE WHEN movimentacao = 'E' THEN volume_movimentado ELSE 0 END) AS entradas,
            SUM(CASE WHEN movimentacao = 'S' THEN volume_movimentado ELSE 0 END) AS saidas
        FROM historico_estoque
        WHERE data >= '{inicio}' AND data < '{fim}'
        GROUP BY industria_id, unidade_id, setor_id, produto_id;
    """
    df_mov = pd.read_sql(query, conn)
    conn.close()
    return df_mov



def deletar_relatorios_antigos(mes_ref, meses=6):
    """
    Deleta relatórios antigos no MongoDB.
    :param mes_ref: mês atual do relatório, string "YYYY-MM"
    :param meses: quantos meses anteriores deletar
    """
    client = MongoClient(mongo_uri)
    db = client["ChatBot"]
    col = db["relatorios_mensais"]

    # Converte mes_ref para datetime
    mes_atual = datetime.datetime.strptime(mes_ref, "%Y-%m")

    meses_para_deletar = [
        (mes_atual - relativedelta(months=i)).strftime("%Y-%m")
        for i in range(1, meses+1)
    ]

    resultado = col.delete_many({"mes_referencia": {"$in": meses_para_deletar}})
    client.close()
    print(f"{resultado.deleted_count} relatórios antigos deletados: {meses_para_deletar}")


    
# Busca a industria, unidade, setor e média da porcentagem de ocupação filtrando pela data passada, industria, unidade e setor
def buscar_dados_ocupacao(inicio, fim):
    conn = get_conn()

    query = f"""
        SELECT
            hc.industria_id,
            hc.unidade_id,
            p.setor_id,
            AVG(hc.porcentagem_ocupacao) AS ocupacao_media
        FROM historico_capacidade hc
        JOIN produto p ON hc.produto_id = p.id
        WHERE hc.data_completa >= '{inicio}' AND hc.data_completa < '{fim}'
        GROUP BY hc.industria_id, hc.unidade_id, p.setor_id;

    """
    df_mov = pd.read_sql(query, conn)
    conn.close()
    return df_mov


# Salva no Mongo
def salvar_relatorio(documento):
    client = MongoClient(mongo_uri)
    db = client["ChatBot"]
    col = db["relatorios_mensais"]
    col.insert_one(documento)
    client.close()


# Pega os dados do resumo necessários 

def gerar_relatorio_resumo():
    hoje = datetime.date.today()
    primeiro_dia_mes = datetime.date(hoje.year, hoje.month, 1)
    mes_anterior_fim = primeiro_dia_mes
    mes_anterior_inicio = (primeiro_dia_mes - datetime.timedelta(days=1)).replace(day=1)
    mes_ref = mes_anterior_inicio.strftime("%Y-%m")


   # Consulta PostgreSQL
    df_mov = buscar_dados_movimentacao(mes_anterior_inicio, mes_anterior_fim)
    df_ocp = buscar_dados_ocupacao(mes_anterior_inicio, mes_anterior_fim)

    df_completo = pd.merge(
        df_mov,
        df_ocp,
        on=["industria_id", "unidade_id", "setor_id"],
        how="left"
    )
    # Cálculo de métricas
    
    resumo = {
        "entradas_total_volume": float(df_mov["entradas"].sum()),
        "saidas_total_volume": float(df_mov["saidas"].sum()),
        "saldo_final_volume": float(df_mov["entradas"].sum() - df_mov["saidas"].sum()),
        "porcentagem_ocupacao_media": float(df_ocp["ocupacao_media"].mean()) if not df_ocp.empty else 0.0
    }

    return resumo, df_completo, mes_ref


# Gera um relatório e guarda no mongo
def gerar_relatorio_mensal(resumo_geral, df_completo, mes_ref, user_id):

    deletar_relatorios_antigos(mes_ref)


    # Sugestões do agente chatbot
    sugestoes = gerar_sugestoes_estoque(
        entradas_total_volume=resumo_geral["entradas_total_volume"],
        saidas_total_volume=resumo_geral["saidas_total_volume"],
        saldo_final_volume=resumo_geral["saldo_final_volume"],
        porcentagem_ocupacao_media=resumo_geral["porcentagem_ocupacao_media"],
        user_id=user_id
    )
    # 🔹 Documento completo para o MongoDB
    documento = {
        "mes_referencia": mes_ref,
        "gerado_em": datetime.datetime.now().isoformat(),
        "origem": "RPA automático",
        "resumo_geral": resumo_geral,
        "sugestoes_agente": sugestoes["sugestoes"],
        "metricas_mensais": {
            "por_industria": df_completo.to_dict(orient="records")
        }
    }

    salvar_relatorio(documento)
    print(f"✅ Relatório de {mes_ref} salvo no MongoDB com sugestões do agente.")

# resumo_geral, df_completo, mes_ref = gerar_relatorio_resumo()
# gerar_relatorio_mensal(resumo_geral, df_completo, mes_ref, user_id)
# descobrir como passar o user da rota para o agendador de tarefas