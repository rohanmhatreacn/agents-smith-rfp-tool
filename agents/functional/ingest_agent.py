from strands import Agent
import os
import aiofiles
import logging


class IngestAgent(Agent):
    """Handles uploads and text extraction from PDF, DOCX, XLSX, and TXT."""

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger("IngestAgent")

    async def run(self, file_path: str):
        ext = os.path.splitext(file_path)[-1].lower()
        try:
            # Simplified text extraction - just read the file as text for now
            async with aiofiles.open(file_path, 'r', encoding='utf-8') as f:
                text = await f.read()
            self.logger.info("✅ Extracted content from %s file: %s", ext, file_path)
            return {"content": text}
        except Exception as e:
            self.logger.error("❌ Error parsing %s: %s", file_path, e)
            raise