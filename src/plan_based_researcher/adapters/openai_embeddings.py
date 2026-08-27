from langchain_openai import OpenAIEmbeddings
from plan_based_researcher.ports.embeddings import EmbeddingPort  # structural only


class OpenAIEmbeddingAdapter:
    def __init__(self, api_key: str | None = None) -> None:
        kwargs = {"model": "text-embedding-3-small"}
        if api_key is not None:
            kwargs["api_key"] = api_key
        self._embeddings = OpenAIEmbeddings(**kwargs)

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return await self._embeddings.aembed_documents(texts)

    async def embed_query(self, text: str) -> list[float]:
        return await self._embeddings.aembed_query(text)
