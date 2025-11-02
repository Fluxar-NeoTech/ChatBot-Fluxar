# ------------------------------------------------------------ Imports ----------------------------------------------------------------------------

from dotenv import load_dotenv
import os 
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
from langchain_community.chat_message_histories import ChatMessageHistory
import os 
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    AIMessagePromptTemplate
)
from datetime import datetime
from zoneinfo import ZoneInfo



# Define a data local
TZ = ZoneInfo("America/Sao_Paulo")
today_local = datetime.now(TZ).date()


# histórico temporário
store = {}
def get_session_history(session_id) -> ChatMessageHistory:
    # Função que retorna o histório de uma sessão específica 
    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]


load_dotenv()


# modelo
llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0.7,
    top_p=0.95,
    google_api_key=os.getenv("GEMINI_API_KEY")
)



# ------------------------------------------------------------ Exemplo de estrutura de prompt -----------------------------------------------------

# estrutura de prompt usada em todos os agentes
example_prompt = ChatPromptTemplate.from_messages([
    HumanMessagePromptTemplate.from_template("{human}"),
    AIMessagePromptTemplate.from_template("{ai}")
])