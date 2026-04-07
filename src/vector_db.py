import os
from dotenv import load_dotenv
import chromadb
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import Chroma

# Load environment variables from .env
load_dotenv()


def get_vector_store():
    """Initializes or loads the local ChromaDB vector store."""

    # Grab the key from the environment
    api_key = os.getenv("GOOGLE_API_KEY")

    if not api_key:
        raise ValueError("GOOGLE_API_KEY not found. Check your .env file!")

    # Force the embeddings to use the API Key instead of searching for Cloud Credentials
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/embedding-001",
        google_api_key=api_key,  # <--- THIS IS THE FIX
        task_type="retrieval_document"
    )

    # Path to store the database locally
    persist_directory = "data/chroma_db"

    # Create/Load the vector store
    vector_db = Chroma(
        persist_directory=persist_directory,
        embedding_function=embeddings,
        collection_name="legislai_bills"
    )

    return vector_db


if __name__ == "__main__":
    try:
        db = get_vector_store()
        print("ChromaDB initialized successfully with Google Embeddings.")
    except Exception as e:
        print(f"Initialization failed: {e}")
