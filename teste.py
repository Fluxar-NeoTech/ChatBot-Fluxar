    
# import os
# from dotenv import load_dotenv
# from pymongo import MongoClient
# from app.gemini.tools.faq_tool import gerar_e_salvar_embeddings

# load_dotenv() 
# mongo_uri = os.getenv("MONGO_URI")

# client = MongoClient(mongo_uri)
# db = client["Embedding-FAQ"]
# col = db["embedding"]

# gerar_e_salvar_embeddings()


# for doc in col.find().limit(3):
#     print(doc.keys())