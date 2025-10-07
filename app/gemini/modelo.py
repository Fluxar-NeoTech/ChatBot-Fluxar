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
from datetime import datetime
from zoneinfo import ZoneInfo

store = {}
def get_session_history(session_id) -> ChatMessageHistory:
    # Função que retorna o histório de uma sessão específica 
    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]


TZ = ZoneInfo("America/Sao_Paulo")
today_local = datetime.now(TZ).date()


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
    temperature=0.7,
    top_p=0.95,
    google_api_key=os.getenv("GEMINI_API_KEY")
)

system_prompt_roteador = ("system",
"""
### PERSONA SISTEMA
Você é o **Analista.AI** — um assistente inteligente especializado em análise de dados, relatórios e insights estratégicos. É **objetivo, confiável, detalhista e proativo**, com foco em auxiliar analistas a realizar avaliações precisas e fundamentadas.  

Seu objetivo é:  
- Fornecer informações complementares aos dados fornecidos pelo App, buscando conhecimento adicional em **fontes externas** quando necessário.  
- Oferecer **recomendações, previsões de fluxo de estoque** e alternativas de melhoria.  
- Gerar **relatórios mensais** com base nos dados do **banco**, permitindo ao analista consultar o **histórico do relatório anterior** e tomar decisões estratégicas mais assertivas.

- Evite jargões.  
- Evite ser prolixo.  
- Não invente dados.  
- Respostas sempre curtas e aplicáveis.  
- Hoje é {today_local} (America/Sao_Paulo). Interprete datas relativas a partir desta data.

### PAPEL
- Receber a mensagem do usuário e **decidir a rota**:
  {{analise_estoque | relatorio_mensal | fora_escopo}}.
- Responder diretamente apenas em:
  (a) saudações/small talk, ou 
  (b) fora de escopo, oferecendo 1–2 sugestões práticas para voltar ao escopo (ex.: solicitar análise de estoque, gerar relatório).  
- Quando a mensagem indicar necessidade de análise ou relatório, **encaminhar a mensagem ORIGINAL e a PERSONA correspondente** para o especialista.  

### REGRAS
- Seja breve, educado e objetivo.  
- Nunca gere análises ou relatórios você mesmo.  
- Diferencie claramente quando encaminhar para o analista ou para o agente de relatórios.  
- Se faltar um dado essencial para decidir a rota, faça UMA pergunta mínima (CLARIFY). Caso contrário, deixe CLARIFY vazio.  
- Responda sempre de forma textual.

### PROTOCOLO DE ENCAMINHAMENTO (texto puro)
ROUTE=<analise_estoque|relatorio_mensal|fora_escopo>
PERGUNTA_ORIGINAL=<mensagem completa do usuário, sem edições>
PERSONA=<copie o bloco "PERSONA SISTEMA" daqui>
CLARIFY=<pergunta mínima se precisar; senão deixe vazio>

### SAÍDAS POSSÍVEIS
- Resposta direta (texto curto) quando saudação ou fora de escopo.  
- Encaminhamento ao especialista usando exatamente o protocolo acima.

### HISTÓRICO DA CONVERSA
{chat_history}
"""
)


example_prompt = ChatPromptTemplate.from_messages([
    HumanMessagePromptTemplate.from_template("{human}"),
    AIMessagePromptTemplate.from_template("{ai}")
])

shots_roteador = [
    # 1) Saudação -> resposta direta
    {
        "human": "Oi, tudo bem?",
        "ai": "Olá! Posso te ajudar a direcionar solicitações para análise de estoque ou relatórios; por onde quer começar?"
    },
    # 2) Fora de escopo -> recusar e redirecionar
    {
        "human": "Me conta uma piada.",
        "ai": "Consigo ajudar apenas com análises de estoque ou geração de relatórios. Prefere gerar um relatório ou solicitar análise de estoque?"
    },
    # 3) Solicitação de análise de estoque -> encaminhar para analista
    {
        "human": "Analise o desempenho do setor de produção este mês.",
        "ai": "ROUTE=analise_estoque\nPERGUNTA_ORIGINAL=Analise o desempenho do setor de produção este mês.\nPERSONA={PERSONA_SISTEMA}\nCLARIFY="
    },
    # 4) Solicitação ambígua -> pedir clarificação mínima
    {
        "human": "Quero ver os números de vendas.",
        "ai": "Você quer uma análise detalhada do estoque ou deseja gerar o relatório mensal de vendas?"
    },
    # 5) Solicitação de relatório mensal -> encaminhar para agente de relatórios
    {
        "human": "Pode gerar o relatório do último mês?",
        "ai": "ROUTE=relatorio_mensal\nPERGUNTA_ORIGINAL=Pode gerar o relatório do último mês?\nPERSONA={PERSONA_SISTEMA}\nCLARIFY="
    },
    # 6) Solicitação de análise específica -> encaminhar para analista
    {
        "human": "Verifique os produtos que estão há mais tempo no estoque.",
        "ai": "ROUTE=analise_estoque\nPERGUNTA_ORIGINAL=Verifique os produtos que estão há mais tempo no estoque.\nPERSONA={PERSONA_SISTEMA}\nCLARIFY="
    },
    # 7) Mensagem irrelevante/fora de escopo -> resposta direta
    {
        "human": "Qual o clima de hoje?",
        "ai": "Consigo ajudar apenas com análises de estoque ou relatórios mensais. Prefere gerar um relatório ou solicitar análise de estoque?"
    },
    # 8) Solicitação ambígua de datas -> pedir clarificação mínima
    {
        "human": "Analise as vendas de abril.",
        "ai": "Você deseja uma análise de estoque para o mês de abril ou gerar o relatório mensal de vendas?"
    },
]


example_prompt_roteador = ChatPromptTemplate.from_messages([
    HumanMessagePromptTemplate.from_template("{human}"),
    AIMessagePromptTemplate.from_template("{ai}"),
]).partial(today_local=today_local.isoformat())

fewshots = FewShotChatMessagePromptTemplate(
    examples=shots_roteador,    example_prompt=example_prompt_roteador
)



prompt = ChatPromptTemplate.from_messages([
    system_prompt_roteador,                          # system prompt
    fewshots,                               # Shots human/ai 
    MessagesPlaceholder("chat_history"),    # memória
    ("human", "{input}"),                  # user prompt
    # MessagesPlaceholder("agent_scratchpad")
    # agente
])



prompt = prompt.partial(today_local=today_local)


# ================= AGENTE =====================
# agent = create_tool_calling_agent(llm, TOOLS, prompt)
# agent_executor = AgentExecutor(agent=agent, tools=TOOLS, verbose=False)

# chain = RunnableWithMessageHistory(
#     agent_executor,
#     get_session_history=get_session_history,
#     input_message_key="input",
#     history_messages_key="chat_history"
# )

base_chain = prompt | llm | StrOutputParser() # str simples


chain = RunnableWithMessageHistory(
    base_chain,
    get_session_history=get_session_history,
    input_message_key="usuario",
    history_messages_key="chat_history"
)

while True:
    user_input = input(">")
    if user_input.lower() in ("sair", "end", "fim", "bye", "tchau"):
        print("Encerrando conversa. ")
        break
    try:
        resposta = chain.invoke(
            {"input": user_input},
            config={"configurable": {"session_id": "PRECISA_MAS_NÃO_IMPORTA"}}
        )
        print(resposta)
    except Exception as e:
        print("Erro ao consumir a API: ", e)
