from app.gemini.modelo import chamada_agente
from app.models.pergunta_analista import PerguntaAnalista
from fastapi import FastAPI, APIRouter, Path, Body, JSONResponse, status 


router = APIRouter(prefix="/session")

@router.post("/{user_id}")
async def enviar_resposta(user_id: int = Path(...,title="ID do Usuário", description="Identificador único do usuário"), body: PerguntaAnalista = Body(description="Pergunta enviada pelo usuário")):
    resposta = chamada_agente(body.pergunta, user_id)  
    if resposta:
        return JSONResponse(
            content={"resposta": resposta},
            status_code=status.HTTP_200_OK
        )
    else:
        return JSONResponse(
            content={"detail": "Não foi possível gerar a resposta. "},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )




