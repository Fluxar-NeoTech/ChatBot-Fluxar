from pydantic import BaseModel

# classe no pydantic para o conteúdo recebido no body da API
class PerguntaAnalista(BaseModel):
    pergunta: str