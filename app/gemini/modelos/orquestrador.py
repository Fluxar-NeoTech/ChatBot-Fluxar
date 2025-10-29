# ------------------------------------------------------------ Imports ----------------------------------------------------------------------------

import json
from app.gemini.modelos.roteador import chain_roteador
from app.gemini.modelos.agente_analista import chain_analista
from app.gemini.modelos.faq import chain_faq
from app.gemini.modelos.agente_relatorio import chain_relatorio
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
from langchain_core.output_parsers import StrOutputParser


# --------------------------------------------------------------- Orquestrador -----------------------------------------------------------------------
 

# Sistem_prompt
system_prompt_orquestrador = ("system",
    """
### PAPEL
Você é o Agente Orquestrador do Flux.AI. Sua função é entregar a resposta final ao usuário **somente** quando um Especialista retornar o JSON.
 
 
### ENTRADA
- ESPECIALISTA_JSON contendo chaves como:
dominio, intencao, resposta, recomendacao (opcional), acompanhamento (opcional),
esclarecer (opcional), janela_tempo (opcional), evento (opcional), escrita (opcional), indicadores (opcional).
 
 
### REGRAS
- Use **exatamente** `resposta` do especialista como a **primeira linha** do output.
- Se `recomendacao` existir e não for vazia, inclua a seção *Recomendação*; caso contrário, **omita**.
- Para *Acompanhamento*: se houver `esclarecer`, use-o; senão, se houver `acompanhamento`, use-o; caso contrário, **omita** a seção.
- Não reescreva números/datas se já vierem prontos. Não invente dados. Seja conciso.
- Não retorne JSON; **sempre** retorne no FORMATO DE SAÍDA.
 
 
### FORMATO DE SAÍDA (sempre ao usuário)
<sua resposta será 1 frase objetiva sobre a situação>
- *Recomendação*:
<ação prática e imediata>     # omita esta seção se não houver recomendação
- *Acompanhamento* (opcional):
<pergunta/minipróximo passo>  # omita se nada for necessário
 
 
### HISTÓRICO DA CONVERSA
{chat_history}
"""
)

# shots
shots_orquestrador = [

    # ======================================================
    # RELATÓRIOS
    # ======================================================

    # 1) Gerar relatório por período (com documento retornado)
    {
        "human": "ROUTE=analise_relatorios\nPERGUNTA_ORIGINAL=Gerar relatório de movimentação entre 2025-09-01 e 2025-09-30\nPERSONA={PERSONA_SISTEMA}\nCLARIFY=",
        "ai": """{{"dominio":"analise_relatorios","intencao":"gerar_relatorio_periodo","resposta":"O relatório de movimentação entre 2025-09-01 e 2025-09-30 foi gerado com sucesso. O saldo final foi de 438 L, com ocupação média de 72%.","recomendacao":"Deseja que eu gere também as sugestões de otimização de estoque?","janela_tempo":{{"de":"2025-09-01","ate":"2025-09-30","rotulo":"setembro/2025"}},"documento":{{"relatorio_id":"relat_2025_09","periodo":{{"de":"2025-09-01","ate":"2025-09-30","rotulo":"setembro/2025"}},"dados":{{"saldo_final_L":438,"ocupacao_media_%":72,"entradas_total_L":980,"saidas_total_L":542}},"setores":[{{"nome":"Produção","uso_L":220,"ocupacao_%":68}},{{"nome":"Armazenagem","uso_L":180,"ocupacao_%":75}},{{"nome":"Distribuição","uso_L":38,"ocupacao_%":55}}],"gerado_em":"2025-10-01T09:30:00","responsavel":"Agente de Análise de Relatórios"}}}}"""
    },

    # 2) Comparar relatórios mensais
    {
        "human": "ROUTE=analise_relatorios\nPERGUNTA_ORIGINAL=Comparar relatórios de 2025-09 e 2025-10\nPERSONA={PERSONA_SISTEMA}\nCLARIFY=",
        "ai": """{{"dominio":"analise_relatorios","intencao":"comparar_relatorios_mensais","resposta":"Comparação concluída entre os meses 2025-09 e 2025-10: houve aumento de 85 L em entradas e queda de 40 L em saídas.","recomendacao":"Quer que eu apresente o gráfico de variação mês a mês?","documento":{{"comparacao_id":"cmp_2025_09_10","periodos":["2025-09","2025-10"],"diferencas":{{"entradas_L":85,"saidas_L":-40,"ocupacao_var_%":3.5}},"observacoes":["Aumento nas entradas devido a reabastecimento da linha de Produção.","Redução nas saídas por desaceleração da demanda em Distribuição."],"gerado_em":"2025-10-15T11:10:00","responsavel":"Agente de Análise de Relatórios"}}}}"""
    },

    # ======================================================
    # ANALISE_ESTOQUE
    # ======================================================

    # 1) Consultar níveis de estoque
    {
        "human": "ROUTE=analise_estoque\nPERGUNTA_ORIGINAL=Consultar níveis de estoque do produto Álcool Etílico\nPERSONA={PERSONA_SISTEMA}\nCLARIFY=",
        "ai": """{{"dominio":"analise_estoque","intencao":"consultar_nivel","resposta":"Os níveis de estoque estão dentro da faixa segura. O produto 'Álcool Etílico' apresenta 62% da capacidade ocupada.","recomendacao":"Quer que eu verifique o histórico de consumo desse item?","documento":{{"produto":"Álcool Etílico","nivel_atual_%":62,"capacidade_total_L":1200,"estoque_atual_L":744,"status":"seguro","ultima_atualizacao":"2025-10-25T08:20:00"}}}}"""
    },

    # 2) Detectar anomalias ou inconsistências
    {
        "human": "ROUTE=analise_estoque\nPERGUNTA_ORIGINAL=Detectar anomalias no setor de Armazenagem\nPERSONA={PERSONA_SISTEMA}\nCLARIFY=",
        "ai": """{{"dominio":"analise_estoque","intencao":"detectar_anomalias","resposta":"Foram detectadas inconsistências no setor de Armazenagem: divergência de 48 L entre o estoque físico e o registrado.","recomendacao":"Deseja que eu gere um relatório detalhado da auditoria?","documento":{{"setor":"Armazenagem","divergencia_L":48,"tipo_inconsistencia":"estoque_fisico_vs_sistema","data_detectada":"2025-10-26T15:40:00","responsavel_verificacao":"Agente de Análise de Estoque"}}}}"""
    },
    {
        "human": "ROUTE=faq\nPERGUNTA_ORIGINAL=qual o e-mail de suporte?\nPERSONA={{PERSONA_SISTEMA}}\nCLARIFY=",
        "ai": """{{"dominio":"faq","intencao":"consultar_faq","resposta":"Você pode entrar em contato com nossa equipe de suporte pelo e-mail suporte2025.neo.tech@gmail.com.","recomendacao":"Se preferir, posso também abrir um chamado diretamente no sistema para você.","documento":{{"tipo":"contato_suporte","email":"suporte2025.neo.tech@gmail.com","canal_alternativo":"formulário de suporte no portal Neo Tech","ultima_atualizacao":"2025-10-29T14:00:00","responsavel":"Atendimento Neo Tech"}}}}"""
    },

]

# fewshots
fewshots_orquestrador = FewShotChatMessagePromptTemplate(
    examples=shots_orquestrador,
    example_prompt=example_prompt,
)
 
# prompt 
prompt_orquestrador  = ChatPromptTemplate.from_messages([
    system_prompt_orquestrador,                          # system prompt
    fewshots_orquestrador,                               # Shots human/ai
    MessagesPlaceholder(variable_name="chat_history"),    # memória
    ("human", "{input}"),                  # user prompt
]).partial(today_local=today_local.isoformat())

# chain 
chain_orquestrador = RunnableWithMessageHistory(
    prompt_orquestrador | llm | StrOutputParser(),
    get_session_history=get_session_history,
    input_messages_key="input",
    history_messages_key="chat_history",
)


# ========================================================= Função de direcionamento de Agentes ==================================================

# Chamada de agentes
def chamada_agente(pergunta: str, user_id: int):

    session_config = {"configurable": {"session_id": user_id}}
    # ver como usar o user_id aqui 
    resposta_roteador = chain_roteador.invoke(
            {"input":pergunta},
            config=session_config
        )
    if "ROUTE=" not in resposta_roteador:
        return resposta_roteador
   
    elif "ROUTE=analise_estoque" in resposta_roteador:
        resposta = chain_analista.invoke({"input":resposta_roteador},
            config=session_config)

       
    elif "ROUTE=relatorio_mensal" in resposta_roteador:
        resposta = chain_relatorio.invoke({"input":resposta_roteador},
            config=session_config)
        
    elif "ROUTE=faq" in resposta_roteador:
        resposta = chain_faq.invoke({"input":resposta_roteador},
            config=session_config)
        
    else:
        # Caso o roteador não se encaixe em nenhuma rota esperada
        return "Rota não reconhecida pelo orquestrador."

    
    if not isinstance(resposta, dict):
        resposta = json.loads(resposta)
    resposta = resposta.get("output",resposta)
    resposta = chain_orquestrador.invoke({"input":resposta, "chat_history": get_session_history(user_id)  # Passando o histórico
    },
            config=session_config)
   
    if isinstance(resposta, str):
        try:
            resposta = json.loads(resposta)
        except json.JSONDecodeError:
            pass
    else:
        resposta = resposta.get("output",resposta)
    return resposta



# --------------------------------------------------------------- Input/Output --------------------------------------------------------------------

# while True:
#     user_input = input(">")
#     if user_input.lower() in ("sair", "end", "fim", "bye", "tchau"):
#         print("Encerrando conversa. ")
#         break
#     try:
#         resposta = chamada_agente(user_input, 2)
#         print(resposta)
        
#     except Exception as e:
#         print(f"Erro ao consumir a API {e}")
       


      

