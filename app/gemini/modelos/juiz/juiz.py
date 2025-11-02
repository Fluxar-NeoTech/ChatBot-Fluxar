from langchain_google_genai import ChatGoogleGenerativeAI
import os 
from dotenv import load_dotenv

load_dotenv()

juiz = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    temperature=0.3,
    google_api_key=os.getenv("GEMINI_API_KEY")
)

# --------------------------- Carregar system prompt ---------------------------

dir_atual = os.path.dirname(__file__)
caminho_prompt = os.path.join(dir_atual, "system_prompt_juiz.txt")

with open(caminho_prompt, "r", encoding="utf-8") as f:
    system_prompt_text = f.read()

prompt_juiz = ("system", system_prompt_text)


from langchain.schema import HumanMessage, SystemMessage


# Função para avaliar a resposta de um agente com base em uma pergunta
def avaliar_resposta_agente(pergunta, resposta_agente):
    # Monta a lista de mensagens para enviar ao modelo
    mensagens = [
        SystemMessage(content=prompt_juiz),  # System prompt do juiz
        HumanMessage(content=f"Pergunta: {pergunta}\n\nResposta do agente: {resposta_agente}")  # Pergunta + resposta
    ]
    # Invoca o modelo Gemini e retorna o conteúdo da resposta
    return juiz.invoke(mensagens).content
