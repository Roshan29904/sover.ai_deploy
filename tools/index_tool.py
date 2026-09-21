from pathlib import Path

from langchain_core.tools import tool

from rag.ingestion import load_and_split
from rag.embeddings import get_embedding_model
from rag.retriever import get_vector_store
from langchain_community.vectorstores import FAISS


VECTOR_DB_PATH = Path("vector_db/faiss_index")


@tool
def index_document(file_path: str) -> str:
    """
    Add a local document to the sovereign AI knowledge base.

    Supported formats include TXT, PDF, DOCX, PPTX and XLSX.
    """

    try:
        path = Path(file_path)

        if not path.exists():
            return f"File not found: {file_path}"

        chunks = load_and_split(str(path))

        if not chunks:
            return "No readable content found in the document."

        embeddings = get_embedding_model()

        vector_store = get_vector_store()

        if vector_store is None:

            VECTOR_DB_PATH.mkdir(
                parents=True,
                exist_ok=True
            )

            vector_store = FAISS.from_documents(
                chunks,
                embeddings
            )

        else:

            vector_store.add_documents(chunks)

        vector_store.save_local(
            str(VECTOR_DB_PATH)
        )

        return (
            f"Document indexed successfully.\n"
            f"File: {path.name}\n"
            f"Chunks added: {len(chunks)}"
        )

    except Exception as e:
        return f"Unable to index document: {e}"