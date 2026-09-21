from pathlib import Path

from langchain_community.vectorstores import FAISS

from rag.embeddings import get_embedding_model


VECTOR_DB_PATH = Path("vector_db/faiss_index")


def get_vector_store():
    """
    Load the persisted FAISS vector store.
    """

    if not (VECTOR_DB_PATH / "index.faiss").exists():
        return None

    embeddings = get_embedding_model()

    return FAISS.load_local(
        str(VECTOR_DB_PATH),
        embeddings,
        allow_dangerous_deserialization=True
    )


def retrieve_context(query: str, k: int = 4):
    """
    Retrieve the most relevant document chunks for a query.
    """

    vector_store = get_vector_store()

    if vector_store is None:
        return []

    return vector_store.similarity_search(
        query,
        k=k
    )