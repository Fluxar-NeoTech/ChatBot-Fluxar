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
from app.gemini.modelos.base import today_local, example_prompt, llm, get_session_history
from app.gemini.tools.relatorio_tools import TOOLS_RELATORIO

# =============================================================== AGENTES ========================================================================

# --------------------------------------------------------------- Relatórios ----------------------------------------------------------------------

import json

# ------------------------- Carregar system prompt -------------------------
dir_atual = os.path.dirname(__file__)
caminho_prompt = os.path.join(dir_atual, "system_prompt_relatorio.txt")

with open(caminho_prompt, "r", encoding="utf-8") as f:
    system_prompt_text = f.read()

system_prompt_relatorio = ("system", system_prompt_text)


# ------------------------- Carregar few-shots -------------------------
dir_atual = os.path.dirname(__file__)
caminho_fewshots = os.path.join(dir_atual, "fewshots_relatorio.txt")

with open(caminho_fewshots, "r", encoding="utf-8") as f:
    shots_relatorio = json.load(f)


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
]).partial(
    today_local=today_local.isoformat()
)

# tool calling
agent_relatorio = create_tool_calling_agent(llm, TOOLS_RELATORIO, prompt_relatorio)

# executor 
agent_executor_relatorio = AgentExecutor(
    agent=agent_relatorio,
    tools=TOOLS_RELATORIO,
    verbose=False,
)

# chain
chain_relatorio = RunnableWithMessageHistory(
    agent_executor_relatorio,
    get_session_history=get_session_history,
    input_messages_key="input",
    history_messages_key="chat_history"
)
