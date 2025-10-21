import os
import socket
from typing import Literal
from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()


class Config(BaseModel):
    """
    Central configuration for the RFP tool.
    Auto-detects environment and sets up appropriate resources.
    """
    
    environment: Literal["local", "cloud"]
    
    openai_api_key: str | None
    openai_model: str
    
    aws_region: str
    bedrock_model_id: str
    
    ollama_host: str
    ollama_model: str
    
    storage_bucket: str
    storage_table: str
    
    minio_endpoint: str
    sqlite_path: str
    
    
    @staticmethod
    def is_cloud() -> bool:
        """
        Detects if running in cloud environment (AWS).
        Checks for AWS environment variables and DNS resolution.
        """
        aws_indicators = [
            os.getenv('AWS_EXECUTION_ENV'),
            os.getenv('AWS_LAMBDA_FUNCTION_NAME'),
            os.getenv('ECS_CONTAINER_METADATA_URI'),
        ]
        
        if any(aws_indicators):
            return True
        
        try:
            hostname = socket.getfqdn()
            if 'amazonaws.com' in hostname or 'ec2.internal' in hostname:
                return True
        except:
            pass
        
        return False
    
    
    @classmethod
    def load(cls) -> "Config":
        """
        Loads configuration from environment variables.
        Auto-detects cloud vs local and sets appropriate defaults.
        """
        env = "cloud" if cls.is_cloud() else "local"
        
        return cls(
            environment=env,
            
            openai_api_key=os.getenv("OPENAI_API_KEY"),
            openai_model=os.getenv("OPENAI_MODEL", "gpt-4"),
            
            aws_region=os.getenv("AWS_REGION", "us-east-1"),
            bedrock_model_id=os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-sonnet-20240229-v1:0"),
            
            ollama_host=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
            ollama_model=os.getenv("OLLAMA_MODEL", "llama3.2"),
            
            storage_bucket=os.getenv("STORAGE_BUCKET", "rfp-tool-storage"),
            storage_table=os.getenv("STORAGE_TABLE", "rfp-tool-sessions"),
            
            minio_endpoint=os.getenv("MINIO_ENDPOINT", "localhost:9000"),
            sqlite_path=os.getenv("SQLITE_PATH", ".data/local.db"),
        )
    
    
    def get_llm_priority(self) -> list[str]:
        """
        Returns LLM providers in priority order based on available credentials.
        Priority: OpenAI -> Bedrock -> Ollama
        """
        priority = []
        
        if self.openai_api_key:
            priority.append("openai")
        
        if self.environment == "cloud" or self._has_aws_credentials():
            priority.append("bedrock")
        
        priority.append("ollama")
        
        return priority
    
    
    def _has_aws_credentials(self) -> bool:
        """
        Checks if AWS credentials are available for Bedrock access.
        """
        try:
            import boto3
            sts = boto3.client('sts', region_name=self.aws_region)
            sts.get_caller_identity()
            return True
        except:
            return False


config = Config.load()

