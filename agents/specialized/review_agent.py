from strands import Agent, tool
import sys
import os

# Add config directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'config'))

# Import model configuration
from model_config import model_config

REVIEW_AGENT_SYSTEM_PROMPT = """
You are ReviewAgent, a senior proposal reviewer ensuring tone, consistency, and quality across the entire document.

Your objectives:
1. Check for logical flow and consistency between sections.
2. Refine grammar, formatting, and tone for professional polish.
3. Ensure alignment with win themes and evaluation scoring criteria.
4. Highlight strengths and improvement areas.

Return feedback summaries or directly output refined content where applicable.
"""

@tool
def review_agent(query: str) -> str:
    """Performs final proposal review and refinement."""
    try:
        print("Routed to Review Agent")
        agent = model_config.create_agent(
            system_prompt=REVIEW_AGENT_SYSTEM_PROMPT,
            tools=[]
        )
        response = agent(f"Perform quality review on: {query}")
        return str(response)
    except Exception as e:
        return f"Error during proposal review: {str(e)}"
