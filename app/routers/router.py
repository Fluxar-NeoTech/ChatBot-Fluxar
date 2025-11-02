
from app.gemini.modelos.orquestrador.orquestrador import chamada_agente
from app.models.pergunta_analista import PerguntaAnalista
from fastapi import FastAPI, APIRouter, Path, Body, status 
from fastapi.responses import JSONResponse

# definição da rota
router = APIRouter(prefix="/session")

# Definição da rota POST para enviar perguntas e receber respostas
@router.post("/{user_id}")
def enviar_resposta(user_id: int = Path(...,title="ID do Usuário", description="Identificador único do usuário"), body: PerguntaAnalista = Body(description="Pergunta enviada pelo usuário")):
    try:
         # Chama o fluxo do chatbot passando a pergunta do usuário e seu ID, retornando a resposta do chatbot
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




