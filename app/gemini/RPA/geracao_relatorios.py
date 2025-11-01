import datetime
from app.gemini.tools.analista_tools import get_conn
import pandas as pd
import os
from pymongo import MongoClient
from dotenv import load_dotenv
from app.gemini.tools.relatorio_tools import gerar_sugestoes_estoque


# ==========================================
# Configuração inicial
# ==========================================
load_dotenv()
mongo_uri = os.getenv("MONGO_URI")


# ==========================================
# Funções SQL
# ==========================================
def buscar_dados_movimentacao(inicio, fim, user_id):
    conn = get_conn()
    query = f"""
        SELECT
            he.industria_id,
            he.unidade_id,
            he.setor_id,
            he.produto_id,
            SUM(CASE WHEN he.movimentacao = 'E' THEN he.volume_movimentado ELSE 0 END) AS entradas,
            SUM(CASE WHEN he.movimentacao = 'S' THEN he.volume_movimentado ELSE 0 END) AS saidas
        FROM historico_estoque he
        JOIN funcionario f 
            ON he.unidade_id = f.unidade_id 
           AND he.setor_id = f.setor_id
        WHERE data >= '{inicio}' 
          AND data < '{fim}' 
          AND f.id = {user_id}
        GROUP BY he.industria_id, he.unidade_id, he.setor_id, he.produto_id;
    """
    df_mov = pd.read_sql(query, conn)
    conn.close()
    return df_mov


def buscar_dados_ocupacao(inicio, fim, user_id):
    conn = get_conn()
    query = f"""
        SELECT
            hc.industria_id,
            hc.unidade_id,
            p.setor_id,
            AVG(hc.porcentagem_ocupacao) AS ocupacao_media
        FROM historico_capacidade hc
        JOIN produto p ON hc.produto_id = p.id
        JOIN funcionario f ON hc.unidade_id = f.unidade_id AND p.setor_id = f.setor_id
        WHERE hc.data_completa >= '{inicio}'
          AND hc.data_completa < '{fim}'
          AND f.id = {user_id}
        GROUP BY hc.industria_id, hc.unidade_id, p.setor_id;
    """
    df_ocp = pd.read_sql(query, conn)
    conn.close()
    return df_ocp


# ==========================================
# Função para salvar no MongoDB
# ==========================================
def salvar_relatorio(documento):
    client = MongoClient(mongo_uri)
    db = client["ChatBot"]
    col = db["relatorios_mensais"]
    col.insert_one(documento)
    client.close()


# ==========================================
# Geração dos dados consolidados
# ==========================================
def gerar_relatorio_resumo(user_id):
    hoje = datetime.date.today()
    primeiro_dia_mes = datetime.date(hoje.year, hoje.month, 1)
    mes_anterior_fim = primeiro_dia_mes
    mes_anterior_inicio = (primeiro_dia_mes - datetime.timedelta(days=1)).replace(day=1)
    
    # 🔹 Agora o mês de referência é o nome do mês, ex: "Outubro"
    mes_ref = mes_anterior_inicio.strftime("%B").capitalize()

    # Consulta PostgreSQL
    df_mov = buscar_dados_movimentacao(mes_anterior_inicio, mes_anterior_fim, user_id)
    df_ocp = buscar_dados_ocupacao(mes_anterior_inicio, mes_anterior_fim, user_id)

    # Merge dos resultados
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


# ==========================================
# Criação e gravação do relatório
# ==========================================
def gerar_relatorio_mensal(resumo_geral, mes_ref, user_id):
    # Sugestões e status gerados pelo agente
    sugestoes, status_operacional = gerar_sugestoes_estoque(
        entradas_total_volume=resumo_geral["entradas_total_volume"],
        saidas_total_volume=resumo_geral["saidas_total_volume"],
        saldo_final_volume=resumo_geral["saldo_final_volume"],
        porcentagem_ocupacao_media=resumo_geral["porcentagem_ocupacao_media"],
        user_id=user_id
    )

    # Documento final conforme modelo
    documento = {
        "mes_referencia": mes_ref,
        "gerado_em": datetime.datetime.now().isoformat(),
        "origem": "RPA",
        "user_id": user_id,
        "resumo_geral": {
            "entradas_total_volume": resumo_geral["entradas_total_volume"],
            "saidas_total_volume": resumo_geral["saidas_total_volume"],
            "saldo_final_volume": resumo_geral["saldo_final_volume"],
            "porcentagem_ocupacao_media": resumo_geral["porcentagem_ocupacao_media"],
            "sugestoes_agente": sugestoes,
            "status_operacional": status_operacional
        }
    }

    salvar_relatorio(documento)
    print(f"✅ Relatório de {mes_ref} salvo no MongoDB com sucesso para user_id={user_id}.")
