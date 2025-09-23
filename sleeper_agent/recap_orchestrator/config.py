"""Configuration for the recap orchestrator."""

import os
from pathlib import Path
from typing import Optional

# Load environment variables from global .env file
try:
    from dotenv import load_dotenv
    global_env_path = Path.home() / ".env"
    if global_env_path.exists():
        load_dotenv(global_env_path)
        print(f"✅ Loaded environment variables from {global_env_path}")
    else:
        # Fallback to local .env file
        local_env_path = Path(__file__).parent.parent.parent / ".env"
        if local_env_path.exists():
            load_dotenv(local_env_path)
            print(f"✅ Loaded environment variables from {local_env_path}")
except ImportError:
    print("⚠️ python-dotenv not installed, using system environment variables only")
except Exception as e:
    print(f"⚠️ Error loading .env file: {e}")

class RecapConfig:
    """Configuration for the recap orchestrator."""
    
    # Required environment variables (league ID passed separately via CLI)
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    PERPLEXITY_API_KEY: str = os.getenv("PERPLEXITY_API_KEY", "")
    
    # Optional model configurations
    MODEL_STEP1_PRIMARY: str = os.getenv("MODEL_STEP1_PRIMARY", "sonar")
    MODEL_STEP1_FALLBACK: str = os.getenv("MODEL_STEP1_FALLBACK", "sonar-mini")
    MODEL_STEP2: str = os.getenv("MODEL_STEP2", "gpt-5")
    MODEL_STEP3: str = os.getenv("MODEL_STEP3", "gpt-5")
    MODEL_STEP4_PATCH: str = os.getenv("MODEL_STEP4_PATCH", "gpt-5")
    
    # Other configurations
    TIMEZONE: str = os.getenv("TIMEZONE", "America/New_York")
    
    # API endpoints
    PERPLEXITY_BASE_URL: str = "https://api.perplexity.ai"
    OPENAI_BASE_URL: str = "https://api.openai.com/v1/chat/completions"
    
    # Rate limiting (seconds between requests) - increased for better reliability
    PERPLEXITY_RATE_LIMIT: float = 2.0  # Increased to 2 seconds for better reliability
    OPENAI_RATE_LIMIT: float = 1.5
    
    @classmethod
    def validate(cls) -> None:
        """Validate required environment variables are set."""
        missing = []
        if not cls.OPENAI_API_KEY:
            missing.append("OPENAI_API_KEY")
        if not cls.PERPLEXITY_API_KEY:
            missing.append("PERPLEXITY_API_KEY")
        
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
    
    @classmethod
    def get_estimated_cost_usd(cls, input_chars: int, output_chars: int, model: str) -> float:
        """Estimate cost in USD based on character counts (rough approximation)."""
        # Very rough token estimation: ~4 chars per token
        input_tokens = input_chars / 4
        output_tokens = output_chars / 4
        
        # Rough pricing per 1M tokens (as of 2025)
        pricing = {
            "sonar-mini": {"input": 0.20, "output": 0.20},
            "sonar": {"input": 1.00, "output": 1.00},
            "gpt-4": {"input": 30.00, "output": 60.00},
            "gpt-4o": {"input": 2.50, "output": 10.00},
            "gpt-4o-mini": {"input": 0.15, "output": 0.60},
            "gpt-4-turbo": {"input": 10.00, "output": 30.00},
            "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
            "gpt-5": {"input": 10.00, "output": 30.00},  # Estimated pricing for GPT-5
            "gpt-5-mini": {"input": 2.00, "output": 8.00},
            "gpt-4.1": {"input": 5.00, "output": 15.00},
            "gpt-4.1-mini": {"input": 1.00, "output": 4.00},
        }
        
        # Find matching pricing
        model_key = None
        for key in pricing.keys():
            if key in model:
                model_key = key
                break
        
        if not model_key:
            return 0.0
        
        cost = (
            (input_tokens / 1_000_000) * pricing[model_key]["input"] +
            (output_tokens / 1_000_000) * pricing[model_key]["output"]
        )
        
        return cost