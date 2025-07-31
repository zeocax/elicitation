"""LLM configuration management"""

import os
from typing import Optional, Dict, Any
from pathlib import Path


class LLMConfig:
    """Configuration for LLM models"""
    
    def __init__(self):
        # Load .env file if it exists
        self._load_env_file()
        
        # Default to OpenAI, but support multiple providers
        self.provider = os.environ.get('AI_PROVIDER', 'openai')
        
        # API keys from environment variables
        self.openai_api_key = os.environ.get('OPENAI_API_KEY', '')
        self.openai_base_url = os.environ.get('OPENAI_BASE_URL', '')  # Optional custom endpoint
        self.anthropic_api_key = os.environ.get('ANTHROPIC_API_KEY', '')
        
        # Proxy settings
        self.http_proxy = os.environ.get('HTTP_PROXY', '') or os.environ.get('http_proxy', '')
        self.https_proxy = os.environ.get('HTTPS_PROXY', '') or os.environ.get('https_proxy', '')
        self.openai_proxy = os.environ.get('OPENAI_PROXY', '')  # OpenAI-specific proxy
        
        # Model settings
        self.model = os.environ.get('AI_MODEL', 'gpt-4')
        
        # temperature is optional - if not set, the model will use its default
        temperature = os.environ.get('AI_TEMPERATURE', '')
        self.temperature = float(temperature) if temperature else None

        # max_tokens is optional - if not set, the model will use its default
        max_tokens_str = os.environ.get('AI_MAX_TOKENS', '')
        self.max_tokens = int(max_tokens_str) if max_tokens_str else None
    
    def _load_env_file(self):
        """Load environment variables from .env file"""
        # Look for .env in multiple locations
        possible_paths = [
            Path.cwd() / '.env',  # Current directory
            Path(__file__).parent.parent.parent / '.env',  # Project root
            Path.home() / '.env',  # User home
        ]
        
        for env_path in possible_paths:
            if env_path.exists():
                try:
                    with open(env_path, 'r') as f:
                        for line in f:
                            line = line.strip()
                            if line and not line.startswith('#') and '=' in line:
                                key, value = line.split('=', 1)
                                key = key.strip()
                                value = value.strip().strip('"').strip("'")
                                if key not in os.environ:  # Don't override existing env vars
                                    os.environ[key] = value
                    break  # Stop after first .env file found
                except Exception:
                    pass  # Silently ignore .env file errors
    
    def get_api_key(self, provider: Optional[str] = None) -> str:
        """Get API key for specified provider"""
        provider = provider or self.provider
        
        if provider == 'openai':
            return self.openai_api_key
        elif provider == 'anthropic':
            return self.anthropic_api_key
        else:
            return ''
    
    def get_model_config(self) -> Dict[str, Any]:
        """Get model configuration"""
        return {
            'model': self.model,
            'temperature': self.temperature,
            'max_tokens': self.max_tokens
        }