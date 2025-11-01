import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PATH_PALAVRAS = os.path.join(BASE_DIR, "palavras_bloqueadas.txt")

def carregar_palavras_proibidas():
    try:
        with open(PATH_PALAVRAS, "r", encoding="utf-8") as f:
            return [linha.strip().lower() for linha in f if linha.strip()]
    except FileNotFoundError:
        print("[Aviso] Arquivo de palavras bloqueadas não encontrado.")
        return []

def contem_palavra_proibida(texto_usuario: str) -> bool:
    palavras_proibidas = carregar_palavras_proibidas()
    texto_minusculo = texto_usuario.lower()
    return any(palavra in texto_minusculo for palavra in palavras_proibidas)