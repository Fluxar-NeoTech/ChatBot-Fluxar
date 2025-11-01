from langchain_google_genai import ChatGoogleGenerativeAI
import os 
from dotenv import load_dotenv

load_dotenv()

juiz = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    temperature=0.3,
    google_api_key=os.getenv("GEMINI_API_KEY")
)

prompt_juiz = '''
Você é um avaliador imparcial. Sua tarefa é revisar a resposta do agente de análise de estoque, do agente de faq ou do agente de relatório (consulta, comparação e geração de relatório).

Critérios:
- A resposta está tecnicamente correta?
- As sugestões de melhoria contém fontes e links de referência confiáveis?
- A sugestão está bem formulada?
- O relatório está claro e detalhado?

Se a resposta for boa, diga “Aprovado” e explique por quê.
Se tiver problemas, diga “Reprovado” e proponha uma versão melhorada.
'''

from langchain.schema import HumanMessage, SystemMessage

def avaliar_resposta_agente(pergunta, resposta_agente):
    mensagens = [
        SystemMessage(content=prompt_juiz),
        HumanMessage(content=f"Pergunta: {pergunta}\n\nResposta do tutor: {resposta_agente}")
    ]
    return juiz.invoke(mensagens).content


