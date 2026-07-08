import uuid
from datetime import datetime, timezone
from functools import lru_cache
from typing import cast

import chromadb
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from reviewbot.config import settings


class _GoogleEmbeddingFunction(EmbeddingFunction):
    """Uses Google's hosted embedding API instead of chromadb's default local
    ONNX model, which requires a slow one-time ~80MB download on first use."""

    def __init__(self) -> None:
        self._embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")

    def __call__(self, input: Documents) -> Embeddings:
        return cast(Embeddings, self._embeddings.embed_documents(list(input)))


@lru_cache(maxsize=1)
def _get_collection():
    client = chromadb.PersistentClient(path=str(settings.chroma_dir))
    return client.get_or_create_collection(
        "semantic_facts", embedding_function=_GoogleEmbeddingFunction()
    )


def add_fact(chat_id: int, fact_text: str) -> None:
    collection = _get_collection()
    collection.add(
        documents=[fact_text],
        metadatas=[{"chat_id": chat_id, "created_at": datetime.now(timezone.utc).isoformat()}],
        ids=[str(uuid.uuid4())],
    )


def clear_facts(chat_id: int) -> None:
    collection = _get_collection()
    collection.delete(where={"chat_id": chat_id})


def query_facts(chat_id: int, query_text: str, n_results: int = 5) -> list[str]:
    collection = _get_collection()
    if collection.count() == 0 or not query_text.strip():
        return []

    result = collection.query(
        query_texts=[query_text],
        n_results=n_results,
        where={"chat_id": chat_id},
    )
    documents = result.get("documents") or [[]]
    return documents[0]
