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
from app.gemini.tools.faq_tool import buscar_no_mongo
from operator import itemgetter
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser


# --------------------------------------------------------------- FAQ ----------------------------------------------------------------------


# --------------------------- Carregar system prompt ---------------------------
dir_atual = os.path.dirname(__file__)
caminho_prompt = os.path.join(dir_atual, "system_prompt_faq.txt")

with open(caminho_prompt, "r", encoding="utf-8") as f:
    system_prompt_text = f.read()
system_prompt_faq = ("system", system_prompt_text)


#prompt
prompt_faq = ChatPromptTemplate.from_messages([
    system_prompt_faq,
    ("human",
     "Pergunta do usuário:\n{question}\n\n"
     "CONTEXTO (trechos do documento):\n{context}\n\n"
     "Responda com base APENAS no CONTEXTO.")
])

# Função para buscar contexto no MongoDB
def get_faq_context(question: str) -> str:
    return buscar_no_mongo(question, k=6)

#chain
chain_faq = (
    RunnablePassthrough.assign(
        question=itemgetter("input"),
        context=lambda x: get_faq_context(x["input"])
    )
    | prompt_faq | llm | StrOutputParser()
)



