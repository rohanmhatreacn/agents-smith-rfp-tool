from strands import Agent, tool
import sys
import os

# Add config directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'config'))

# Import model configuration
from model_config import model_config

FINANCIAL_AGENT_SYSTEM_PROMPT = """
You are FinancialAgent, a pricing and cost analysis expert focused on developing
cost breakdowns and pricing narratives for RFP proposals.

Your responsibilities:
1. Estimate costs for services, labor, and infrastructure.
2. Create simple Bill of Quantities (BoQs) or rate tables.
3. Justify pricing rationale (e.g., cost-efficiency, scalability).
4. Summarize commercial models and payment schedules.
5. Validate pricing alignment with client budgets and RFP constraints.

Always output clear tables and summaries that can be easily inserted into the proposal.
"""

@tool
def financial_agent(query: str) -> str:
    """Performs cost modeling and pricing narrative generation."""
    try:
        print("Routed to Financial Agent")
        agent = model_config.create_agent(
            system_prompt=FINANCIAL_AGENT_SYSTEM_PROMPT,
            tools=[]
        )
        response = agent(f"Generate financial model or pricing breakdown for: {query}")
        return str(response)
    except Exception as e:
        return f"Error generating financial analysis: {str(e)}"
