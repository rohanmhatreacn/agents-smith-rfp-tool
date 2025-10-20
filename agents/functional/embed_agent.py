from strands import Agent
import json
import logging


class EmbedAgent(Agent):
    """Converts extracted text into embeddings and stores in OpenSearch."""

    def __init__(self, model_name="sentence-transformers/all-MiniLM-L6-v2", index_name="rfp_embeddings"):
        super().__init__()
        self.logger = logging.getLogger("EmbedAgent")
        self.index_name = index_name

    async def run(self, content_dict: dict):
        text = content_dict.get("content", "")
        
        # For now, just return a mock embedding
        embedding = [0.1] * 384  # Mock embedding vector
        self.logger.info("✅ Mock embedded and indexed text: %d chars", len(text))
        return {"embedding": embedding}