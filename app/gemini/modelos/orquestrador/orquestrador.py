# ------------------------------------------------------------ Imports ----------------------------------------------------------------------------

import json
import os
from app.gemini.modelos.roteador.roteador import chain_roteador
from app.gemini.modelos.agente_analista.agente_analista import chain_analista
from app.gemini.modelos.faq.faq import chain_faq
from app.gemini.modelos.agente_de_relatorio.agente_relatorio import chain_relatorio
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.prompts import MessagesPlaceholder
from langchain_core.prompts.few_shot import FewShotChatMessagePromptTemplate
from langchain.agents import create_tool_calling_agent, AgentExecutor
from app.gemini.tools.analista_tools import TOOLS_ANALISE
from app.gemini.modelos.base import today_local, example_prompt, llm, get_session_history
from langchain_core.output_parsers import StrOutputParser
from app.gemini.modelos.juiz.juiz import avaliar_resposta_agente
from app.gemini.modelos.guardrail.guardrail_input import contem_palavra_proibida

# --------------------------------------------------------------- Orquestrador -----------------------------------------------------------------------

# --------------------------- Carregar system prompt ---------------------------

dir_atual = os.path.dirname(__file__)
caminho_prompt = os.path.join(dir_atual, "system_prompt_orquestrador.txt")

with open(caminho_prompt, "r", encoding="utf-8") as f:
    system_prompt_text = f.read()

system_prompt_orquestrador = ("system", system_prompt_text)

# --------------------------- Carregar few-shots ------------------------------
dir_atual = os.path.dirname(__file__)
caminho_fewshots = os.path.join(dir_atual, "fewshots_orquestrador.txt")

with open(caminho_fewshots, "r", encoding="utf-8") as f:
    shots_orquestrador = json.load(f)


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
]).partial(
    today_local=today_local.isoformat()
)

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
    
    # INPUT GUARDRAIL — bloqueia mensagens inadequadas do usuário
    if contem_palavra_proibida(pergunta):
        return "⚠️ Sua mensagem contém linguagem inadequada. Por favor, reformule antes de continuar."
    
    # Invoca o roteador para decidir o agente
    resposta_roteador = chain_roteador.invoke(
        {"input": pergunta, "user_id": user_id},
        config=session_config
    )

    # Se não for rota válida, retorna direto
    # Quando FAQ - retorna direto também
    
    if "ROUTE=analise_estoque" in resposta_roteador:
        agente_escolhido = chain_analista
    elif "ROUTE=relatorio_mensal" in resposta_roteador:
        agente_escolhido = chain_relatorio
    elif "ROUTE=faq" in resposta_roteador:
        pergunta_para_faq = resposta_roteador.split("PERGUNTA_ORIGINAL=")[-1].split("\n")[0]

        # retorna a resposta para o usuário
        return chain_faq.invoke({"input": pergunta_para_faq}, config=session_config)
    elif "ROUTE=" not in resposta_roteador:
        return resposta_roteador
    else:
        return "Não foi possível gerar a resposta esperada. Tente reformular sua pergunta."

        

    # Invoca o agente escolhido
    resposta_agente = agente_escolhido.invoke(
        {"input": resposta_roteador, "user_id": user_id},
        config=session_config
    )
    
    # Avalia a resposta pelo juiz
    avaliacao_juiz = avaliar_resposta_agente(pergunta, resposta_agente)

    if "Aprovado" in avaliacao_juiz:
        resposta = resposta_agente.get("output", resposta_agente)
        

        # devolve a resposta pelo orquestrador
        return chain_orquestrador.invoke({
            "input": resposta,
            "user_id": user_id,
            "chat_history": get_session_history(user_id)
        }, config=session_config)

    elif "Reprovado" in avaliacao_juiz:

        # Extrai apenas o feedback do juiz da string 'avaliacao_juiz'.
        # Se a string contém "Feedback:", pega o texto após essa palavra e remove espaços em branco.
        # Caso contrário, mantém a string inteira.

        feedback = avaliacao_juiz.split("Feedback:")[-1].strip() if "Feedback:" in avaliacao_juiz else avaliacao_juiz


        # Monta uma nova pergunta para o agente, informando que a resposta anterior foi reprovada e incluindo o feedback do juiz para que a resposta seja reformulada.
        pergunta_nova = (
            f"{pergunta}\n\nO juiz reprovou a resposta_agente anterior. "
            f"Reformule a resposta_agente considerando o feedback do juiz:\n{feedback}"
        )


        # Invoca o agente escolhido para gerar uma nova resposta com base na pergunta reformulada

        resposta_agente = agente_escolhido.invoke({"input": pergunta_nova, "user_id": user_id}, config=session_config)
        resposta = resposta_agente.get("output", resposta_agente)
        


        # devolve a resposta pelo orquestrador
        return chain_orquestrador.invoke({
            "input": resposta,
            "user_id": user_id,
            "chat_history": get_session_history(user_id)
        }, config=session_config)
