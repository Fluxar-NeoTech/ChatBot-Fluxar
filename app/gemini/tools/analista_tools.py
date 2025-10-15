import os
from typing import Optional
from dotenv import load_dotenv
import psycopg2
from langchain.tools import tool  # ou "from langchain.tools import tool" dependendo da versão
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import datetime as _dt

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")  

def get_conn():
    return psycopg2.connect(DATABASE_URL)


from pydantic import BaseModel, Field
from typing import Optional

class QueryStockMovementsArgs(BaseModel):
    text: Optional[str] = Field(None, description="Texto para buscar em nome do produto ou setor")
    movimentacao: Optional[str] = Field(None, description="Tipo de movimentação: 'E' (entrada) ou 'S' (saída)")
    date_local: Optional[str] = Field(None, description="Data específica local (YYYY-MM-DD)")
    date_from_local: Optional[str] = Field(None, description="Data inicial do intervalo (YYYY-MM-DD)")
    date_to_local: Optional[str] = Field(None, description="Data final do intervalo (YYYY-MM-DD)")
    industria_id: Optional[int] = Field(None, description="ID da indústria")
    unidade_id: Optional[int] = Field(None, description="ID da unidade")
    setor_id: Optional[int] = Field(None, description="ID do setor")
    produto_id: Optional[int] = Field(None, description="ID do produto")
    limit: int = Field(20, description="Limite máximo de resultados (padrão: 20)")


@tool("query_stock_movements", args_schema=QueryStockMovementsArgs)
def query_stock_movements(
    text: Optional[str] = None,              # texto de busca (produto ou setor)
    movimentacao: Optional[str] = None,      # 'E' (entrada) ou 'S' (saída)
    date_local: Optional[str] = None,        # uma data específica
    date_from_local: Optional[str] = None,   # início do intervalo
    date_to_local: Optional[str] = None,     # fim do intervalo
    industria_id: Optional[int] = None,
    unidade_id: Optional[int] = None,
    setor_id: Optional[int] = None,
    produto_id: Optional[int] = None,
    limit: int = 20,
) -> dict:
    """
    Consulta o histórico de movimentações de estoque (tabela historico_estoque).

    Filtros opcionais:
    - texto (busca por nome de produto ou setor)
    - movimentação ('E' ou 'S')
    - intervalo de datas locais (America/Sao_Paulo)
    - indústria, unidade, setor, produto
    
    Ordenação:
    - Se houver intervalo (date_from_local/date_to_local): ASC (cronológico)
    - Caso contrário: DESC (mais recentes primeiro)
    """
    conn = get_conn()
    cur = conn.cursor()

    try:
        filters = []
        params = []

        # Texto (busca por nome do produto ou setor)
        if text:
            filters.append("(p.nome ILIKE %s OR s.nome ILIKE %s)")
            params.extend([f"%{text}%", f"%{text}%"])

        # Movimentação (Entrada/Saída)
        if movimentacao:
            filters.append("h.movimentacao = %s")
            params.append(movimentacao.upper())

        # IDs
        if industria_id:
            filters.append("h.industria_id = %s")
            params.append(industria_id)
        if unidade_id:
            filters.append("h.unidade_id = %s")
            params.append(unidade_id)
        if setor_id:
            filters.append("h.setor_id = %s")
            params.append(setor_id)
        if produto_id:
            filters.append("h.produto_id = %s")
            params.append(produto_id)

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

        # Consulta SQL principal
        query = f"""
            SELECT
                h.id,
                h.data AT TIME ZONE 'America/Sao_Paulo' AS data_local,
                h.movimentacao,
                h.volume_movimentado,
                p.nome AS produto,
                s.nome AS setor,
                u.nome AS unidade,
                i.nome AS industria
            FROM historico_estoque h
            JOIN produto p ON h.produto_id = p.id
            JOIN setor s ON h.setor_id = s.id
            JOIN unidade u ON h.unidade_id = u.id
            JOIN industria i ON h.industria_id = i.id
            {where_clause}
            {order_clause}
            LIMIT {limit};
        """

        cur.execute(query, tuple(params))
        rows = cur.fetchall()

        results = []
        for row in rows:
            results.append({
                "id": row[0],
                "data_local": row[1].isoformat() if row[1] else None,
                "movimentacao": "Entrada" if row[2] == 'E' else "Saída",
                "volume_movimentado": float(row[3]),
                "produto": row[4],
                "setor": row[5],
                "unidade": row[6],
                "industria": row[7],
            })

        return {"status": "ok", "results": results}

    except Exception as e:
        conn.rollback()
        conn.rollback()
        print("Erro ao executar query_stock_movements:", e)  # 🔹 print do erro real
        return {"status": "error", "message": str(e)}

    finally:
        cur.close()
        conn.close()


TOOLS_ANALISE = [query_stock_movements]


