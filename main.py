# import uvicorn
# from app.routers.router import router
# from fastapi import FastAPI

from app.gemini.modelos.orquestrador import chamada_agente

# app = FastAPI()

# app.include_router(router)


# if __name__ == "__main__":
#     uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)

while True:
    user_input = input(">")
    if user_input.lower() in ("sair", "end", "fim", "bye", "tchau"):
        print("Encerrando conversa. ")
        break
    try:
        resposta = chamada_agente(user_input, 2)
        print(resposta)
        
    except Exception as e:
        print(f"Erro ao consumir a API {e}")