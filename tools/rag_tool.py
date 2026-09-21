from langchain_core.tools import tool

from rag.retriever import retrieve_context


@tool
def search_knowledge_base(query: str) -> str:
    """
    Search the local knowledge base for information relevant to the user's query.
    """

    try:
        documents = retrieve_context(query, k=4)

        if not documents:
            return "No relevant information found in the knowledge base."

        results = []

        for document in documents:
            source = document.metadata.get("source", "Unknown")

            results.append(
                f"Source: {source}\n"
                f"{document.page_content}"
            )

        return "\n\n---\n\n".join(results)

    except Exception as e:
        return f"Knowledge base search failed: {e}"