import uvicorn
from app.routers.router import router
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Cria a instância principal da aplicação FastAPI
app = FastAPI()

# Configura o middleware de CORS para permitir requisições de qualquer origem

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Inclui o roteador principal na aplicação
app.include_router(router)

# Bloco principal para rodar a aplicação quando executado diretamente
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

