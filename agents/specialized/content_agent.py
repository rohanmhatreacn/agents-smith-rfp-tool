import os

# Prefer real strands; fall back to local shims for lint/runtime resilience
try:
    from strands import Agent, tool
except ImportError:
    def tool(fn):
        return fn
    class Agent:
        def __init__(self, model=None, system_prompt="", tools=None):
            self.model = model
            self.system_prompt = system_prompt
            self.tools = tools or []
        def __call__(self, prompt: str):
            return f"[Mock Agent response] {prompt}"

# Prefer real Ollama model; fall back to a minimal shim
try:
    from strands.models.ollama import OllamaModel
except ImportError:
    class OllamaModel:
        def __init__(self, host="http://localhost:11434", model_id="llama3.2:latest", temperature=0.3):
            self.host = host
            self.model_id = model_id
            self.temperature = temperature

# Import model configuration via absolute path
from config.model_config import model_config

CONTENT_AGENT_SYSTEM_PROMPT = """
You are ContentAgent, a persuasive proposal writer specializing in crafting high-quality,
client-focused narratives for RFP responses.

Your tasks include:
1. Drafting executive summaries and proposal sections.
2. Adapting tone and style for technical, managerial, or persuasive contexts.
3. Ensuring coherence with overall solution and win themes.
4. Maintaining clear, professional, and compelling structure.

Focus on clarity, storytelling, and alignment with evaluation criteria.
When refining text, show improved and original versions if helpful.
"""

@tool
def content_agent(query: str) -> str:
    """Generates or refines proposal content."""
    # Try local Ollama first (requested behavior)
    try:
        print("Routed to Content Agent (Ollama-first)")
        ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        ollama_model_id = os.getenv("MODEL_ID", "qwen3:4b")
        temperature = float(os.getenv("TEMPERATURE", "0.3"))

        ollama_agent = Agent(
            model=OllamaModel(
                host=ollama_host,
                model_id=ollama_model_id,
                temperature=temperature,
            ),
            system_prompt=CONTENT_AGENT_SYSTEM_PROMPT,
            tools=[],
        )
        response = ollama_agent(f"Draft or refine proposal content for: {query}")
        return str(response)
    except Exception as ollama_error:
        # Fall back to configured provider (e.g., Bedrock) only if Ollama fails
        try:
            agent = model_config.create_agent(
                system_prompt=CONTENT_AGENT_SYSTEM_PROMPT,
                tools=[]
            )
            response = agent(f"Draft or refine proposal content for: {query}")
            return str(response)
        except Exception as configured_error:
            return (
                f"Error generating via Ollama: {ollama_error} | "
                f"Configured provider failed: {configured_error}"
            )
