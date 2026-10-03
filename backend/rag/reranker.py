from models.reranker import RerankerError, get_reranker


async def rerank(query: str, documents: list[str], top_k: int = 6):
    return await get_reranker().rerank(query, documents, top_k=top_k)
