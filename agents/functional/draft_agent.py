"""Draft agent that prefers local Ollama (qwen3:4b) with cloud fallback."""

# Prefer real strands Agent; fall back to local shim for runtime resilience
try:
    from strands import Agent
except ImportError:  # pragma: no cover - fallback for environments without strands
    class Agent:  # minimal base to keep app runnable
        def __init__(self):
            pass

import aiohttp
import os
import logging


class DraftAgent(Agent):
    """Generates base RFP draft using local Ollama (qwen3:4b) or AgentCore cloud fallback."""

    def __init__(self, local_model="qwen3:4b"):
        super().__init__()
        self.logger = logging.getLogger("DraftAgent")
        # Resolve model and host from environment with sensible defaults
        self.local_model = os.getenv("MODEL_ID", local_model)
        self.ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        self.cloud_url = os.getenv("AGENTCORE_API")

    async def run(self, context: dict):
        prompt = context.get("prompt", "Generate proposal draft.")
        try:
            # Try local Ollama
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.ollama_host}/api/generate",
                    json={
                        "model": self.local_model,
                        "prompt": prompt,
                        "options": {
                            "temperature": float(os.getenv("TEMPERATURE", "0.3"))
                        }
                    },
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as resp:
                    if resp.status == 200:
                        result = await resp.json()
                        response_text = result.get("response", "")
                        self.logger.info("✅ Generated proposal via Ollama.")
                        return {"draft": response_text}

                # Fallback to AgentCore
                if self.cloud_url:
                    async with session.post(self.cloud_url, json={"prompt": prompt}) as cloud_resp:
                        result = await cloud_resp.json()
                        response_text = result.get("output", "")
                        self.logger.info("☁️ Used AgentCore fallback.")
                        return {"draft": response_text}

        except Exception as e:
            self.logger.error("❌ Draft generation failed: %s", e)
            # Return a mock response for now
            return {"draft": f"Mock draft response for: {prompt[:100]}..."}