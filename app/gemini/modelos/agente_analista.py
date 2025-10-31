# ------------------------------------------------------------ Imports ----------------------------------------------------------------------------


from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_core.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder
)
from langchain_core.prompts.few_shot import FewShotChatMessagePromptTemplate
from langchain.agents import create_tool_calling_agent, AgentExecutor
from app.gemini.tools.analista_tools import TOOLS_ANALISE
from app.gemini.modelos.base import today_local, example_prompt, llm, get_session_history


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
- intencao  : "analisar" | "resumo" | "investigar"
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
        "human": "ROUTE=analise_estoque\nPERGUNTA_ORIGINAL=Mostre a ocupação média dos setores neste mês.\nPERSONA={PERSONA_SISTEMA}\nCLARIFY=",
        "ai": """{{"dominio":"analise","intencao":"resumo","resposta":"A ocupação média geral foi de 72%, com destaque para o setor de frios (85%) e embalagens (68%).","recomendacao":"Avaliar expansão do setor de frios e redistribuição de produtos entre setores.","indicadores":{"ocupacao_media":72.4,"frios":85.0,"embalagens":68.2}}}"""
    },
    {
        "human": "ROUTE=analise_estoque\nPERGUNTA_ORIGINAL=Quais lotes estão próximos da data de validade?\nPERSONA={PERSONA_SISTEMA}\nCLARIFY=",
        "ai": """{{"dominio":"analise","intencao":"alerta","resposta":"Foram encontrados 8 lotes com validade inferior a 15 dias, principalmente no setor de laticínios.","recomendacao":"Priorizar expedição imediata desses lotes ou movimentação para outras unidades","indicadores":{"lotes_em_risco":8,"media_validade_dias":12.4,"setor_critico":"laticínios"}}}"""
    },
    {
        "human": "ROUTE=analise_estoque\nPERGUNTA_ORIGINAL=Mostre a descrição do setor de embalagem.\nPERSONA={PERSONA_SISTEMA}\nCLARIFY=",
        "ai": """{{"dominio":"setor","intencao":"consultar","resposta":"O setor de Embalagem é responsável pela finalização dos produtos, incluindo empacotamento e rotulagem.","recomendacao":"Verificar se há integração entre o setor de embalagem e o de expedição para otimizar o fluxo logístico.","dados":{"setor":"Embalagem","descricao":"Responsável pela finalização dos produtos, empacotamento e rotulagem."}}}"""
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
    verbose=False, 
        handle_parsing_errors=True,
    return_intermediate_steps=True
)

# chain
chain_analista = RunnableWithMessageHistory(
    agent_executor_analise,
    get_session_history=get_session_history,
    input_messages_key="input",
    history_messages_key="chat_history"
)
 