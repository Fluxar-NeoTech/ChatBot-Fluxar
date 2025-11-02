import os
from typing import Optional
from dotenv import load_dotenv
import psycopg
from langchain.tools import tool
from pydantic import BaseModel, Field
import datetime as _dt

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

def get_conn():
    return psycopg.connect(DATABASE_URL)


# ==========================================================
# TOOL 1 — Query Movimentações de Estoque
# ==========================================================

# Define os argumentos aceitos pela ferramenta de consulta de movimentações

class QueryMovimentacaoEstoqueArgs(BaseModel):
    user_id: int = Field(..., description="ID do usuário (funcionário logado)")
    text: Optional[str] = Field(None, description="Texto genérico para buscar em produto, setor ou unidade")
    movimentacao: Optional[str] = Field(None, description="Tipo de movimentação: 'E' (entrada) ou 'S' (saída)")
    date_local: Optional[str] = Field(None, description="Data específica local (YYYY-MM-DD)")
    date_from_local: Optional[str] = Field(None, description="Data inicial do intervalo (YYYY-MM-DD)")
    date_to_local: Optional[str] = Field(None, description="Data final do intervalo (YYYY-MM-DD)")
    industria_nome: Optional[str] = Field(None, description="Nome da indústria")
    unidade_nome: Optional[str] = Field(None, description="Nome da unidade")
    setor_nome: Optional[str] = Field(None, description="Nome do setor")
    produto_nome: Optional[str] = Field(None, description="Nome do produto")
    produto_sku: Optional[str] = Field(None, description="SKU do produto")
    limit: int = Field(20, description="Limite máximo de resultados (padrão: 20)")


# Função que realiza a consulta de movimentações de estoque com base nos filtros informados
@tool("query_movimentacao_estoque", args_schema=QueryMovimentacaoEstoqueArgs)
def query_movimentacao_estoque(
    user_id: int,
    text: Optional[str] = None,
    movimentacao: Optional[str] = None,
    date_local: Optional[str] = None,
    date_from_local: Optional[str] = None,
    date_to_local: Optional[str] = None,
    industria_nome: Optional[str] = None,
    unidade_nome: Optional[str] = None,
    setor_nome: Optional[str] = None,
    produto_nome: Optional[str] = None,
    produto_sku: Optional[str] = None,
    limit: int = 20,
) -> dict:
    """
    Consulta o histórico de movimentações de estoque (historico_estoque),
    filtrando por nomes e SKU do produto, e mantendo restrição de acesso por user_id.
    """
    conn = get_conn()
    cur = conn.cursor()

    try:
        filters = []
        params = []

        # Filtro por user_id
        filters.append("f.id = %s")
        params.append(user_id)

        # Texto genérico
        if text:
            filters.append("(p.nome ILIKE %s OR s.nome ILIKE %s)")
            params.extend([f"%{text}%", f"%{text}%"])

        # Movimentação
        if movimentacao:
            filters.append("h.movimentacao = %s")
            params.append(movimentacao.upper())

        # Filtrar por nomes
        if industria_nome:
            filters.append("i.nome ILIKE %s")
            params.append(f"%{industria_nome}%")
        if unidade_nome:
            filters.append("u.nome ILIKE %s")
            params.append(f"%{unidade_nome}%")
        if setor_nome:
            filters.append("s.nome ILIKE %s")
            params.append(f"%{setor_nome}%")
        if produto_nome:
            filters.append("p.nome ILIKE %s")
            params.append(f"%{produto_nome}%")
        if produto_sku:
            filters.append("l.sku ILIKE %s")
            params.append(f"%{produto_sku}%")

        # Datas
        if date_local:
            filters.append("h.data >= %s::date AND h.data < (%s::date + INTERVAL '1 day')")
            params.extend([date_local, date_local])
        else:
            if date_from_local:
                filters.append("h.data >= %s::date")
                params.append(date_from_local)
            if date_to_local:
                filters.append("h.data < (%s::date + INTERVAL '1 day')")
                params.append(date_to_local)

        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""

        # Ordenação
        order_clause = (
            "ORDER BY h.data ASC"
            if date_from_local or date_to_local
            else "ORDER BY h.data DESC"
        )

        # Consulta SQL com join em lote para pegar SKU
        query = f"""
            SELECT
                h.id,
                h.data AT TIME ZONE 'America/Sao_Paulo' AS data_local,
                h.movimentacao,
                h.volume_movimentado,
                p.nome AS produto,
                l.sku AS produto_sku,
                s.nome AS setor,
                u.nome AS unidade,
                i.nome AS industria
            FROM historico_estoque h
            JOIN produto p ON h.produto_id = p.id
            JOIN lote l ON l.produto_id = p.id
            JOIN setor s ON h.setor_id = s.id
            JOIN unidade u ON h.unidade_id = u.id
            JOIN industria i ON h.industria_id = i.id
            JOIN funcionario f ON f.setor_id = s.id AND f.unidade_id = u.id
            {where_clause}
            {order_clause}
            LIMIT {limit};
        """

        cur.execute(query, tuple(params))
        rows = cur.fetchall()

        # Executa a consulta SQL e organiza os resultados em formato de dicionário
        # Retorna os resultados ou mensagem de erro
        
        results = [
            {
                "id": r[0],
                "data_local": r[1].isoformat() if r[1] else None,
                "movimentacao": "Entrada" if r[2] == 'E' else "Saída",
                "volume_movimentado": float(r[3]),
                "produto": r[4],
                "produto_sku": r[5],
                "setor": r[6],
                "unidade": r[7],
                "industria": r[8],
            }
            for r in rows
        ]

        return {"status": "ok", "results": results}

    except Exception as e:
        conn.rollback()
        print("Erro ao executar query_stock_movements:", e)
        return {"status": "error", "message": str(e)}

    finally:
        cur.close()
        conn.close()

# ==========================================================
# TOOL 2 — Query Descrição de Setor
# ==========================================================

class QuerySetorDescricaoArgs(BaseModel):
    user_id: int = Field(..., description="ID do usuário (funcionário logado)")
    nome_setor: str = Field(..., description="Nome do setor a ser consultado")


@tool("query_setor_descricao", args_schema=QuerySetorDescricaoArgs)
def query_setor_descricao(user_id: int, nome_setor: str) -> dict:
    """
    Retorna a descrição de setores cujo nome contenha o texto informado,
    **somente** se o funcionário (user_id) tiver acesso a esse setor.
    """
    conn = get_conn()
    cur = conn.cursor()

    try:

        # Monta a query SQL para buscar setores que o usuário tem acesso
        # e cujo nome contenha o texto informado (case-insensitive)
        query = """
            SELECT 
                s.id,
                s.nome,
                s.descricao
            FROM setor s
            JOIN funcionario f ON f.setor_id = s.id
            WHERE f.id = %s
              AND s.nome ILIKE %s;
        """

        # Executa a query passando os parâmetros user_id e nome_setor
        cur.execute(query, (user_id, f"%{nome_setor}%"))
        rows = cur.fetchall()


        # Caso não haja resultados, retorna status "nra" e mensagem
        if not rows:
            return {"status": "nra", "message": f"Nenhum setor encontrado com nome semelhante a '{nome_setor}'."}

        # Processa os resultados em uma lista de dicionários
        results = [
            {"id": r[0], "nome": r[1], "descricao": r[2] or "(sem descrição)"}
            for r in rows
        ]

        return {"status": "ok", "resultados": results}

    except Exception as e:
        conn.rollback()
        print("Erro ao executar query_setor_descricao:", e)
        return {"status": "error", "message": str(e)}

    finally:
        cur.close()
        conn.close()


TOOLS_ANALISE = [query_movimentacao_estoque, query_setor_descricao]
