from langchain_huggingface import HuggingFaceEndpointEmbeddings


def get_embedding_model():
    """
    Return the Hugging Face embedding model used for RAG.
    """

    return HuggingFaceEndpointEmbeddings(
        model="BAAI/bge-base-en-v1.5"
    )
