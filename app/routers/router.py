from app.gemini.modelo import chamada_agente
from app.models.pergunta_analista import PerguntaAnalista
from fastapi import FastAPI, APIRouter, Path, Body


router = APIRouter(prefix="/session")

@router.post("/{user_id}")
async def enviar_resposta(user_id: int = Path(...,title="ID do Usuário", description="Identificador único do usuário"), body: PerguntaAnalista = Body(description="Pergunta enviada pelo usuário")):
    resposta = chamada_agente(body.pergunta, user_id)  
    return {"resposta": resposta}




