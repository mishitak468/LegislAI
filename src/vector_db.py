import os
from dotenv import load_dotenv
import chromadb
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma

load_dotenv()


def get_vector_store():
    """Initializes or loads the local ChromaDB vector store."""

    api_key = os.getenv("GOOGLE_API_KEY")

    if not api_key:
        raise ValueError("GOOGLE_API_KEY not found. Check your .env file!")

    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/gemini-embedding-2-preview",  # Updated model name
        google_api_key=api_key,
        task_type="retrieval_document"
    )

    persist_directory = "data/chroma_db"

    vector_db = Chroma(
        persist_directory=persist_directory,
        embedding_function=embeddings,
        collection_name="legislai_bills"
    )

    return vector_db


if __name__ == "__main__":
    try:
        db = get_vector_store()
        print("ChromaDB initialized successfully with Google Embeddings 2.")
    except Exception as e:
        print(f"Initialization failed: {e}")
