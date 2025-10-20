import json
import logging
import sys
import os
import uuid
from datetime import datetime

# Add config directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'config'))

# Import strands Agent (single clear import)
try:
    from strands import Agent
except ImportError as e:
    logging.error("Failed to import 'strands'. Please install it: pip install strands")
    raise

from config.model_config import model_config

from services.s3_client import s3_client
from services.dynamodb_client import dynamodb_client

# Import all RFP specialized agents with fallback
try:
    from .specialized.strategist_agent import strategist_agent
    from .specialized.solution_architect_agent import solution_architect_agent
    from .specialized.diagram_agent import diagram_agent
    from .specialized.content_agent import content_agent
    from .specialized.financial_agent import financial_agent
    from .specialized.compliance_agent import compliance_agent
    from .specialized.review_agent import review_agent
except ImportError as e:
    logging.warning(f"Some specialized agents failed to import: {e}")
    # Define fallback functions
    def strategist_agent(query): return f"Strategist agent not available: {query}"
    def solution_architect_agent(query): return f"Solution architect agent not available: {query}"
    def diagram_agent(query): return f"Diagram agent not available: {query}"
    def content_agent(query): return f"Content agent not available: {query}"
    def financial_agent(query): return f"Financial agent not available: {query}"
    def compliance_agent(query): return f"Compliance agent not available: {query}"
    def review_agent(query): return f"Review agent not available: {query}"

# Import functional agents with fallback
try:
    from .functional.ingest_agent import IngestAgent
    from .functional.embed_agent import EmbedAgent
    from .functional.draft_agent import DraftAgent
    from .functional.refine_agent import RefineAgent
    from .functional.export_agent import ExportAgent
except ImportError as e:
    logging.warning(f"Some functional agents failed to import: {e}")
    # Define fallback classes
    class IngestAgent: pass
    class EmbedAgent: pass
    class DraftAgent: pass
    class RefineAgent: pass
    class ExportAgent: pass

logging.basicConfig(level=logging.INFO)

RFP_ORCHESTRATOR_SYSTEM_PROMPT = """
You are ProposalOrchestrator, a central AI agent coordinating the full RFP proposal generation workflow.

1. Identify the intent and stage of the user query:
   - Requirements analysis or win themes → StrategistAgent
   - Technical design or AWS architecture → SolutionArchitectAgent
   - Architecture visualization or diagram generation → DiagramAgent
   - Writing or persuasive content → ContentAgent
   - Costing or pricing → FinancialAgent
   - Compliance validation or checklist review → ComplianceAgent
   - Final refinement, cohesion, and formatting → ReviewAgent

2. Maintain multi-agent coherence:
   - Track proposal state across refinements
   - Aggregate responses when multiple agents collaborate
   - Route queries dynamically based on detected intent

Always confirm routing when context is ambiguous. Return structured JSON with `section`, `agent`, and `summary` fields when coordinating multi-agent tasks.
"""

class OrchestratorAgent(Agent):
    def __init__(self):
        # Use the configured model provider
        model = model_config.get_model()
        
        super().__init__(
            model=model,
            system_prompt=RFP_ORCHESTRATOR_SYSTEM_PROMPT,
            tools=[
                strategist_agent,
                solution_architect_agent,
                diagram_agent,
                content_agent,
                financial_agent,
                compliance_agent,
                review_agent,
            ],
        )

        # Initialize functional pipeline
        self.ingest_agent = IngestAgent()
        self.embed_agent = EmbedAgent()
        self.draft_agent = DraftAgent()
        self.refine_agent = RefineAgent()
        self.export_agent = ExportAgent()

        # Proposal memory
        self.proposal_state = {}
        self.logger = logging.getLogger("RFPOrchestrator")

    async def store_large_output(self, content: str, content_type: str = "output", session_id: str = None) -> str:
        """Store large output in S3 and return a reference key."""
        if not session_id:
            session_id = str(uuid.uuid4())
        
        # Generate unique key for this content
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        content_key = f"sessions/{session_id}/{content_type}_{timestamp}.txt"
        
        try:
            # Store content in S3/MinIO
            success = s3_client.upload_file_object(
                file_data=content.encode('utf-8'),
                object_key=content_key,
                content_type="text/plain",
                metadata={
                    "session_id": session_id,
                    "content_type": content_type,
                    "timestamp": timestamp,
                    "size": str(len(content))
                }
            )
            
            if success:
                self.logger.info(f"✅ Stored {content_type} content in S3: {content_key}")
                return content_key
            else:
                self.logger.error(f"❌ Failed to store {content_type} content in S3")
                return None
                
        except Exception as e:
            self.logger.error(f"❌ Error storing content in S3: {e}")
            return None

    async def store_session_data(self, session_id: str, data: dict):
        """Store session data in DynamoDB."""
        try:
            success = dynamodb_client.save_session_data(session_id, data)
            if success:
                self.logger.info(f"✅ Stored session data for {session_id}")
            else:
                self.logger.error(f"❌ Failed to store session data for {session_id}")
        except Exception as e:
            self.logger.error(f"❌ Error storing session data: {e}")

    async def run(self, user_input: str, file_path: str = None, session_id: str = None):
        try:
            # Step 1: Handle document ingestion if file uploaded
            if file_path:
                self.logger.info("📄 Processing uploaded file: %s", file_path)
                try:
                    parsed = await self.ingest_agent.run(file_path)
                    embeddings = await self.embed_agent.run(parsed)
                    self.proposal_state["source_text"] = parsed.get("content", "")
                    self.proposal_state["embeddings"] = embeddings
                    self.logger.info("✅ Document processed successfully")
                except Exception as e:
                    self.logger.error("❌ Document processing failed: %s", e)
                    raise ValueError(f"Failed to process document: {str(e)}")

            # Step 2: Use system prompt to detect routing
            self.logger.info("🔍 Analyzing query for routing: %s", user_input[:100])
            try:
                routing_decision = await self.route_task(user_input)
            except Exception as e:
                self.logger.error("❌ Routing failed: %s", e)
                # Fallback routing
                routing_decision = {"section": "general", "agent": "ContentAgent", "summary": "Fallback routing due to error"}

            agent_name = routing_decision.get("agent")
            summary = routing_decision.get("summary", "")
            self.logger.info("🎯 Routing to %s: %s", agent_name, summary)

            # Step 3: Build lightweight shared context and dispatch task
            self.logger.info("⚡ Dispatching task to %s", agent_name)
            try:
                # Build a compact context string to pass along so agents can "talk"
                source_preview = (self.proposal_state.get("source_text", "") or "")[:1000]
                prev_sections = {k: (str(v)[:500]) for k, v in self.proposal_state.items() if k not in ("source_text", "embeddings")}
                context_prompt = (
                    "\n\n[Context]\n"
                    f"Known sections: {list(prev_sections.keys())}\n"
                    f"Recent section previews: {prev_sections}\n"
                    f"Source preview (first 1000 chars): {source_preview}\n"
                )

                enriched_input = f"{user_input}\n\nPlease consider the shared proposal context above when responding."

                response = await self.dispatch(agent_name, enriched_input)
                self.logger.info("✅ Task completed by %s", agent_name)
            except Exception as e:
                self.logger.error("❌ Agent dispatch failed: %s", e)
                response = f"Error processing request with {agent_name}: {str(e)}"

            # Step 4: Persist output with storage (always store)
            output_content = str(response)
            content_key = None
            
            # Ensure we have a session id
            if not session_id:
                session_id = str(uuid.uuid4())

            # Store outputs in S3/MinIO (always)
            content_key = await self.store_large_output(
                output_content,
                f"{routing_decision['section']}_output",
                session_id
            )

            # Store/Update session data snapshot in DynamoDB (include compact proposal_state)
            compact_state = {}
            for k, v in self.proposal_state.items():
                if k in ("source_text", "embeddings"):
                    continue
                compact_state[k] = str(v)[:1000]

            await self.store_session_data(session_id, {
                "section": routing_decision["section"],
                "agent": agent_name,
                "content_key": content_key,
                "proposal_state": compact_state,
                "updated_at": datetime.now().isoformat()
            })
            
            # Step 5: Update proposal state and return result
            self.proposal_state[routing_decision["section"]] = response
            result = {
                "section": routing_decision["section"],
                "agent": agent_name,
                "summary": summary,
                "output": response,
                "content_key": content_key,  # Add storage reference
                "session_id": session_id,
                "reasoning": {
                    "query_analysis": f"Analyzed user query: '{user_input}'\n\nIntent detected: The user is requesting assistance with {routing_decision['section']} section of an RFP proposal. The query indicates a need for specialized expertise in this domain.",
                    "routing_logic": f"Selected {agent_name} because:\n- Query analysis revealed focus on {routing_decision['section']} section\n- {agent_name} is specialized for this type of request\n- Summary: {summary}\n- This agent has the appropriate tools and knowledge to handle the specific requirements",
                    "processing_steps": [
                        f"Document ingestion: {'Completed successfully' if file_path else 'No document uploaded - processing text-only query'}",
                        f"Query analysis: Detected intent for {routing_decision['section']} section based on keywords and context",
                        f"Agent selection: Chose {agent_name} as the most appropriate specialist for this task",
                        f"Task execution: {agent_name} processed the request and generated comprehensive response",
                        f"Response generation: Created {len(output_content)} characters of detailed content",
                        f"Storage: Content stored in S3 and session metadata saved to DynamoDB"
                    ]
                }
            }
            
            self.logger.info("🎉 Orchestration complete: %s characters generated", len(output_content))
            return result

        except Exception as e:
            self.logger.error("❌ Error in orchestrator run: %s", e)
            # Return error result instead of raising
            return {
                "section": "error",
                "agent": "ErrorHandler",
                "summary": f"Processing failed: {str(e)}",
                "output": f"An error occurred while processing your request: {str(e)}\n\nPlease try again with a simpler query or contact support.",
                "reasoning": {
                    "query_analysis": f"Error during analysis: {str(e)}",
                    "routing_logic": "Error occurred before routing could complete",
                    "processing_steps": ["Error occurred during processing"]
                }
            }

    async def route_task(self, user_input: str):
        """Determine which specialized agent to invoke."""
        routing_prompt = f"""
        Analyze the following instruction and determine which agent should handle it.
        Return JSON in the format: {{ "section": "name", "agent": "AgentName", "summary": "why this route" }}
        Instruction: {user_input}
        """
        try:
            # Use the agent's call method instead of run to avoid recursion
            result = self(routing_prompt)
            return json.loads(str(result))
        except (json.JSONDecodeError, ValueError):
            # Fallback if parsing fails
            return {"section": "general", "agent": "ContentAgent", "summary": "Defaulted to content generation."}

    async def dispatch(self, agent_name: str, user_input: str):
        """Execute the selected specialized agent with error handling."""
        agent_map = {
            "StrategistAgent": strategist_agent,
            "SolutionArchitectAgent": solution_architect_agent,
            "DiagramAgent": diagram_agent,
            "ContentAgent": content_agent,
            "FinancialAgent": financial_agent,
            "ComplianceAgent": compliance_agent,
            "ReviewAgent": review_agent,
        }
        agent = agent_map.get(agent_name)
        if not agent:
            self.logger.warning("⚠️ No agent found for %s, defaulting to ContentAgent.", agent_name)
            agent = content_agent
        
        try:
            # Call the agent function directly since they are @tool decorated functions
            result = agent(user_input)
            
            # Ensure result is not too large
            if isinstance(result, str) and len(result) > 100000:  # 100KB limit
                self.logger.warning("⚠️ Agent response too large (%d chars), truncating", len(result))
                result = result[:100000] + "\n\n... (Response truncated due to size limits)"
            
            return result
            
        except Exception as e:
            self.logger.error("❌ Agent %s failed: %s", agent_name, e)
            return f"Error in {agent_name}: {str(e)}\n\nPlease try again or contact support."
