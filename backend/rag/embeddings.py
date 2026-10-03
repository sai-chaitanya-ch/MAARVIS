from models.embeddings import EmbeddingError, get_embeddings


async def embed_texts(texts: list[str]) -> list[list[float]]:
    return await get_embeddings().embed(texts)
