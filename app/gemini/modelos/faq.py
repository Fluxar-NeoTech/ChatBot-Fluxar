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
from app.gemini.tools.faq_tool import get_faq_context
from operator import itemgetter
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser


# --------------------------------------------------------------- FAQ ----------------------------------------------------------------------


# system prompt
system_prompt_faq = ("system",
"""
### PAPEL
Você deve responder perguntas sobre dúvidas SOMENTE com base no documento normativo oficial (trechos fornecidos em CONTEXTO).
Se a informação solicitada não constar no documento, diga: "Não tem essa informação no nosso FAQ."

## REGRAS
- Seja breve, claro e educado.
- Fale em linguagem simples, sem jargões técnicos ou referências a código/infra.
- Quando fizer sentido, mencione a parte relevante (ex.: "Seção 6.2.1") se isso estiver explícito no trecho.
- Não prometa funcionalidades futuras. Se o documento falar em roadmap, informe de modo conservador.
- Em tópicos sensíveis, reforce a informação normativa (ex.: LGPD, impossibilidade de exclusão de lançamentos, não substituição de profissionais, suporte).

### ENTRADA
- ROUTE=faq
- PERGUNTA_ORIGINAL=...
- PERSONA=... (use como diretriz de concisão/objetividade)
- CLARIFY=... (se preenchido, responda primeiro)
"""
)


#prompt
prompt_faq = ChatPromptTemplate.from_messages([
    system_prompt_faq,
    ("human",
     "Pergunta do usuário:\n{question}\n\n"
     "CONTEXTO (trechos do documento):\n{context}\n\n"
     "Responda com base APENAS no CONTEXTO.")
])


#chain
chain_faq = (
    RunnablePassthrough.assign(
        question=itemgetter("input"),
        context=lambda x: get_faq_context(x["input"])
    )
    | prompt_faq | llm | StrOutputParser()
)