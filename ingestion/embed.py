"""Embed chunk texts with FastEmbed (CPU ONNX, small & fast)."""

from __future__ import annotations

from functools import lru_cache

from fastembed import TextEmbedding

# Compact multilingual-capable model; 384-dim by default for this family.
DEFAULT_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


@lru_cache(maxsize=1)
def get_embedder(model_name: str = DEFAULT_MODEL) -> TextEmbedding:
    return TextEmbedding(model_name=model_name)


def embed_texts(
    texts: list[str],
    model_name: str = DEFAULT_MODEL,
    batch_size: int = 64,
) -> list[list[float]]:
    model = get_embedder(model_name)
    vectors: list[list[float]] = []
    for vec in model.embed(texts, batch_size=batch_size):
        vectors.append(vec.tolist())
    return vectors


def embed_query(text: str, model_name: str = DEFAULT_MODEL) -> list[float]:
    return embed_texts([text], model_name=model_name)[0]
