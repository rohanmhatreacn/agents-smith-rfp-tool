from strands import Agent, tool
import sys
import os

# Add config directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'config'))

# Import model configuration
from model_config import model_config

SOLUTION_ARCHITECT_SYSTEM_PROMPT = """
You are SolutionArchitectAgent, a senior technical architect specializing in designing cloud-native,
secure, and scalable solutions for RFP responses.

Your responsibilities:
1. Review RFP requirements and propose an optimal architecture (AWS preferred).
2. Define components, data flow, and integrations.
3. Recommend services (compute, storage, AI, networking) with justifications.
4. Prepare a system architecture narrative for the proposal.
5. Collaborate with DiagramAgent when visuals are requested.

Always ensure architecture aligns with client requirements and compliance constraints.
Output should include both summary text and structured component listings if possible.
"""

@tool
def solution_architect_agent(query: str) -> str:
    """Designs the technical solution and architecture narrative for RFPs."""
    try:
        print("Routed to Solution Architect Agent")
        agent = model_config.create_agent(
            system_prompt=SOLUTION_ARCHITECT_SYSTEM_PROMPT,
            tools=[]
        )
        response = agent(f"Design an optimal architecture based on: {query}")
        return str(response)
    except Exception as e:
        return f"Error generating solution architecture: {str(e)}"
