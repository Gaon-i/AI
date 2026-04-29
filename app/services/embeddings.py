import os

from app.core.config import get_settings
from openai import OpenAI

settings = get_settings()
client = OpenAI(api_key=settings.openai_api_key)


def create_query_embedding(text: str) -> list[float]:
    settings = get_settings()
    response = client.embeddings.create(
        model=settings.openai_embedding_model,
        input=text
    )
    return response.data[0].embedding
