# ------------------------------------------------------------ Imports ----------------------------------------------------------------------------

import json
from app.gemini.modelos.roteador import chain_roteador
from app.gemini.modelos.agente_analista import agent_executor_analise


# ========================================================= Função de direcionamento de Agentes ==================================================

# Chamada de agentes
def chamada_agente(pergunta: str, user_id: str) -> str:

    session_config = {"configurable": {"user_id": user_id}}
    # ver como usar o user_id aqui 
    resposta_roteador = chain_roteador.invoke(
            {"input":pergunta},
            config=session_config
        )
    if "ROUTE=" not in resposta_roteador:
        return resposta_roteador
   
    elif "ROUTE=analise_estoque" in resposta_roteador:
        resposta = agent_executor_analise.invoke({"input":resposta_roteador},
            config=session_config)
       
    # elif "ROUTE=relatorio_mensal" in resposta_roteador:
    #     resposta = agent_executor_relatorio.invoke({"input":resposta_roteador},
    #         config=session_config)
        
    else:
        # Caso o roteador não se encaixe em nenhuma rota esperada
        return "Rota não reconhecida pelo orquestrador."

    
    if not isinstance(resposta, dict):
        resposta = json.loads(resposta)
    resposta = resposta.get("output",resposta)
    # resposta = chain_orquestrador.invoke({"input":resposta},
    #         config=session_config)
   
    if isinstance(resposta, str):
        try:
            resposta = json.loads(resposta)
        except json.JSONDecodeError:
            pass

        resposta = resposta.get("output",resposta)
    return resposta



# --------------------------------------------------------------- Input/Output --------------------------------------------------------------------

# while True:
#     user_input = input(">")
#     if user_input.lower() in ("sair", "end", "fim", "bye", "tchau"):
#         print("Encerrando conversa. ")
#         break
#     try:
#         resposta = chamada_agente(user_input)
#         print(resposta)
        
#     except Exception as e:
#         print(f"Erro ao consumir a API {e}")
       


      

