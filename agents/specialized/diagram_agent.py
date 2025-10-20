"""
DiagramAgent – generates architecture diagrams for RFP proposals.
Supports both local (Ollama MCP) and cloud (AWS Bedrock AgentCore) modes.
"""
import os
from strands import Agent, tool
import sys

# Add config directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'config'))

# Import model configuration
from model_config import model_config

MODE = os.getenv("DIAGRAM_AGENT_MODE", "local")  # 'local' or 'cloud'

SYSTEM_PROMPT = """
You are DiagramAgent, an AWS Solutions Architect specializing in creating architecture diagrams
for RFP proposals. Provide detailed text descriptions of diagrams that can be converted to visual representations.
"""

def get_model():
    """Return the appropriate model instance based on the DIAGRAM_AGENT_MODE environment variable."""
    # For now, return None since BedrockModel is not available
    return None

def get_tools():
    """Return list of tools for diagram generation based on operation mode."""
    # For now, return empty list since MCP tools are not available
    return []

@tool
def diagram_agent(query: str) -> str:
    """Generate AWS or system diagrams for RFP architecture proposals."""
    try:
        agent = model_config.create_agent(
            system_prompt=SYSTEM_PROMPT,
            tools=[]
        )
        response = agent(query)
        return str(response)
    except Exception as e:
        return f"Error generating diagram: {str(e)}"
