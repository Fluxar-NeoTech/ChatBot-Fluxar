import re

def aplicar_output_guardrail(resposta_modelo: str) -> str:
    padroes_proibidos = [
        r"\bpalavrão\b",
        r"informação confidencial",
        r"https?://[^\s]+"
    ]

    texto_filtrado = resposta_modelo
    for padrao in padroes_proibidos:
        texto_filtrado = re.sub(padrao, "[conteúdo removido]", texto_filtrado, flags=re.IGNORECASE)

    if any(x in texto_filtrado.lower() for x in ["ignore as regras", "prompt secreto", "sistema oculto"]):
        texto_filtrado = "⚠️ Resposta bloqueada por segurança."

    return texto_filtrado
