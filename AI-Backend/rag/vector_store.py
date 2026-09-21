from pathlib import Path

from langchain_community.vectorstores import FAISS

from rag.embeddings import get_embedding_model
from rag.ingestion import load_and_split


VECTOR_DB_PATH = Path("vector_db/faiss_index")


def create_vector_store(file_path: str):

    documents = load_and_split(file_path)

    if not documents:
        raise ValueError("No content found in the document.")

    embeddings = get_embedding_model()

    vector_store = FAISS.from_documents(
        documents,
        embeddings
    )

    VECTOR_DB_PATH.mkdir(
        parents=True,
        exist_ok=True
    )

    vector_store.save_local(
        str(VECTOR_DB_PATH)
    )

    return vector_store