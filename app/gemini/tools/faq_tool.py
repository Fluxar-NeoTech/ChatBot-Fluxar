import os
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from pymongo import MongoClient
from dotenv import load_dotenv

MD_PATH = "app/gemini/docs/FAQ_Fluxar.md" # Caminho do arquivo FAQ em Markdown
load_dotenv()


# conexão com o MongoDB
client = MongoClient(os.getenv("MONGO_URI"))
db = client["Embedding-FAQ"]
collection = db["embedding"]

def gerar_e_salvar_embeddings():
    """Carrega o FAQ, divide em chunks e salva embeddings no Mongo."""
    loader = TextLoader(MD_PATH, encoding="utf-8")  # Lê o arquivo Markdown
    docs = loader.load()  # Carrega o conteúdo do documento

    # Divide o texto em pedaços menores para melhor geração de embeddings
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=700,
        chunk_overlap=150
    )
    chunks = splitter.split_documents(docs)

    # Cria modelo de embeddings usando API do Google Gemini
    embeddings_model = GoogleGenerativeAIEmbeddings(
        model="models/text-embedding-004",
        google_api_key=os.getenv("GEMINI_API_KEY")
    )

    documentos_gerados = []  # Lista para armazenar os documentos gerados

    # Gera embeddings para cada chunk e salva no MongoDB
    for i, chunk in enumerate(chunks):
        text = chunk.page_content
        vector = embeddings_model.embed_query(text)  # Gera embedding

        doc = {
            "text": text,
            "embedding": vector,
            "metadata": {
                "source": MD_PATH,
                "chunk_id": i
            }
        }
        collection.insert_one(doc)  # Salva no Mongo
        documentos_gerados.append(doc)  # Adiciona à lista de documentos gerados

    print(f"{len(chunks)} embeddings salvos no MongoDB")
    return documentos_gerados  # Retorna todos os documentos gerados



def buscar_no_mongo(question: str, k=6):
    """Busca os chunks mais relevantes no MongoDB usando vetor da pergunta."""
    embeddings_model = GoogleGenerativeAIEmbeddings(
        model="models/text-embedding-004",
        google_api_key=os.getenv("GEMINI_API_KEY")
    )

    query_vector = embeddings_model.embed_query(question) # Gera embedding da pergunta

    # Pipeline de agregação MongoDB para busca vetorial
    pipeline = [
        {
            "$vectorSearch": {
                "index": "vector_index",
                "queryVector": query_vector,
                "path": "embedding",
                "numCandidates": 100,
                "limit": k
            }
        },
        {
            "$project": {
                "_id": 0,
                "text": 1,
                "score": {"$meta": "vectorSearchScore"}
            }
        }
    ]

    # Executa a busca
    results = list(collection.aggregate(pipeline))

    # Junta os textos dos chunks encontrados em um único contexto
    context_text = "\n\n".join([
    r.get("text", "")
    for r in results
    if r.get("text")  # garante que o texto existe
    ])


    return context_text


def reset_embeddings(atualizar=False):
    """
    Se atualizar=False, deleta todos os documentos da coleção e gera embeddings do zero.
    Se atualizar=True, sobrescreve os embeddings existentes ou adiciona novos.
    """
    if not atualizar:
        print("Deletando todos os embeddings existentes...")
        collection.drop()
        print("Coleção deletada. Criando novamente e gerando embeddings...")

    embeddings = gerar_e_salvar_embeddings()   # Gera novos embeddings

    if atualizar:
        # Atualiza embeddings existentes ou adiciona novos 
        for emb in embeddings:
            # usa 'faq_id' como identificador único
            collection.replace_one({"faq_id": emb["faq_id"]}, emb, upsert=True)
        print("Embeddings existentes atualizados ou adicionados.")
    else:
        # Insere todos os embeddings de uma vez (pode gerar duplicados)
        collection.insert_many(embeddings)
        print("Embeddings criados do zero.")
