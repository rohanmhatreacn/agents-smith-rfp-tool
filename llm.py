import os
import logging
from config import config

logger = logging.getLogger(__name__)


class LLMProvider:
    """
    Unified LLM interface with automatic provider selection and fallback.
    Tries providers in priority order: OpenAI -> Bedrock -> Ollama.
    """
    
    def __init__(self):
        """
        Initializes the LLM provider with automatic selection based on config.
        Falls back to next available provider if primary fails.
        """
        self.providers = config.get_llm_priority()
        self.current_provider = None
        self.model_name = None
        self._initialize()
    
    
    def _initialize(self):
        """
        Attempts to initialize LLM providers in priority order.
        Sets up the first working provider as the active client.
        """
        for provider in self.providers:
            try:
                if provider == "openai":
                    self._verify_openai()
                    self.model_name = config.openai_model
                    self.current_provider = "openai"
                    logger.info("✅ Using OpenAI (%s)", config.openai_model)
                    return
                    
                elif provider == "bedrock":
                    self._verify_bedrock()
                    self.model_name = config.bedrock_model_id
                    self.current_provider = "bedrock"
                    logger.info("✅ Using AWS Bedrock (%s)", config.bedrock_model_id)
                    return
                    
                elif provider == "ollama":
                    self._verify_ollama()
                    self.model_name = config.ollama_model
                    self.current_provider = "ollama"
                    logger.info("✅ Using Ollama (%s)", config.ollama_model)
                    return
                    
            except Exception as e:
                logger.warning("⚠️ Failed to initialize %s: %s", provider, str(e))
                continue
        
        raise RuntimeError("❌ No LLM provider available. Check your configuration.")
    
    
    def _verify_openai(self):
        """
        Verifies OpenAI credentials are available.
        Sets API key in environment for Strands to use.
        """
        if config.openai_api_key:
            os.environ['OPENAI_API_KEY'] = config.openai_api_key
        if not os.getenv('OPENAI_API_KEY'):
            raise ValueError("OPENAI_API_KEY not found")
    
    
    def _verify_bedrock(self):
        """
        Verifies AWS credentials for Bedrock access.
        Strands will use boto3 automatically when AWS credentials are available.
        """
        import boto3
        sts = boto3.client('sts', region_name=config.aws_region)
        sts.get_caller_identity()
        # Set AWS region for Strands to use
        os.environ['AWS_REGION'] = config.aws_region
    
    
    def _verify_ollama(self):
        """
        Verifies Ollama server is accessible.
        Strands will connect to Ollama via the configured host.
        """
        import requests
        response = requests.get(f"{config.ollama_host}/api/tags")
        response.raise_for_status()
        # Set Ollama host for Strands to use
        os.environ['OLLAMA_HOST'] = config.ollama_host
    
    
    def get_model(self):
        """
        Returns the active LLM model for agent initialization.
        For OpenAI, returns None to use direct OpenAI integration.
        For Bedrock/Ollama, returns the model name for Strands.
        """
        if not self.model_name:
            self._initialize()
        
        # For OpenAI, return None to bypass Strands and use direct integration
        if self.current_provider == "openai":
            return None
        
        return self.model_name
    
    
    def __str__(self) -> str:
        """Returns human-readable description of active provider."""
        if self.current_provider == "openai":
            return f"OpenAI ({config.openai_model})"
        elif self.current_provider == "bedrock":
            return f"Bedrock ({config.bedrock_model_id})"
        elif self.current_provider == "ollama":
            return f"Ollama ({config.ollama_model})"
        return "No provider"


llm_provider = LLMProvider()
