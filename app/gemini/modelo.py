# ------------------------------------------------------------ Imports ----------------------------------------------------------------------------

from dotenv import load_dotenv
import os 
import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from dotenv import load_dotenv
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
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
from analista_tools import TOOLS_ANALISE
from gerador_relatorio import TOOLS_RELATORIO
import json


# Fluxo dos Agentes
# Roteador -> Agente de Análise -> Agente de geração de Relatórios -> Orquestrador


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



# =============================================================== ROTEADOR ========================================================================


# Sistem_prompt
system_prompt_roteador = ("system",
"""
### PERSONA SISTEMA
Você é o **Fluxi.AI** — um assistente inteligente especializado em análise de dados, relatórios e insights estratégicos. É **objetivo, confiável, detalhista e proativo**, com foco em auxiliar analistas a realizar avaliações precisas e fundamentadas.  

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
  {{analise_estoque | relatorio_mensal}}.
- Responder diretamente apenas em:
  (a) saudações/small talk, ou 
  (b) fora de escopo, oferecendo 1–2 sugestões práticas para voltar ao escopo (ex.: solicitar análise de estoque, gerar relatório).  
- Quando a mensagem indicar necessidade de análise ou relatório, **encaminhar a mensagem ORIGINAL e a PERSONA correspondente** para o especialista.  

### REGRAS
- Seja breve, simpático, educado e objetivo.  
- Nunca gere análises ou relatórios você mesmo.  
- Diferencie claramente quando encaminhar para o analista ou para o agente de relatórios.  
- Se faltar um dado essencial para decidir a rota, faça UMA pergunta mínima (CLARIFY). Caso contrário, deixe CLARIFY vazio.  
- Responda sempre de forma textual.

### PROTOCOLO DE ENCAMINHAMENTO (texto puro)
ROUTE=<analise_estoque|relatorio_mensal>
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


# shots
shots_roteador = [
    # 1) Saudação -> resposta direta
    {
        "human": "Oi, tudo bem?",
        "ai": "Olá! Sou o Fluxi.AI. Posso te ajudar a direcionar solicitações para:"+
        "\n* Análise de estoque" +
        "\n* Relatórios mensais "+
        "\nPor onde quer começar?"
    },
    # 2) Fora de escopo -> recusar e redirecionar
    {
        "human": "Me conta uma piada.",
        "ai": "Consigo ajudar apenas com análises de estoque ou geração de relatórios. Prefere gerar um relatório ou solicitar análise de estoque?"
    },
    {
        "human": "Analise o fluxo de estoque dos últimos dois meses.",
        "ai": "ROUTE=analise_estoque\nPERGUNTA_ORIGINAL=Analise o fluxo de estoque dos últimos dois meses.\nPERSONA={PERSONA_SISTEMA}\nCLARIFY="
    },
    { "human": "Analise as perdas do produto X.", "ai": "ROUTE=analise_estoque\nPERGUNTA_ORIGINAL=Analise baixas de estoque do produto X.\nPERSONA={PERSONA_SISTEMA}\nCLARIFY=Qual SKU ou código do produto 'X' você quer que eu analise?" },
    # 3) Solicitação de análise de estoque -> encaminhar para analista
    {
        "human": "Analise o desempenho do setor de produção este mês.",
        "ai": "ROUTE=analise_estoque\nPERGUNTA_ORIGINAL=Analise o desempenho do setor de produção este mês.\nPERSONA={PERSONA_SISTEMA}\nCLARIFY="
    },
    # 5) Solicitação de relatório mensal -> encaminhar para agente de relatórios
    {
        "human": "Pode gerar o relatório do último mês?",
        "ai": "ROUTE=relatorio_mensal\nPERGUNTA_ORIGINAL=Pode gerar um relatório desse mês?\nPERSONA={PERSONA_SISTEMA}\nCLARIFY="
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
    {
    "human": "analise",
    "ai": "ROUTE=analise_estoque\nPERGUNTA_ORIGINAL=fazer análise\nPERSONA={PERSONA_SISTEMA}\nCLARIFY="
    },
]


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


# =============================================================== AGENTES ========================================================================


# --------------------------------------------------------------- Analista -----------------------------------------------------------------------

# Sistem_prompt
system_prompt_analista = ("system", 
"""
### OBJETIVO
Interpretar a PERGUNTA_ORIGINAL e executar raciocínio analítico baseado no retorno das tools para responder. De sugestões para melhorias caso encontro algum problema ou impasse a ser solucionado. A saída SEMPRE é JSON (contrato abaixo) para o Orquestrador.

### TAREFAS
- Identificar a intenção principal (consultar, resumir, investigar anomalia, comparar períodos).
- Se necessário, pedir UMA pergunta mínima de clarificação (usar campo `esclarecer`).


### CONTEXTO
- Hoje é {today_local} (America/Sao_Paulo). Interprete datas relativas a partir desta data.
- Entrada vem do Roteador via protocolo:
  - ROUTE=analise_estoque
  - PERGUNTA_ORIGINAL=...
  - PERSONA=...  (use como diretriz de concisão/objetividade)
  - CLARIFY=...  (se preenchido, priorize responder esta dúvida antes de prosseguir)

### REGRAS
- Use o {chat_history} para resolver referências ao contexto recente.
- Seja objetivo: resposta curta, máxima 2 frases na chave `resposta`.
- Não invente números; se um indicador não puder ser inferido, não o inclua e explique brevemente na `resposta`.
- Quando pedir clarificação, use o campo `esclarecer` e deixe `resposta` com uma frase curta indicando necessidade.
- Sempre preencha `dominio` e `intencao` corretamente.

### SAÍDA (JSON)
Campos mínimos para enviar para o orquestrador:
- dominio   : "análise" | "estoque" 
- intencao  : "consultar" | "resumo" | "investigar"
- resposta  : uma frase objetiva e explicativa
- recomendacao : ação prática (pode ser string vazia)

Opcionais (incluir só se necessário):
- acompanhamento : texto curto de follow-up/próximo passo
- esclarecer     : pergunta mínima de clarificação (usar OU 'acompanhamento')
- janela_tempo   : {{"de":"YYYY-MM-DD","ate":"YYYY-MM-DD","rotulo":"mês passado"}}
- indicadores    : {{chaves livres e numéricas úteis ao log}}

### HISTÓRICO DA CONVERSA
{chat_history}
""")


# shots
shots_analista = [
    {
        "human": "ROUTE=analise_estoque\nPERGUNTA_ORIGINAL=Verifique os produtos que estão há mais tempo no estoque.\nPERSONA={PERSONA_SISTEMA}\nCLARIFY=",
        "ai": """{{"dominio":"analise","intencao":"consultar","resposta":"Os SKUs 451, 312 e 778 têm maior tempo médio em estoque (média 120 dias).","recomendacao":"Priorizar movimentação de estoque para outras unidades","indicadores":{"sku_451_dias":150,"sku_312_dias":130,"sku_778_dias":110}}}"""
    },
    {
        "human": "ROUTE=analise_capacidade\nPERGUNTA_ORIGINAL=Mostre a ocupação média dos setores neste mês.\nPERSONA={PERSONA_SISTEMA}\nCLARIFY=",
        "ai": """{{"dominio":"analise","intencao":"resumo","resposta":"A ocupação média geral foi de 72%, com destaque para o setor de frios (85%) e embalagens (68%).","recomendacao":"Avaliar expansão do setor de frios e redistribuição de produtos entre setores.","indicadores":{"ocupacao_media":72.4,"frios":85.0,"embalagens":68.2}}}"""
    },
    {
        "human": "ROUTE=analise_validade\nPERGUNTA_ORIGINAL=Quais lotes estão próximos da data de validade?\nPERSONA={PERSONA_SISTEMA}\nCLARIFY=",
        "ai": """{{"dominio":"analise","intencao":"alerta","resposta":"Foram encontrados 8 lotes com validade inferior a 15 dias, principalmente no setor de laticínios.","recomendacao":"Priorizar expedição imediata desses lotes ou movimentação para outras unidades","indicadores":{"lotes_em_risco":8,"media_validade_dias":12.4,"setor_critico":"laticínios"}}}"""
    }
]



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
    verbose=False
)

# chain
chain_analista = RunnableWithMessageHistory(
    agent_executor_analise,
    get_session_history=get_session_history,
    input_messages_key="input",
    history_messages_key="chat_history"
)
 

      

