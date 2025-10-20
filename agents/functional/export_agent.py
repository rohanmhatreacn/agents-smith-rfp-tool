from strands import Agent
import os
import logging


class ExportAgent(Agent):
    """Compiles final proposal into DOCX and PDF formats."""

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger("ExportAgent")

    async def run(self, proposal_data: dict, output_dir="outputs"):
        os.makedirs(output_dir, exist_ok=True)

        # For now, just create a simple text file
        txt_path = os.path.join(output_dir, "proposal.txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(f"Proposal: {proposal_data.get('title', 'Proposal')}\n\n")
            for key, value in proposal_data.items():
                f.write(f"{key}: {value}\n\n")

        self.logger.info("✅ Exported proposal to %s", txt_path)
        return {"txt_path": txt_path}