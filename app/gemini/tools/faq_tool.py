import os
from langchain_community.document_loaders import TextLoader  # para .md
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_google_genai import GoogleGenerativeAIEmbeddings

MD_PATH = "app/gemini/docs/FAQ_Fluxar.md"

def get_faq_context(question: str):
    """
    Busca os trechos mais relevantes do arquivo Markdown de FAQ com base na pergunta do usuário.
    Retorna uma string contendo os trechos mais parecidos.
    """
    try:
        # Carrega o Markdown como texto
        loader = TextLoader(MD_PATH, encoding="utf-8")
        docs = loader.load()

        # Divide em trechos
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=700,
            chunk_overlap=150
        )
        chunks = splitter.split_documents(docs)

        # Gera embeddings (usa variável de ambiente GEMINI_API_KEY)
        embeddings = GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004",
            google_api_key=os.getenv("GEMINI_API_KEY")
        )

        # Busca com FAISS
        db = FAISS.from_documents(chunks, embeddings)

        results = db.similarity_search(question, k=6)

        context_text = "\n\n".join([r.page_content for r in results])
        return context_text
    except Exception as e:
        # Em caso de qualquer falha, retorne contexto vazio
        try:
            print(f"[faq_tool] erro ao gerar contexto do FAQ: {type(e).__name__}: {e}")
        except Exception:
            pass
        return ""
