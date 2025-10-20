from app.gemini.modelos.orquestrador import chamada_agente
from app.models.pergunta_analista import PerguntaAnalista
from fastapi import FastAPI, APIRouter, Path, Body, status 
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/session")

@router.post("/{user_id}")
async def enviar_resposta(user_id: int = Path(...,title="ID do Usuário", description="Identificador único do usuário"), body: PerguntaAnalista = Body(description="Pergunta enviada pelo usuário")):
    try:
        resposta = chamada_agente(body.pergunta, user_id)  
        return JSONResponse(
            content={"resposta": resposta},
            status_code=status.HTTP_200_OK
        )
    except Exception as e:
        return JSONResponse(
            content={"detail": f"Não foi possível gerar a resposta: {e} "},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR
        )




