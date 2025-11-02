import datetime
from datetime import timedelta
import psycopg
from pymongo import MongoClient
from dotenv import load_dotenv
import os

from app.gemini.tools.relatorio_tools import gerar_relatorio_mensal

# Carrega variáveis de ambiente
load_dotenv()
mongo_uri = os.getenv("MONGO_URI")
DATABASE_URL = os.getenv("DATABASE_URL")


def salvar_relatorio(documento):
    """
    Salva o relatório gerado no MongoDB.
    Abre a conexão, insere o documento na coleção 'relatorios_mensais' e fecha a conexão automaticamente.
    """
    with MongoClient(mongo_uri) as client:
        db = client["ChatBot"]
        col = db["relatorios_mensais"]
        col.insert_one(documento)


def buscar_ids_analistas():
    """
    Consulta o banco PostgreSQL e retorna a lista de IDs de todos os analistas cadastrados.
    """
    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM funcionario WHERE cargo = 'A';")
            ids_analistas = [row[0] for row in cur.fetchall()]
    print(f"Analistas encontrados: {len(ids_analistas)}")
    return ids_analistas


def gerar_relatorios_para_analistas():
    """
    Gera relatórios mensais para todos os analistas:
    1. Calcula o mês anterior como referência.
    2. Busca os IDs de todos os analistas.
    3. Para cada analista, chama a função que gera o relatório.
    4. Se houver dados, salva o relatório no MongoDB.
    5. Caso contrário, informa que não há dados disponíveis.
    6. Captura e exibe erros caso ocorram durante o processo.
    """
    hoje = datetime.date.today()
    mes_anterior_inicio = (hoje.replace(day=1) - timedelta(days=1)).replace(day=1)

    ids_analistas = buscar_ids_analistas()

    for user_id in ids_analistas:
        print(f"Gerando relatório para user_id={user_id}...")

        # Prepara os argumentos para a função de geração de relatório
        args = {
            "user_id": user_id,
            "ano_mes": mes_anterior_inicio.strftime("%Y-%m")
        }

        try:
            # Gera o relatório chamando a ferramenta externa
            relatorio = gerar_relatorio_mensal.invoke(args)

            if relatorio.get("status") == "sucesso":
                # Remove a chave 'status' e salva o relatório no MongoDB
                relatorio_para_salvar = relatorio.copy()
                relatorio_para_salvar.pop("status", None)
                salvar_relatorio(relatorio_para_salvar)
                print(f"Relatório do mês anterior gerado e salvo para user_id={user_id}.")
            else:
                # Caso não haja dados, exibe mensagem informativa
                print(f"Sem dados disponíveis para user_id={user_id}: {relatorio.get('mensagem')}")
        except Exception as e:
            # Captura erros de execução para cada analista
            print(f"Erro ao gerar relatório para user_id={user_id}: {e}")
