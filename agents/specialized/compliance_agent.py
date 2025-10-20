from strands import Agent, tool
import sys
import os

# Add config directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', 'config'))

# Import model configuration
from model_config import model_config

COMPLIANCE_AGENT_SYSTEM_PROMPT = """
You are ComplianceAgent, responsible for ensuring RFP responses meet all mandatory requirements.

Key tasks:
1. Check completeness and compliance against the RFP checklist.
2. Flag any missing sections, forms, or certifications.
3. Evaluate alignment with submission criteria (technical, financial, legal).
4. Summarize compliance gaps and provide remediation guidance.

Always present findings as a structured compliance table (Requirement / Status / Comments).
"""

@tool
def compliance_agent(query: str) -> str:
    """Performs RFP compliance review and generates gap analysis."""
    try:
        print("Routed to Compliance Agent")
        agent = model_config.create_agent(
            system_prompt=COMPLIANCE_AGENT_SYSTEM_PROMPT,
            tools=[]
        )
        response = agent(f"Perform compliance check for: {query}")
        return str(response)
    except Exception as e:
        return f"Error performing compliance validation: {str(e)}"
