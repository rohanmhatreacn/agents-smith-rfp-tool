"""
Model configuration module for supporting both Ollama and AWS Bedrock AgentCore.
"""
import os
from typing import Optional, Union
import logging

# Import model types (prefer strands; otherwise provide minimal local shims)
try:
    from strands import Agent
    from strands.models.ollama import OllamaModel
    from strands.models.bedrock import BedrockModel
except ImportError:
    # Provide minimal shims to keep app runnable without strands
    class Agent:
        def __init__(self, model=None, system_prompt="", tools=None):
            self.model = model
            self.system_prompt = system_prompt
            self.tools = tools or []

    class OllamaModel:
        def __init__(self, host="http://localhost:11434", model_id="llama3.2:latest", temperature=0.3):
            self.host = host
            self.model_id = model_id
            self.temperature = temperature

    class BedrockModel:
        def __init__(self, model_id="us.anthropic.claude-3-sonnet-20240229-v1:0", region_name="us-west-2", temperature=0.3):
            self.model_id = model_id
            self.region_name = region_name
            self.temperature = temperature


class ModelConfig:
    """Centralized model configuration for the RFP system."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.model_provider = os.getenv("MODEL_PROVIDER", "ollama").lower()
        # Default to qwen3:4b to match local Ollama setup
        self.model_id = os.getenv("MODEL_ID", "qwen3:4b")
        self.temperature = float(os.getenv("TEMPERATURE", "0.3"))
        
        # Ollama configuration
        self.ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
        
        # Bedrock configuration
        self.bedrock_region = os.getenv("AWS_REGION", "us-west-2")
        self.bedrock_model_id = os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-3-sonnet-20240229-v1:0")

    def _bedrock_credentials_valid(self) -> bool:
        """Best-effort validation that AWS credentials are present and usable.
        Falls back to False if boto3 is unavailable or call fails.
        """
        try:
            import boto3
            from botocore.exceptions import BotoCoreError, NoCredentialsError, ClientError
            sts = boto3.client("sts", region_name=self.bedrock_region)
            sts.get_caller_identity()
            return True
        except (ImportError, NoCredentialsError, BotoCoreError, ClientError, Exception) as e:
            self.logger.warning(f"Bedrock creds check failed, will prefer Ollama fallback: {e}")
            return False
        
    def get_model(self) -> Union[OllamaModel, BedrockModel]:
        """Get the configured model instance."""
        if self.model_provider == "ollama":
            return OllamaModel(
                host=self.ollama_host,
                model_id=self.model_id,
                temperature=self.temperature
            )
        elif self.model_provider == "bedrock":
            # Safety: if AWS creds are invalid/missing, transparently fall back to Ollama
            if self._bedrock_credentials_valid():
                return BedrockModel(
                    model_id=self.bedrock_model_id,
                    region_name=self.bedrock_region,
                    temperature=self.temperature
                )
            # Fall back to Ollama with a sensible default if MODEL_ID was a Bedrock id
            fallback_model_id = os.getenv("OLLAMA_FALLBACK_MODEL_ID", "qwen3:4b")
            self.logger.info("Using Ollama fallback due to Bedrock credential issues")
            return OllamaModel(
                host=self.ollama_host,
                model_id=fallback_model_id,
                temperature=self.temperature
            )
        else:
            raise ValueError(f"Unsupported model provider: {self.model_provider}")
    
    def create_agent(self, system_prompt: str, tools: Optional[list] = None) -> Agent:
        """Create an Agent instance with the configured model."""
        model = self.get_model()
        return Agent(
            model=model,
            system_prompt=system_prompt,
            tools=tools or []
        )


# Global model configuration instance
model_config = ModelConfig()
