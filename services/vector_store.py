from typing import List
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from models.schema import ChunkModel
import os

FAISS_INDEX_DIR = "faiss_index"

class VectorStoreManager:
    def __init__(self):
        self.embeddings = HuggingFaceEmbeddings(model_name="BAAI/bge-m3")
        self.vector_store = None
        self._load_or_create_index()

    def _load_or_create_index(self):
        if os.path.exists(FAISS_INDEX_DIR) and os.listdir(FAISS_INDEX_DIR):
            print("Loading existing FAISS index...")
            self.vector_store = FAISS.load_local(
                FAISS_INDEX_DIR, 
                self.embeddings,
                allow_dangerous_deserialization=True
            )
        else:
            print("Creating new FAISS index...")
            self.vector_store = None

    def add_chunks(self, chunks: List[ChunkModel]):
        if not chunks:
            return

        texts = [c.text for c in chunks]
        metadatas = [{"chunk_id": c.chunk_id, "document_id": c.document_id, **c.metadata} for c in chunks]
        
        if self.vector_store is None:
            self.vector_store = FAISS.from_texts(texts, self.embeddings, metadatas=metadatas)
        else:
            self.vector_store.add_texts(texts, metadatas=metadatas)
            
        # Save to disk
        self.vector_store.save_local(FAISS_INDEX_DIR)
        print(f"Saved {len(texts)} chunks to FAISS index.")

# Dependency injection
vector_store_manager = VectorStoreManager()

def get_vector_store():
    return vector_store_manager
