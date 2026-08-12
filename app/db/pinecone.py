from pinecone import Pinecone, ServerlessSpec

from lib.config import config


class VectorService:

    def __init__(self, api_key, index_name):
        self.pc = Pinecone(
            api_key=api_key
        )

        self.index_name = index_name

        self._ensure_index()

        self.index = self.pc.Index(self.index_name)

    def _ensure_index(self):
        if not self.pc.has_index(self.index_name):
            self.pc.create_index(
            name=self.index_name,
            dimension=1536,
            metric="cosine",
            spec=ServerlessSpec(
                cloud="aws",
                region="us-east-1"
                )
            )
            tags={
                    "environment": config.app.environment
            }

    

vector_service = VectorService(config.pinecone.api_key, config.pinecone.profile_index)