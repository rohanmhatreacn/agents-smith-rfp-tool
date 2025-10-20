from strands import Agent, tool
import sys
import os

# Add config directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'config'))

# Import model configuration
from model_config import model_config

STRATEGIST_SYSTEM_PROMPT = """
You are StrategistAgent, an expert in analyzing RFPs to extract mandatory requirements,
identify win themes, and structure the proposal narrative.

Capabilities:
1. Parse key sections (scope, evaluation criteria, deliverables)
2. Identify mandatory and differentiating requirements
3. Recommend win themes and narrative structure
4. Summarize client priorities and competitive positioning

Respond concisely and provide structured output (JSON if possible) for downstream agents.
"""

@tool
def strategist_agent(query: str) -> str:
    """Analyze RFP content and outline proposal structure."""
    try:
        agent = model_config.create_agent(
            system_prompt=STRATEGIST_SYSTEM_PROMPT,
            tools=[]
        )
        return str(agent(f"Analyze this RFP request: {query}"))
    except Exception as e:
        return f"Error processing strategy query: {str(e)}"
