# ------------------------------------------------------------ Imports ----------------------------------------------------------------------------


import json
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables.history import RunnableWithMessageHistory
import os 
from langchain_core.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder
)
from langchain_core.prompts.few_shot import FewShotChatMessagePromptTemplate
from app.gemini.modelos.base import today_local, example_prompt, llm, get_session_history


# =============================================================== ROTEADOR ========================================================================

# -------------------------------------------------------- Carregar system prompt -----------------------------------------------------------------
dir_atual = os.path.dirname(__file__)
caminho_prompt = os.path.join(dir_atual, "system_prompt_roteador.txt")

with open(caminho_prompt, "r", encoding="utf-8") as f:
    system_prompt_text = f.read()

system_prompt_roteador = ("system", system_prompt_text)


# ----------------------------------------------------------- Carregar few-shots -------------------------------------------------------------------

dir_atual = os.path.dirname(__file__)
caminho_fewshots = os.path.join(dir_atual, "fewshots_roteador.txt")

with open(caminho_fewshots, "r", encoding="utf-8") as f:
    shots_roteador = json.load(f)
# fewshots
fewshots = FewShotChatMessagePromptTemplate(
    examples=shots_roteador,    example_prompt=example_prompt
)

# prompt 
prompt_roteador = ChatPromptTemplate.from_messages([
    system_prompt_roteador,                          # system prompt
    fewshots,                               # Shots human/ai 
    MessagesPlaceholder("chat_history"),    # memória
    ("human", "{input}"),                  # user prompt
]).partial(today_local=today_local)


# chain 
base_chain = prompt_roteador | llm | StrOutputParser() # str simples


# RunnableWithMessageHistory
chain_roteador = RunnableWithMessageHistory(
    base_chain,
    get_session_history=get_session_history,
    input_messages_key="input",
    history_messages_key="chat_history"
)
