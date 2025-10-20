from strands import Agent
import logging


class RefineAgent(Agent):
    """Refines targeted proposal sections based on user input."""

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger("RefineAgent")

    async def run(self, section_text: str, user_feedback: str):
        prompt = (
            f"Refine the following section using this feedback:\n"
            f"Feedback: {user_feedback}\n"
            f"Section: {section_text}"
        )
        self.logger.info("📝 Refining section with user input.")
        # Here you'd integrate the same Ollama or AgentCore logic
        return {"refined_section": f"Refined version of: {section_text[:100]}..."}