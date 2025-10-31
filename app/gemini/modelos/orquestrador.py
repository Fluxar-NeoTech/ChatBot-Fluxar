# ------------------------------------------------------------ Imports ----------------------------------------------------------------------------

import json
from app.gemini.modelos.roteador import chain_roteador
from app.gemini.modelos.agente_analista import chain_analista
from app.gemini.modelos.faq import chain_faq
from app.gemini.modelos.agente_relatorio import chain_relatorio
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder
)
from langchain_core.prompts.few_shot import FewShotChatMessagePromptTemplate
from langchain.agents import create_tool_calling_agent, AgentExecutor
from app.gemini.tools.analista_tools import TOOLS_ANALISE
from app.gemini.modelos.base import today_local, example_prompt, llm, get_session_history
from langchain_core.output_parsers import StrOutputParser
from app.gemini.modelos.juiz import avaliar_resposta_agente

# --------------------------------------------------------------- Orquestrador -----------------------------------------------------------------------
 

# Sistem_prompt
system_prompt_orquestrador = ("system",
    """
### PAPEL
Você é o Agente Orquestrador do Flux.AI. Sua função é entregar a resposta_agente final ao usuário **somente** quando um Especialista retornar o JSON.
 
 
### ENTRADA
- ESPECIALISTA_JSON contendo chaves como:
dominio, intencao, resposta_agente, recomendacao (opcional), acompanhamento (opcional),
esclarecer (opcional), janela_tempo (opcional), evento (opcional), escrita (opcional), indicadores (opcional).
 
 
### REGRAS
- Use **exatamente** `resposta_agente` do especialista como a **primeira linha** do output.
- Se `recomendacao` existir e não for vazia, inclua a seção *Recomendação*; caso contrário, **omita**.
- Para *Acompanhamento*: se houver `esclarecer`, use-o; senão, se houver `acompanhamento`, use-o; caso contrário, **omita** a seção.
- Não reescreva números/datas se já vierem prontos. Não invente dados. Seja conciso.
- Não retorne JSON; **sempre** retorne no FORMATO DE SAÍDA.
 
 
### FORMATO DE SAÍDA (sempre ao usuário)
<sua resposta_agente será 1 frase objetiva sobre a situação>
- *Recomendação*:
<ação prática e imediata>     # omita esta seção se não houver recomendação
- *Acompanhamento* (opcional):
<pergunta/minipróximo passo>  # omita se nada for necessário
 
 
### HISTÓRICO DA CONVERSA
{chat_history}
"""
)


# shots
shots_orquestrador = [

    # ======================================================
    # RELATÓRIOS
    # ======================================================

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
                "resposta": "📊 RELATÓRIO MENSAL — Outubro de 2025\\n──────────────────────────────────────\\n\\n📈 RESUMO DE MOVIMENTAÇÃO\\n- Entradas totais: **4523 unidades**  \\n- Saídas totais: **1666 unidades**  \\n- Saldo final: **2857 unidades**  \\n- Ocupação média do estoque: **21.83%**\\n\\nDurante o mês de outubro, observou-se uma movimentação consistente de produtos, refletindo a demanda regular e a reposição estratégica de itens de alta rotatividade. O saldo final garante uma boa disponibilidade para atender às operações dos próximos períodos.\\n\\n🧮 ANÁLISE DE FLUXO\\n- Entradas: Predominantemente matérias-primas críticas para produção, com destaque para os setores 1 e 2.  \\n- Saídas: Consumo e distribuição de produtos acabados e semiacabados, com picos em datas específicas devido à demanda sazonal.  \\n- Saldo: Estoque equilibrado, porém com baixa ocupação relativa, indicando espaço disponível para otimização logística.\\n\\n🏷️ DESEMPENHO POR SETOR\\n- Setor 1: Alta rotatividade, estoque otimizado, sem gargalos.  \\n- Setor 2: Movimentação moderada, oportunidades de reorganização.  \\n- Setor 3: Baixa ocupação, espaço ocioso significativo, sugere revisão de alocação.\\n\\n RECOMENDAÇÕES\\n────────────────\\n- **Otimizar o layout do estoque:** Consolidar itens de alta rotatividade próximos às áreas de saída.  \\n- **Investigar causas da baixa ocupação:** Analisar produtos com baixa entrada ou saída, sazonalidade e gargalos operacionais.  \\n- **Aproveitar espaço ocioso:** Redistribuir produtos ou armazenar itens estratégicos, reduzindo custos com áreas subutilizadas.  \\n- **Monitoramento contínuo:** Criar indicadores de acompanhamento da ocupação e rotatividade do estoque.  \\n- **Planejamento de compras e vendas:** Ajustar pedidos e produção conforme análise detalhada do fluxo.  \\n- **Treinamento e processos:** Capacitar equipe para reorganização eficiente e melhoria contínua de processos.  \\n- **Relatórios complementares:** Integrar análises mensais de estoque com métricas financeiras e de vendas para decisões estratégicas.\\n\\n💡 CONCLUSÃO\\nO mês de outubro apresentou movimentação estável, saldo positivo e oportunidades claras de otimização de espaço. As ações recomendadas visam maximizar a eficiência operacional, reduzir custos e preparar o estoque para períodos de maior demanda.",
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
        "resposta": "📊 RELATÓRIO COMPARATIVO — Setembro x Outubro 2025\\n──────────────────────────────────────\\n\\n📈 RESUMO DE MOVIMENTAÇÃO\\n- Entradas totais: **200 unidades** \\n- Saídas totais: **150 unidades** \\n- Saldo final: **350 unidades** \\n- Ocupação média do estoque: **5%**\\n\\nNo comparativo entre os meses, observa-se uma diferença significativa no saldo final, indicando que o estoque cresceu em outubro em relação a setembro. A movimentação de entradas e saídas reflete ajustes na reposição e distribuição de produtos durante o período.\\n\\n🧮 ANÁLISE DE FLUXO\\n- Entradas: Ajustadas conforme a demanda do período anterior, com leve aumento de reposição. \\n- Saídas: Redução moderada em outubro, sugerindo menor consumo ou distribuição. \\n- Saldo: Crescimento positivo, garantindo disponibilidade suficiente para operações futuras.\\n\\n🏷️ DESEMPENHO POR MÊS\\n- Setembro: Estoque estável, ocupação baixa, fluxo regular de entradas e saídas. \\n- Outubro: Estoque levemente maior, indicando planejamento estratégico para atender demanda futura.\\n\\n RECOMENDAÇÕES\\n────────────────\\n- **Monitorar entradas e saídas:** Ajustar conforme padrão de consumo mensal. \\n- **Planejar estoques futuros:** Considerar sazonalidade e crescimento do saldo. \\n- **Otimizar ocupação:** Avaliar utilização de espaço ocioso e reorganizar itens. \\n- **Integração com relatórios anteriores:** Acompanhar tendências de movimentação para decisões estratégicas.\\n\\n💡 CONCLUSÃO\\nO comparativo evidencia crescimento do saldo em outubro, manutenção de entradas e saídas equilibradas, e espaço disponível para otimização logística, garantindo preparo para demandas futuras.",
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
                "resposta": "📊 RELATÓRIO MENSAL — Outubro de 2025\\n──────────────────────────────────────\\n\\n📈 RESUMO DE MOVIMENTAÇÃO\\n- Entradas totais: **4523 unidades**  \\n- Saídas totais: **1666 unidades**  \\n- Saldo final: **2857 unidades**  \\n- Ocupação média do estoque: **21.83%**\\n\\nDurante o mês de outubro, observou-se uma movimentação consistente de produtos, refletindo a demanda regular e a reposição estratégica de itens de alta rotatividade. O saldo final garante uma boa disponibilidade para atender às operações dos próximos períodos.\\n\\n🧮 ANÁLISE DE FLUXO\\n- Entradas: Predominantemente matérias-primas críticas para produção, com destaque para os setores 1 e 2.  \\n- Saídas: Consumo e distribuição de produtos acabados e semiacabados, com picos em datas específicas devido à demanda sazonal.  \\n- Saldo: Estoque equilibrado, porém com baixa ocupação relativa, indicando espaço disponível para otimização logística.\\n\\n🏷️ DESEMPENHO POR SETOR\\n- Setor 1: Alta rotatividade, estoque otimizado, sem gargalos.  \\n- Setor 2: Movimentação moderada, oportunidades de reorganização.  \\n- Setor 3: Baixa ocupação, espaço ocioso significativo, sugere revisão de alocação.\\n\\n RECOMENDAÇÕES\\n────────────────\\n- **Otimizar o layout do estoque:** Consolidar itens de alta rotatividade próximos às áreas de saída.  \\n- **Investigar causas da baixa ocupação:** Analisar produtos com baixa entrada ou saída, sazonalidade e gargalos operacionais.  \\n- **Aproveitar espaço ocioso:** Redistribuir produtos ou armazenar itens estratégicos, reduzindo custos com áreas subutilizadas.  \\n- **Monitoramento contínuo:** Criar indicadores de acompanhamento da ocupação e rotatividade do estoque.  \\n- **Planejamento de compras e vendas:** Ajustar pedidos e produção conforme análise detalhada do fluxo.  \\n- **Treinamento e processos:** Capacitar equipe para reorganização eficiente e melhoria contínua de processos.  \\n- **Relatórios complementares:** Integrar análises mensais de estoque com métricas financeiras e de vendas para decisões estratégicas.\\n\\n💡 CONCLUSÃO\\nO mês de outubro apresentou movimentação estável, saldo positivo e oportunidades claras de otimização de espaço. As ações recomendadas visam maximizar a eficiência operacional, reduzir custos e preparar o estoque para períodos de maior demanda.",
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
    # 2) Detectar anomalias ou inconsistências
    {
        "human": "ROUTE=analise_estoque\nPERGUNTA_ORIGINAL=Detectar anomalias no setor de Armazenagem\nPERSONA={PERSONA_SISTEMA}\nCLARIFY=",
        "ai": """{{"dominio":"analise_estoque","intencao":"detectar_anomalias","resposta_agente":"Foram detectadas inconsistências no setor de Armazenagem: divergência de 48 L entre o estoque físico e o registrado.","recomendacao":"Deseja que eu gere um relatório detalhado da auditoria?","documento":{{"setor":"Armazenagem","divergencia_L":48,"tipo_inconsistencia":"estoque_fisico_vs_sistema","data_detectada":"2025-10-26T15:40:00","responsavel_verificacao":"Agente de Análise de Estoque"}}}}"""
    },
    {
        "human": "ROUTE=faq\nPERGUNTA_ORIGINAL=qual o e-mail de suporte?\nPERSONA={{PERSONA_SISTEMA}}\nCLARIFY=",
        "ai": """{{"dominio":"faq","intencao":"consultar_faq","resposta_agente":"Você pode entrar em contato com nossa equipe de suporte pelo e-mail suporte2025.neo.tech@gmail.com.","recomendacao":"Se preferir, posso também abrir um chamado diretamente no sistema para você.","documento":{{"tipo":"contato_suporte","email":"suporte2025.neo.tech@gmail.com","canal_alternativo":"formulário de suporte no portal Neo Tech","ultima_atualizacao":"2025-10-29T14:00:00","responsavel":"Atendimento Neo Tech"}}}}"""
    },
    {
        "human": "ROUTE=analise_estoque\nPERGUNTA_ORIGINAL=Mostre a descrição do setor de embalagem.\nPERSONA={PERSONA_SISTEMA}\nCLARIFY=",
        "ai": """{{"dominio":"analise_estoque","intencao":"consultar_setor","resposta_agente":"O setor de Embalagem é responsável pela finalização dos produtos, incluindo empacotamento e rotulagem.","recomendacao":"Verificar se há integração entre o setor de embalagem e o de expedição para otimizar o fluxo logístico.","documento":{{"setor":"Embalagem","descricao":"Responsável pela finalização dos produtos, empacotamento e rotulagem.","ultima_atualizacao":"2025-10-30T10:45:00","responsavel":"Agente de Análise de Setores"}}}}"""
    }
]

# fewshots
fewshots_orquestrador = FewShotChatMessagePromptTemplate(
    examples=shots_orquestrador,
    example_prompt=example_prompt,
)
 
# prompt 
prompt_orquestrador  = ChatPromptTemplate.from_messages([
    system_prompt_orquestrador,                          # system prompt
    fewshots_orquestrador,                               # Shots human/ai
    MessagesPlaceholder(variable_name="chat_history"),    # memória
    ("human", "{input}"),                  # user prompt
]).partial(today_local=today_local.isoformat())

# chain 
chain_orquestrador = RunnableWithMessageHistory(
    prompt_orquestrador | llm | StrOutputParser(),
    get_session_history=get_session_history,
    input_messages_key="input",
    history_messages_key="chat_history",
)


# ========================================================= Função de direcionamento de Agentes ==================================================

def chamada_agente(pergunta: str, user_id: int):
    session_config = {"configurable": {"session_id": user_id}}
   

    resposta_agente_roteador = chain_roteador.invoke(
        {"input": pergunta},
        config=session_config
    )

    if "ROUTE=analise_estoque" in resposta_agente_roteador:
        agente_escolhido = chain_analista
    elif "ROUTE=relatorio_mensal" in resposta_agente_roteador:
        agente_escolhido = chain_relatorio
    elif "ROUTE=faq" in resposta_agente_roteador:
        agente_escolhido = chain_faq
    else:
        return "Não foi possível gerar a resposta esperada. Tente reformular sua pergunta."


    resposta_agente = agente_escolhido.invoke(
        {"input": resposta_agente_roteador},
        config=session_config
    )
  
    avaliacao_juiz = avaliar_resposta_agente(pergunta, resposta_agente)


    if "Aprovado" in avaliacao_juiz:


        resposta = resposta_agente.get("output",resposta_agente)

        # Envia ao orquestrador
        resposta_orquestrada = chain_orquestrador.invoke({
            "input": resposta,
            "chat_history": get_session_history(user_id)
        }, config=session_config)

        # Trata a resposta final

        return resposta_orquestrada


    elif "Reprovado" in avaliacao_juiz:

        feedback = (
            avaliacao_juiz.split("Feedback:")[-1].strip()
            if "Feedback:" in avaliacao_juiz
            else avaliacao_juiz
        )

        # Enriquecer o input original com o feedback do juiz
        pergunta_nova = (
            f"{pergunta}\n\nO juiz reprovou a resposta_agente anterior. "
            f"Reformule a resposta_agente considerando o feedback do juiz:\n{feedback}"
        )

        resposta_agente = agente_escolhido.invoke(
        {"input": pergunta_nova},
        config=session_config
        )
        
        resposta = resposta_agente.get("output",resposta_agente)

        resposta_orquestrada = chain_orquestrador.invoke({
            "input": resposta_agente,
            "chat_history": get_session_history(user_id)
        }, config=session_config)


        return resposta_orquestrada




# --------------------------------------------------------------- Input/Output --------------------------------------------------------------------

# while True:
#     user_input = input(">")
#     if user_input.lower() in ("sair", "end", "fim", "bye", "tchau"):
#         print("Encerrando conversa. ")
#         break
#     try:
#         resposta_agente = chamada_agente(user_input, 2)
#         print(resposta_agente)
        
#     except Exception as e:
#         print(f"Erro ao consumir a API {e}")
       


      

