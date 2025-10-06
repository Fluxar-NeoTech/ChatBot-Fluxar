from dotenv import load_dotenv
import os 
import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain.memory import ChatMessageHistory
import os 
import google.generativeai as genai
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    AIMessagePromptTemplate,
    MessagesPlaceholder
)
from langchain_core.prompts.few_shot import FewShotChatMessagePromptTemplate
from langchain.agents import create_tool_calling_agent, AgentExecutor


# Somente por enquanto
# Depois guardaremos no Mongo ou redis
store = {}
def get_session_history(session_id) -> ChatMessageHistory:
    # Função que retorna o histório de uma sessão específica 
    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]


load_dotenv()

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    # rever se o system_instruction pode ser usado aqui msm
    temperature=0.7,
    top_p=0.95,
    google_api_key=os.getenv("GEMINI_API_KEY")
)

system_prompt = "1° ANO"

example_prompt = ChatPromptTemplate.from_messages([
    HumanMessagePromptTemplate.from_template("{human}"),
    AIMessagePromptTemplate.from_template("{ai}")
])

shots = [
    "1° ANO"
]

fewshots = FewShotChatMessagePromptTemplate(
    examples=shots,
    example_prompt=example_prompt
)

# try:
#     # rotina para enviar pergunta ao modelo
#     def responder_pergunta(pergunta: str) -> str:
#         resposta = llm.generate_content(pergunta)
#         return resposta.text.strip()
# except Exception as e:
#     print("Erro ao consumir a API:", e)



