import os

# ------------------- Obtém o caminho do arquivo com palavras bloqueadas ------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PATH_PALAVRAS = os.path.join(BASE_DIR, "palavras_bloqueadas.txt")


# -----------------------------------------------------------------------------------------

def carregar_palavras_proibidas():
    """
    Lê o arquivo de palavras bloqueadas e retorna uma lista de palavras proibidas.
    Caso o arquivo não exista, retorna uma lista vazia.
    """
    try:
        with open(PATH_PALAVRAS, "r", encoding="utf-8") as f:
            return [linha.strip().lower() for linha in f if linha.strip()]
    except FileNotFoundError:
        print("[Aviso] Arquivo de palavras bloqueadas não encontrado.")
        return []

def contem_palavra_proibida(texto_usuario: str) -> bool:
    """
    Verifica se o texto enviado pelo usuário contém alguma palavra proibida.
    Retorna True se houver correspondência; caso contrário, False.
    """
    palavras_proibidas = carregar_palavras_proibidas()
    texto_minusculo = texto_usuario.lower()
    return any(palavra in texto_minusculo for palavra in palavras_proibidas)