# ------------------------------------------------------------ Imports ----------------------------------------------------------------------------


import os
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


# =============================================================== AGENTES ========================================================================


# --------------------------------------------------------------- Analista -----------------------------------------------------------------------

import json


# ------------------------- Carregar system prompt -------------------------

dir_atual = os.path.dirname(__file__)
caminho_prompt = os.path.join(dir_atual, "system_prompt_analista.txt")

with open(caminho_prompt, "r", encoding="utf-8") as f:
    system_prompt_text = f.read()

system_prompt_analista = ("system", system_prompt_text)


# ------------------------- Carregar few-shots -------------------------
dir_atual = os.path.dirname(__file__)
caminho_fewshots = os.path.join(dir_atual, "fewshots_analista.txt")

with open(caminho_fewshots, "r", encoding="utf-8") as f:
    shots_analista = json.load(f)


# fewshots
fewshots_analise = FewShotChatMessagePromptTemplate(
    examples=shots_analista,       # exemplos de análise técnica human/ai
    example_prompt=example_prompt
)


# prompt 
prompt_analise = ChatPromptTemplate.from_messages([
    system_prompt_analista,                 # prompt_roteador de sistema
    fewshots_analise,                      # fewshots de comportamento
    MessagesPlaceholder("chat_history"),   # histórico da conversa
    ("human", "{input}"),                  # entrada do usuário
    MessagesPlaceholder("agent_scratchpad")# para chamadas de ferramentas
]).partial(today_local=today_local.isoformat())


# tool calling
agent_analise = create_tool_calling_agent(llm, TOOLS_ANALISE, prompt_analise)

# executor 
agent_executor_analise = AgentExecutor(
    agent=agent_analise,
    tools=TOOLS_ANALISE,
    verbose=False, 
        handle_parsing_errors=True,
    return_intermediate_steps=True
)

# chain
chain_analista = RunnableWithMessageHistory(
    agent_executor_analise,
    get_session_history=get_session_history,
    input_messages_key="input",
    history_messages_key="chat_history"
)
 