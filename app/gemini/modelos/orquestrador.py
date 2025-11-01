# ------------------------------------------------------------ Imports ----------------------------------------------------------------------------

import json
from app.gemini.modelos.roteador import chain_roteador
from app.gemini.modelos.agente_analista import chain_analista
from app.gemini.modelos.faq import chain_faq
from app.gemini.modelos.agente_relatorio import chain_relatorio
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.prompts import MessagesPlaceholder
from langchain_core.prompts.few_shot import FewShotChatMessagePromptTemplate
from langchain.agents import create_tool_calling_agent, AgentExecutor
from app.gemini.tools.analista_tools import TOOLS_ANALISE
from app.gemini.modelos.base import today_local, example_prompt, llm, get_session_history
from langchain_core.output_parsers import StrOutputParser
from app.gemini.modelos.juiz import avaliar_resposta_agente

# --------------------------------------------------------------- Orquestrador -----------------------------------------------------------------------

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

# --------------------------------------------------------------- Shots -------------------------------------------------------------------------

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
        "human": "ROUTE=relatorio_mensal\nPERGUNTA_ORIGINAL=Gere um relatório de movimentação de estoque de outubro de 2025.\nPERSONA={PERSONA_SISTEMA}\nCLARIFY=",
        "ai": """{
            "status": "ok",
            "relatorio": {
                "mes_referencia": "Outubro 2025",
                "resumo_geral": {
                    "entradas_total_volume": 4523,
                    "saidas_total_volume": 1666,
                    "saldo_final_volume": 2857,
                    "porcentagem_ocupacao_media": 21.83
                },
                "resposta": "RELATÓRIO MENSAL — Outubro de 2025\\nEntradas: 4523 | Saídas: 1666 | Saldo: 2857 | Ocupação média: 21.83%\\nRecomendações: Otimizar layout, Monitorar fluxo, Aproveitar espaço ocioso."
            }
        }"""
    },
    {
        "human": "ROUTE=relatorio_mensal\nPERGUNTA_ORIGINAL=Compare os relatórios de setembro e outubro de 2025.\nPERSONA={PERSONA_SISTEMA}\nCLARIFY=",
        "ai": """{
            "status": "ok",
            "relatorio": {
                "mes_referencia": "Comparativo Setembro-Outubro 2025",
                "resumo_geral": {
                    "entradas_total_volume": 200,
                    "saidas_total_volume": 150,
                    "saldo_final_volume": 350,
                    "porcentagem_ocupacao_media": 5.0
                },
                "resposta": "RELATÓRIO COMPARATIVO — Setembro x Outubro 2025\\nEntradas: 200 | Saídas: 150 | Saldo: 350 | Ocupação média: 5%\\nRecomendações: Monitorar entradas e saídas, Planejar estoques futuros, Otimizar ocupação."
            }
        }"""
    },
    {
        "human": "ROUTE=relatorio_mensal\nPERGUNTA_ORIGINAL=Consulte o relatório mensal de setembro de 2025.\nPERSONA={PERSONA_SISTEMA}\nCLARIFY=",
        "ai": """{
            "status": "ok",
            "relatorio": {
                "mes_referencia": "Setembro 2025",
                "resumo_geral": {
                    "entradas_total_volume": 4523,
                    "saidas_total_volume": 1666,
                    "saldo_final_volume": 2857,
                    "porcentagem_ocupacao_media": 21.83
                },
                "resposta": "RELATÓRIO MENSAL — Setembro de 2025\\nEntradas: 4523 | Saídas: 1666 | Saldo: 2857 | Ocupação média: 21.83%\\nRecomendações: Otimizar layout, Monitorar fluxo, Aproveitar espaço ocioso."
            }
        }"""
    },
    # ======================================================
    # ANALISE DE ESTOQUE
    # ======================================================
    {
        "human": "ROUTE=analise_estoque\nPERGUNTA_ORIGINAL=Detectar anomalias no setor de Armazenagem\nPERSONA={PERSONA_SISTEMA}\nCLARIFY=",
        "ai": """{
            "dominio":"analise_estoque",
            "intencao":"detectar_anomalias",
            "resposta_agente":"Foram detectadas inconsistências no setor de Armazenagem: divergência de 48 L entre o estoque físico e o registrado.",
            "recomendacao":"Deseja que eu gere um relatório detalhado da auditoria?",
            "documento":{"setor":"Armazenagem","divergencia_L":48,"tipo_inconsistencia":"estoque_fisico_vs_sistema","data_detectada":"2025-10-26T15:40:00","responsavel_verificacao":"Agente de Análise de Estoque"}
        }"""
    },
    {
        "human": "ROUTE=faq\nPERGUNTA_ORIGINAL=qual o e-mail de suporte?\nPERSONA={PERSONA_SISTEMA}\nCLARIFY=",
        "ai": """{
            "dominio":"faq",
            "intencao":"consultar_faq",
            "resposta_agente":"Você pode entrar em contato com nossa equipe de suporte pelo e-mail suporte2025.neo.tech@gmail.com.",
            "recomendacao":"Se preferir, posso abrir um chamado diretamente no sistema para você.",
            "documento":{"tipo":"contato_suporte","email":"suporte2025.neo.tech@gmail.com","canal_alternativo":"formulário de suporte no portal Neo Tech","ultima_atualizacao":"2025-10-29T14:00:00","responsavel":"Atendimento Neo Tech"}
        }"""
    }
]

# --------------------------------------------------------------- FewShots ---------------------------------------------------------------------

fewshots_orquestrador = FewShotChatMessagePromptTemplate(
    examples=shots_orquestrador,
    example_prompt=example_prompt,
)

# --------------------------------------------------------------- Prompt -----------------------------------------------------------------------

prompt_orquestrador  = ChatPromptTemplate.from_messages([
    system_prompt_orquestrador,
    fewshots_orquestrador,
    MessagesPlaceholder(variable_name="chat_history"),
    ("human", "{input}"),
]).partial(today_local=today_local.isoformat())

# --------------------------------------------------------------- Chain ------------------------------------------------------------------------

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
        pergunta_para_faq = resposta_agente_roteador.split("PERGUNTA_ORIGINAL=")[-1].split("\n")[0]
        return chain_faq.invoke({"input": pergunta_para_faq}, config=session_config)
    else:
        return "Não foi possível gerar a resposta esperada. Tente reformular sua pergunta."

    resposta_agente = agente_escolhido.invoke(
        {"input": resposta_agente_roteador},
        config=session_config
    )
  
    avaliacao_juiz = avaliar_resposta_agente(pergunta, resposta_agente)

    if "Aprovado" in avaliacao_juiz:
        resposta = resposta_agente.get("output", resposta_agente)
        return chain_orquestrador.invoke({
            "input": resposta,
            "chat_history": get_session_history(user_id)
        }, config=session_config)

    elif "Reprovado" in avaliacao_juiz:
        feedback = avaliacao_juiz.split("Feedback:")[-1].strip() if "Feedback:" in avaliacao_juiz else avaliacao_juiz
        pergunta_nova = (
            f"{pergunta}\n\nO juiz reprovou a resposta_agente anterior. "
            f"Reformule a resposta_agente considerando o feedback do juiz:\n{feedback}"
        )
        resposta_agente = agente_escolhido.invoke({"input": pergunta_nova}, config=session_config)
        resposta = resposta_agente.get("output", resposta_agente)
        return chain_orquestrador.invoke({
            "input": resposta,
            "chat_history": get_session_history(user_id)
        }, config=session_config)
