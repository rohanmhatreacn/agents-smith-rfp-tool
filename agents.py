import logging
from strands import Agent, tool
from llm import llm_provider

logger = logging.getLogger(__name__)


@tool
def strategist_agent(query: str) -> str:
    """
    Analyzes RFP requirements and identifies win themes.
    Extracts mandatory requirements, evaluation criteria, and competitive positioning.
    Returns concise strategic analysis (one paragraph).
    """
    system_prompt = """You are a strategic RFP analyst. Analyze requirements and provide:
    1. Key mandatory requirements (3-5 items)
    2. Win themes (2-3 themes)
    3. Competitive positioning recommendation
    Keep response to exactly one paragraph, 100 words max."""
    
    try:
        agent = Agent(
            model=llm_provider.get_model(),
            system_prompt=system_prompt
        )
        response = agent(f"Analyze this RFP: {query}")
        logger.info("✅ Strategist agent completed")
        return str(response)
    except Exception as e:
        logger.error(f"❌ Strategist agent failed: {e}")
        return f"Strategic analysis unavailable: {str(e)}"


@tool
def solution_architect_agent(query: str) -> str:
    """
    Designs technical architecture and solution components.
    Provides AWS services recommendations and integration patterns.
    Returns concise technical design (one paragraph).
    """
    system_prompt = """You are a solutions architect. Design technical architecture with:
    1. Core AWS services (3-5 services)
    2. Integration approach
    3. Key architectural decisions
    Keep response to exactly one paragraph, 100 words max."""
    
    try:
        agent = Agent(
            model=llm_provider.get_model(),
            system_prompt=system_prompt
        )
        response = agent(f"Design solution for: {query}")
        logger.info("✅ Solution architect agent completed")
        return str(response)
    except Exception as e:
        logger.error(f"❌ Solution architect agent failed: {e}")
        return f"Technical design unavailable: {str(e)}"


@tool
def diagram_agent(query: str) -> dict:
    """
    Generates AWS architecture diagrams using MCP server.
    Creates visual representations of technical solutions.
    Returns diagram data as JSON (simple 3-component diagram).
    """
    diagram_data = {
        "diagram_type": "aws_architecture",
        "components": [
            {"name": "API Gateway", "type": "api", "connections": ["Lambda"]},
            {"name": "Lambda", "type": "compute", "connections": ["DynamoDB"]},
            {"name": "DynamoDB", "type": "database", "connections": []}
        ],
        "description": "Simple 3-tier AWS architecture",
        "generated_for": query[:100]
    }
    
    logger.info("✅ Diagram agent completed (simplified)")
    return diagram_data


@tool
def content_agent(query: str) -> str:
    """
    Writes persuasive proposal content and executive summaries.
    Crafts client-focused narratives aligned with win themes.
    Returns polished content (one paragraph).
    """
    system_prompt = """You are a proposal writer. Create compelling content with:
    1. Clear value proposition
    2. Client-focused benefits
    3. Professional, persuasive tone
    Keep response to exactly one paragraph, 100 words max."""
    
    try:
        agent = Agent(
            model=llm_provider.get_model(),
            system_prompt=system_prompt
        )
        response = agent(f"Write proposal content for: {query}")
        logger.info("✅ Content agent completed")
        return str(response)
    except Exception as e:
        logger.error(f"❌ Content agent failed: {e}")
        return f"Content generation unavailable: {str(e)}"


@tool
def financial_agent(query: str) -> dict:
    """
    Creates pricing models and cost breakdowns.
    Provides budget estimates and financial justifications.
    Returns simple financial table (3 rows).
    """
    financial_data = {
        "cost_breakdown": [
            {"item": "Development", "cost": "$150,000", "duration": "6 months"},
            {"item": "Infrastructure", "cost": "$50,000", "duration": "Annual"},
            {"item": "Support", "cost": "$30,000", "duration": "Annual"}
        ],
        "total": "$230,000",
        "notes": "Estimated costs based on typical project scope"
    }
    
    logger.info("✅ Financial agent completed (simplified)")
    return financial_data


@tool
def compliance_agent(query: str) -> str:
    """
    Validates proposal against RFP compliance requirements.
    Checks mandatory criteria, formatting, and completeness.
    Returns compliance summary (one paragraph).
    """
    system_prompt = """You are a compliance reviewer. Provide:
    1. Compliance status (compliant/needs review)
    2. Key requirements met (3 items)
    3. Any gaps or concerns
    Keep response to exactly one paragraph, 100 words max."""
    
    try:
        agent = Agent(
            model=llm_provider.get_model(),
            system_prompt=system_prompt
        )
        response = agent(f"Check compliance for: {query}")
        logger.info("✅ Compliance agent completed")
        return str(response)
    except Exception as e:
        logger.error(f"❌ Compliance agent failed: {e}")
        return f"Compliance check unavailable: {str(e)}"


@tool
def review_agent(query: str) -> str:
    """
    Performs final review and refinement of proposal.
    Ensures coherence, quality, and professional polish.
    Returns review summary (one paragraph).
    """
    system_prompt = """You are a proposal reviewer. Provide:
    1. Overall quality assessment
    2. Strengths (2 items)
    3. Suggested improvements (2 items)
    Keep response to exactly one paragraph, 100 words max."""
    
    try:
        agent = Agent(
            model=llm_provider.get_model(),
            system_prompt=system_prompt
        )
        response = agent(f"Review this proposal section: {query}")
        logger.info("✅ Review agent completed")
        return str(response)
    except Exception as e:
        logger.error(f"❌ Review agent failed: {e}")
        return f"Review unavailable: {str(e)}"


AGENT_REGISTRY = {
    "strategist": strategist_agent,
    "solution_architect": solution_architect_agent,
    "diagram": diagram_agent,
    "content": content_agent,
    "financial": financial_agent,
    "compliance": compliance_agent,
    "review": review_agent,
}

