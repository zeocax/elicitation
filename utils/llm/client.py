"""Unified LLM client interface"""

from typing import Optional, Dict, Any, List
from .config import LLMConfig
from .providers import OpenAIProvider, AnthropicProvider, LLMProvider


class LLMClient:
    """Unified client for different LLM providers"""
    
    def __init__(self, config: Optional[LLMConfig] = None):
        """Initialize LLM client with configuration
        
        Args:
            config: LLMConfig instance. If None, creates a new one.
        """
        self.config = config or LLMConfig()
        self._provider: Optional[LLMProvider] = None
    
    def _get_provider(self) -> LLMProvider:
        """Get the appropriate provider based on configuration"""
        if self._provider:
            return self._provider
        
        provider_name = self.config.provider
        
        if provider_name == 'openai':
            api_key = self.config.get_api_key('openai')
            if not api_key:
                raise ValueError("OpenAI API key not found. Set OPENAI_API_KEY environment variable.")
            
            # Determine proxy
            proxy_url = self.config.openai_proxy or self.config.https_proxy or self.config.http_proxy
            
            self._provider = OpenAIProvider(
                api_key=api_key,
                base_url=self.config.openai_base_url if self.config.openai_base_url else None,
                proxy=proxy_url if proxy_url else None
            )
        
        elif provider_name == 'anthropic':
            api_key = self.config.get_api_key('anthropic')
            if not api_key:
                raise ValueError("Anthropic API key not found. Set ANTHROPIC_API_KEY environment variable.")
            
            self._provider = AnthropicProvider(api_key=api_key)
        
        else:
            raise ValueError(f"Unsupported AI provider: {provider_name}")
        
        return self._provider
    
    async def call(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """Make a call to the LLM
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            **kwargs: Additional parameters (model, temperature, max_tokens, etc.)
        
        Returns:
            Response string from the LLM (content only, reasoning is logged)
        """
        provider = self._get_provider()
        
        # Merge config defaults with provided kwargs
        call_kwargs = {
            'model': kwargs.get('model', self.config.model),
        }
        
        if self.config.temperature is not None:
            call_kwargs['temperature'] = self.config.temperature
        if 'temperature' in kwargs:
            call_kwargs['temperature'] = kwargs['temperature']
        
        if self.config.max_tokens is not None:
            call_kwargs['max_tokens'] = self.config.max_tokens
        if 'max_tokens' in kwargs:
            call_kwargs['max_tokens'] = kwargs['max_tokens']
        
        # Add any other kwargs
        for key, value in kwargs.items():
            if key not in call_kwargs:
                call_kwargs[key] = value
        
        result = await provider.call(messages, **call_kwargs)
        
        return result
    
    async def complete(self, prompt: str, system_prompt: Optional[str] = None, **kwargs) -> str:
        """Simple completion interface
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            **kwargs: Additional parameters
        
        Returns:
            Response string from the LLM
        """
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        return await self.call(messages, **kwargs)