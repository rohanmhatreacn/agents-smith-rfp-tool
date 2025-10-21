import logging
import json
import os
from typing import Any
from strands import Agent
from llm import llm_provider
from agents import AGENT_REGISTRY, _call_openai
from document import document_processor
from storage import storage
from export import exporter
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)


class Orchestrator:
    """
    Intelligent routing system that analyzes user queries and directs them
    to the appropriate specialized agent. Coordinates multi-agent workflows
    and aggregates results into final proposal outputs.
    """
    
    def __init__(self):
        """
        Initializes orchestrator with routing logic and agent registry.
        Sets up the main coordination agent for intelligent decision-making.
        """
        self.agents = AGENT_REGISTRY
        # Use direct OpenAI call if OpenAI is the current provider
        if llm_provider.current_provider == "openai":
            self.routing_agent = None  # Will use direct OpenAI calls
        else:
            self.routing_agent = Agent(
                model=llm_provider.get_model(),
                system_prompt=self._get_routing_prompt()
            )
        self.proposal_state = {}
    
    
    def _get_routing_prompt(self) -> str:
        """
        Returns the system prompt for the routing agent.
        Defines agent capabilities and routing logic.
        """
        return """You are an intelligent routing coordinator for RFP proposal generation.

Analyze user queries and route to the appropriate agent:

- strategist: Requirements analysis, win themes, competitive positioning
- solution_architect: Technical design, AWS architecture, system components
- diagram: Architecture visualization, technical diagrams
- content: Proposal writing, executive summaries, narrative content
- financial: Pricing, cost estimates, budget breakdowns
- compliance: Requirement validation, checklist review, gap analysis
- review: Final review, quality check, refinement

Respond with JSON only:
{
    "agent": "agent_name",
    "reasoning": "why this agent is appropriate",
    "context": "relevant context to pass to agent"
}

Be concise and decisive."""
    
    
    async def process(
        self, 
        user_input: str, 
        file_path: str | None = None,
        session_id: str | None = None
    ) -> dict[str, Any]:
        """
        Main processing pipeline that handles user input through the entire workflow:
        1. Document extraction (if file provided)
        2. Intelligent routing to appropriate agent
        3. Agent processing and response generation
        4. Storage of results
        5. Return structured output
        
        Returns dict with agent response, metadata, and session information.
        """
        try:
            if not session_id:
                session_id = str(uuid.uuid4())
            
            logger.info("🚀 Starting processing for session: %s", session_id)
            
            document_content = None
            if file_path:
                logger.info("📄 Extracting document: %s", file_path)
                doc_data = document_processor.extract(file_path)
                document_content = doc_data['text']
                self.proposal_state['document'] = doc_data
            
            enriched_input = user_input
            if document_content:
                enriched_input = f"{user_input}\n\nDocument Context:\n{document_content[:2000]}"
            
            logger.info("🎯 Routing query to appropriate agent")
            routing_decision = self._route_query(enriched_input)
            
            agent_name = routing_decision['agent']
            context = routing_decision.get('context', enriched_input)
            
            logger.info("🤖 Executing %s agent", agent_name)
            result = await self._execute_agent(agent_name, context)
            
            self.proposal_state[agent_name] = result
            
            output_key = f"{session_id}/{agent_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            storage.save_file(
                output_key,
                json.dumps(result, default=str).encode(),
                "application/json"
            )
            
            storage.save_session(session_id, {
                "agent": agent_name,
                "query": user_input,
                "output_key": output_key,
                "proposal_state": self.proposal_state,
            })
            
            response = {
                "session_id": session_id,
                "agent": agent_name,
                "reasoning": routing_decision['reasoning'],
                "result": result,
                "output_key": output_key,
                "timestamp": datetime.now().isoformat(),
            }
            
            logger.info("✅ Processing complete for session: %s", session_id)
            return response
            
        except Exception as e:
            logger.error("❌ Processing failed: %s", e)
            raise
    
    
    def _route_query(self, query: str) -> dict:
        """
        Uses the routing agent to determine which specialist should handle the query.
        Returns routing decision with agent name and reasoning.
        """
        try:
            routing_query = f"Route this query to the appropriate agent: {query[:500]}"
            
            # Use direct OpenAI call if OpenAI is the current provider
            if llm_provider.current_provider == "openai":
                response = _call_openai(self._get_routing_prompt(), routing_query)
            else:
                response = self.routing_agent(routing_query)
            
            response_str = str(response).strip()
            if response_str.startswith("```"):
                response_str = response_str.split("```")[1]
                if response_str.startswith("json"):
                    response_str = response_str[4:]
            
            decision = json.loads(response_str)
            
            if decision['agent'] not in self.agents:
                logger.warning("⚠️ Unknown agent '%s', defaulting to content", decision['agent'])
                decision['agent'] = 'content'
            
            return decision
            
        except Exception as e:
            logger.warning("⚠️ Routing failed: %s, defaulting to content agent", e)
            return {
                "agent": "content",
                "reasoning": "Fallback routing due to parsing error",
                "context": query
            }
    
    
    async def _execute_agent(self, agent_name: str, context: str) -> Any:
        """
        Executes the specified agent with the given context.
        Returns the agent's response (string, dict, or list).
        """
        agent_func = self.agents[agent_name]
        return agent_func(context)
    
    
    async def generate_full_proposal(self, session_id: str, output_format: str = "docx") -> str:
        """
        Generates a complete proposal document from all accumulated agent outputs.
        Combines strategist, architect, content, financial, and compliance sections.
        Returns path to the generated file (DOCX or PDF).
        """
        try:
            logger.info("📝 Generating full proposal for session: %s", session_id)
            
            session_data = storage.load_session(session_id)
            if not session_data:
                raise ValueError(f"Session not found: {session_id}")
            
            proposal_content = session_data.get('proposal_state', {})
            
            if 'diagram' in proposal_content:
                os.makedirs(".data/diagrams", exist_ok=True)
                diagram_path = f".data/diagrams/{session_id}_diagram.png"
                exporter.save_diagram_image(
                    proposal_content['diagram'],
                    diagram_path
                )
                proposal_content['diagram_image'] = diagram_path
            
            os.makedirs(".data/proposals", exist_ok=True)
            output_path = f".data/proposals/{session_id}_proposal.{output_format}"
            
            if output_format == "docx":
                exporter.export_docx(proposal_content, output_path)
            elif output_format == "pdf":
                exporter.export_pdf(proposal_content, output_path)
            else:
                raise ValueError(f"Unsupported format: {output_format}")
            
            logger.info("✅ Proposal generated: %s", output_path)
            return output_path
            
        except Exception as e:
            logger.error("❌ Proposal generation failed: %s", e)
            raise


orchestrator = Orchestrator()

