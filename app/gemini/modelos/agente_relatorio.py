# ------------------------------------------------------------ Imports ----------------------------------------------------------------------------


from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder
)
from langchain_core.prompts.few_shot import FewShotChatMessagePromptTemplate
from langchain.agents import create_tool_calling_agent, AgentExecutor
from app.gemini.modelos.base import today_local, example_prompt, llm, get_session_history
from app.gemini.tools.relatorio_tools import TOOLS_RELATORIO


# =============================================================== AGENTES ========================================================================


# --------------------------------------------------------------- Relatórios ----------------------------------------------------------------------


# Sistem_prompt
system_prompt_relatorio = ("system",
"""
### OBJETIVO
Gerar relatórios estruturados e narrativos detalhados baseados em dados. A saída SEMPRE é JSON para o Orquestrador.

### TAREFAS
- Interpretar o propósito do relatório solicitado (resumo executivo, comparação entre períodos).
- Determinar a janela temporal apropriada (usar `janela_tempo` se fornecida).
- Agregar e sumarizar documentos/contexto do retriever.
- Produzir:
  - Sumário executivo
  - Análise de fluxo
  - Desempenho por setor
  - Recomendações detalhadas
  - Conclusão narrativa
- Sempre incluir subtópicos claros, divisórias e emojis como no estilo fornecido.

### CONTEXTO
- Hoje é {today_local} (America/Sao_Paulo). Interprete datas relativas a partir desta data.
- Entrada via protocolo:
  - ROUTE=relatorio_mensal
  - PERGUNTA_ORIGINAL=...
  - PERSONA=...
  - CLARIFY=...

### REGRAS
- Use {chat_history} e documentos anexados pelo retriever como fontes.
- Não invente valores; inclua fonte ou indique 'estimado'.
- Entregue relatório em JSON seguindo este contrato.

### SAÍDA (JSON)
- dominio          : "relatorio"
- intencao         : "resumo" | "kpi" | "comparacao" | "executivo" | "consulta"
- resposta         : texto detalhado, narrativo e visual com subtópicos, divisórias e emojis
- recomendacao     : lista de ações práticas (mesmo conteúdo da seção de recomendações)
- relatorio_formatado: versão visual completa para exibição (mesmo conteúdo de `resposta`)

### HISTÓRICO DA CONVERSA
{chat_history}
"""
)


shots_relatorio = [
    {
        "human": "ROUTE=relatorio_mensal\nPERGUNTA_ORIGINAL=Quais são as sugestões para otimizar o estoque com base nos dados fornecidos?\nPERSONA={PERSONA_SISTEMA}\nCLARIFY=",
        "ai": """{
            "sugestoes": [
                "Aumentar as entradas de produtos que têm alta demanda.",
                "Reduzir as saídas de produtos que estão com baixa rotatividade.",
                "Implementar um sistema de monitoramento de estoque em tempo real."
            ]
        }"""
    },
    {
        "human": "ROUTE=relatorio_mensal\nPERGUNTA_ORIGINAL=Gere um relatório de movimentação de estoque de outubro de 2025 para a Indústria 1.\nPERSONA={PERSONA_SISTEMA}\nCLARIFY=",
        "ai": """{
            "status": "ok",
            "relatorio": {
                "mes_referencia": "Outubro 2025",
                "gerado_em": "2025-10-31T12:00:00Z",
                "origem": "Chatbot sob demanda",
                "resumo_geral": {
                    "entradas_total_volume": 4523,
                    "saidas_total_volume": 1666,
                    "saldo_final_volume": 2857,
                    "porcentagem_ocupacao_media": 21.83
                },
                "resposta": "RELATÓRIO MENSAL — Outubro de 2025\\n──────────────────────────────────────\\n\\nRESUMO DE MOVIMENTAÇÃO\\n- Entradas totais: 4523 unidades  \\n- Saídas totais: 1666 unidades  \\n- Saldo final: 2857 unidades  \\n- Ocupação média do estoque: 21.83%\\n\\nDurante o mês de outubro, observou-se uma movimentação consistente de produtos, refletindo a demanda regular e a reposição estratégica de itens de alta rotatividade. O saldo final garante uma boa disponibilidade para atender às operações dos próximos períodos.\\n\\nANÁLISE DE FLUXO\\n- Entradas: Predominantemente matérias-primas críticas para produção, com destaque para os setores 1 e 2.  \\n- Saídas: Consumo e distribuição de produtos acabados e semiacabados, com picos em datas específicas devido à demanda sazonal.  \\n- Saldo: Estoque equilibrado, porém com baixa ocupação relativa, indicando espaço disponível para otimização logística.\\n\\nDESEMPENHO POR SETOR\\n- Setor 1: Alta rotatividade, estoque otimizado, sem gargalos.  \\n- Setor 2: Movimentação moderada, oportunidades de reorganização.  \\n- Setor 3: Baixa ocupação, espaço ocioso significativo, sugere revisão de alocação.\\n\\nRECOMENDAÇÕES\\n────────────────\\n- Otimizar o layout do estoque: Consolidar itens de alta rotatividade próximos às áreas de saída.  \\n- Investigar causas da baixa ocupação: Analisar produtos com baixa entrada ou saída, sazonalidade e gargalos operacionais.  \\n- Aproveitar espaço ocioso: Redistribuir produtos ou armazenar itens estratégicos, reduzindo custos com áreas subutilizadas.  \\n- Monitoramento contínuo: Criar indicadores de acompanhamento da ocupação e rotatividade do estoque.  \\n- Planejamento de compras e vendas: Ajustar pedidos e produção conforme análise detalhada do fluxo.  \\n- Treinamento e processos: Capacitar equipe para reorganização eficiente e melhoria contínua de processos.  \\n- Relatórios complementares: Integrar análises mensais de estoque com métricas financeiras e de vendas para decisões estratégicas.\\n\\nCONCLUSÃO\\nO mês de outubro apresentou movimentação estável, saldo positivo e oportunidades claras de otimização de espaço. As ações recomendadas visam maximizar a eficiência operacional, reduzir custos e preparar o estoque para períodos de maior demanda.",
                "recomendacao": [
                    "Otimizar o layout do estoque",
                    "Investigar causas da baixa ocupação",
                    "Aproveitar espaço ocioso",
                    "Monitoramento contínuo",
                    "Planejamento de compras e vendas",
                    "Treinamento e processos",
                    "Relatórios complementares"
                ]
            }
        }"""
    },
    {
        "human": "ROUTE=relatorio_mensal\nPERGUNTA_ORIGINAL=Compare os relatórios de setembro e outubro de 2025.\nPERSONA={PERSONA_SISTEMA}\nCLARIFY=",
        "ai": """{
            "status": "ok",
            "relatorio": {
                "mes_referencia": "Comparativo Setembro-Outubro 2025",
                "gerado_em": "2025-10-31T12:00:00Z",
                "origem": "Chatbot sob demanda",
                "resumo_geral": {
                    "entradas_total_volume": 200,
                    "saidas_total_volume": 150,
                    "saldo_final_volume": 350,
                    "porcentagem_ocupacao_media": 5.0
                },
                "resposta": "RELATÓRIO COMPARATIVO — Setembro x Outubro 2025\\n──────────────────────────────────────\\n\\nRESUMO DE MOVIMENTAÇÃO\\n- Entradas totais: 200 unidades \\n- Saídas totais: 150 unidades \\n- Saldo final: 350 unidades \\n- Ocupação média do estoque: 5%\\n\\nNo comparativo entre os meses, observa-se uma diferença significativa no saldo final, indicando que o estoque cresceu em outubro em relação a setembro. A movimentação de entradas e saídas reflete ajustes na reposição e distribuição de produtos durante o período.\\n\\nANÁLISE DE FLUXO\\n- Entradas: Ajustadas conforme a demanda do período anterior, com leve aumento de reposição. \\n- Saídas: Redução moderada em outubro, sugerindo menor consumo ou distribuição. \\n- Saldo: Crescimento positivo, garantindo disponibilidade suficiente para operações futuras.\\n\\nDESEMPENHO POR MÊS\\n- Setembro: Estoque estável, ocupação baixa, fluxo regular de entradas e saídas. \\n- Outubro: Estoque levemente maior, indicando planejamento estratégico para atender demanda futura.\\n\\nRECOMENDAÇÕES\\n────────────────\\n- Monitorar entradas e saídas: Ajustar conforme padrão de consumo mensal. \\n- Planejar estoques futuros: Considerar sazonalidade e crescimento do saldo. \\n- Otimizar ocupação: Avaliar utilização de espaço ocioso e reorganizar itens. \\n- Integração com relatórios anteriores: Acompanhar tendências de movimentação para decisões estratégicas.\\n\\nCONCLUSÃO\\nO comparativo evidencia crescimento do saldo em outubro, manutenção de entradas e saídas equilibradas, e espaço disponível para otimização logística, garantindo preparo para demandas futuras.",
                "recomendacao": [
                    "Monitorar entradas e saídas",
                    "Planejar estoques futuros",
                    "Otimizar ocupação",
                    "Integração com relatórios anteriores"
                ]
            }
        }"""
    },
    {
        "human": "ROUTE=relatorio_mensal\nPERGUNTA_ORIGINAL=Consulte o relatório mensal de setembro de 2025.\nPERSONA={PERSONA_SISTEMA}\nCLARIFY=",
        "ai": """{
            "status": "ok",
            "mensagem": "Relatório mensal encontrado para 2025-09.",
            "relatorio": {
                "mes_referencia": "Outubro 2025",
                "gerado_em": "2025-10-31T12:00:00Z",
                "origem": "Chatbot sob demanda",
                "resumo_geral": {
                    "entradas_total_volume": 4523,
                    "saidas_total_volume": 1666,
                    "saldo_final_volume": 2857,
                    "porcentagem_ocupacao_media": 21.83
                },
                "resposta": "RELATÓRIO MENSAL — Outubro de 2025\\n──────────────────────────────────────\\n\\nRESUMO DE MOVIMENTAÇÃO\\n- Entradas totais: 4523 unidades  \\n- Saídas totais: 1666 unidades  \\n- Saldo final: 2857 unidades  \\n- Ocupação média do estoque: 21.83%\\n\\nDurante o mês de outubro, observou-se uma movimentação consistente de produtos, refletindo a demanda regular e a reposição estratégica de itens de alta rotatividade. O saldo final garante uma boa disponibilidade para atender às operações dos próximos períodos.\\n\\nANÁLISE DE FLUXO\\n- Entradas: Predominantemente matérias-primas críticas para produção, com destaque para os setores 1 e 2.  \\n- Saídas: Consumo e distribuição de produtos acabados e semiacabados, com picos em datas específicas devido à demanda sazonal.  \\n- Saldo: Estoque equilibrado, porém com baixa ocupação relativa, indicando espaço disponível para otimização logística.\\n\\nDESEMPENHO POR SETOR\\n- Setor 1: Alta rotatividade, estoque otimizado, sem gargalos.  \\n- Setor 2: Movimentação moderada, oportunidades de reorganização.  \\n- Setor 3: Baixa ocupação, espaço ocioso significativo, sugere revisão de alocação.\\n\\nRECOMENDAÇÕES\\n────────────────\\n- Otimizar o layout do estoque: Consolidar itens de alta rotatividade próximos às áreas de saída.  \\n- Investigar causas da baixa ocupação: Analisar produtos com baixa entrada ou saída, sazonalidade e gargalos operacionais.  \\n- Aproveitar espaço ocioso: Redistribuir produtos ou armazenar itens estratégicos, reduzindo custos com áreas subutilizadas.  \\n- Monitoramento contínuo: Criar indicadores de acompanhamento da ocupação e rotatividade do estoque.  \\n- Planejamento de compras e vendas: Ajustar pedidos e produção conforme análise detalhada do fluxo.  \\n- Treinamento e processos: Capacitar equipe para reorganização eficiente e melhoria contínua de processos.  \\n- Relatórios complementares: Integrar análises mensais de estoque com métricas financeiras e de vendas para decisões estratégicas.\\n\\nCONCLUSÃO\\nO mês de outubro apresentou movimentação estável, saldo positivo e oportunidades claras de otimização de espaço. As ações recomendadas visam maximizar a eficiência operacional, reduzir custos e preparar o estoque para períodos de maior demanda.",
                "recomendacao": [
                    "Otimizar o layout do estoque",
                    "Investigar causas da baixa ocupação",
                    "Aproveitar espaço ocioso",
                    "Monitoramento contínuo",
                    "Planejamento de compras e vendas",
                    "Treinamento e processos",
                    "Relatórios complementares"
                ]
            }
        }"""
    }
]

# fewshots
fewshots_relatorio = FewShotChatMessagePromptTemplate(
    examples=shots_relatorio,      # exemplos human/ai de geração de relatórios
    example_prompt=example_prompt
)


# prompt 
prompt_relatorio = ChatPromptTemplate.from_messages([
    system_prompt_relatorio,                # system prompt específico do agente
    fewshots_relatorio,                     # exemplos de estilo e estrutura
    MessagesPlaceholder("chat_history"),    # memória conversacional
    ("human", "{input}"),                   # input do usuário
    MessagesPlaceholder("agent_scratchpad") # rastreio de ferramentas (necessário p/ tool calling)
]).partial(today_local=today_local.isoformat())


# tool calling
agent_relatorio = create_tool_calling_agent(llm, TOOLS_RELATORIO, prompt_relatorio)


# executor 
agent_executor_relatorio = AgentExecutor(
    agent=agent_relatorio,
    tools=TOOLS_RELATORIO,
    verbose=False
)

# chain
chain_relatorio = RunnableWithMessageHistory(
    agent_executor_relatorio,
    get_session_history=get_session_history,
    input_messages_key="input",
    history_messages_key="chat_history"
)

