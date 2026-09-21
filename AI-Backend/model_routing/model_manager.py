from langchain_huggingface import (
    HuggingFaceEndpoint,
    ChatHuggingFace
)

from dotenv import load_dotenv

load_dotenv()


def get_model(model_name):

    model_name = str(model_name).strip()

    llm = HuggingFaceEndpoint(
        repo_id=model_name,
        temperature=0,
        max_new_tokens=2048
    )

    return ChatHuggingFace(
        llm=llm
    )