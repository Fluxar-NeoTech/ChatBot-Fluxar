import uvicorn
from app.routers.router import router
from fastapi import FastAPI


app = FastAPI()

app.include_router(router)


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

# from app.gemini.RPA.geracao_relatorios import gerar_relatorio_mensal, gerar_relatorio_resumo
# from app.gemini.modelos.orquestrador import chamada_agente


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

# # from app.gemini.tools.teste import gerar_e_salvar_embeddings

# # gerar_e_salvar_embeddings()