import os
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from pymongo import MongoClient

MD_PATH = "app/gemini/docs/FAQ_Fluxar.md"

# 🔹 conexão com o MongoDB
client = MongoClient(os.getenv("MONGO_URI"))
db = client["Embedding-FAQ"]
collection = db["embedding"]

def gerar_e_salvar_embeddings():
    """Carrega o FAQ, divide em chunks e salva embeddings no Mongo."""
    loader = TextLoader(MD_PATH, encoding="utf-8")
    docs = loader.load()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=700,
        chunk_overlap=150
    )
    chunks = splitter.split_documents(docs)

    embeddings_model = GoogleGenerativeAIEmbeddings(
        model="models/text-embedding-004",
        google_api_key=os.getenv("GEMINI_API_KEY")
    )

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
        collection.insert_one(doc)

    print(f"{len(chunks)} embeddings salvos no MongoDB ✅")


def buscar_no_mongo(question: str, k=6):
    embeddings_model = GoogleGenerativeAIEmbeddings(
        model="models/text-embedding-004",
        google_api_key=os.getenv("GEMINI_API_KEY")
    )

    query_vector = embeddings_model.embed_query(question)

    pipeline = [
        {
            "$vectorSearch": {
                "queryVector": query_vector,
                "path": "embedding",
                "numCandidates": 50,
                "limit": k
            }
        },
        {"$project": {"text": 1, "score": {"$meta": "vectorSearchScore"}}}
    ]

    results = list(collection.aggregate(pipeline))
    context_text = "\n\n".join([r["text"] for r in results])
    return context_text
