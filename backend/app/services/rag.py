from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams
from app.core.config import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()


class RAGService:
    def __init__(self):
        self.client = None

    def _get_client(self) -> QdrantClient:
        if self.client is None:
            self.client = QdrantClient(
                url=settings.QDRANT_URL,
                api_key=settings.QDRANT_API_KEY if settings.QDRANT_API_KEY else None,
            )
        return self.client

    def init_collection(self, collection_name: str = "knowledge_base"):
        try:
            qdrant = self._get_client()
            collection_info = qdrant.get_collection(collection_name)
            logger.info(
                f"Collection {collection_name} already exists with size {collection_info.config.params.vectors.size}"
            )
        except Exception:
            qdrant.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=1536, distance=Distance.COSINE),
            )
            logger.info(f"Created collection {collection_name} with size 1536")


rag_service = RAGService()

