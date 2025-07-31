"""LLM provider implementations"""

from typing import Dict, Any, Optional
from abc import ABC, abstractmethod
import re


def parse_content(response: str) -> str:
    """Split response into thinking and content"""
    thinking_patterns = [
        r'<think>(.*?)</think>',
        r'<thought>(.*?)</thought>'
    ]
    thinking_content = None
    content = response
    for pattern in thinking_patterns:
        match = re.match(pattern, response, re.DOTALL)
        # print("pattern", pattern)
        # print("match", match)
        if match:
            thinking_content = match.group(1)
            content = re.sub(pattern, '', response, flags=re.DOTALL)
            break
    
    return thinking_content, content


class LLMProvider(ABC):
    """Abstract base class for LLM providers"""
    
    @abstractmethod
    async def call(self, messages: list, **kwargs) -> str:
        """Make a call to the LLM"""
        pass

class OpenAIProvider(LLMProvider):
    """OpenAI provider implementation"""
    
    def __init__(self, api_key: str, base_url: Optional[str] = None, proxy: Optional[str] = None):
        try:
            import openai
            import httpx
        except ImportError as e:
            if 'httpx' in str(e):
                raise ImportError("httpx library not installed. Run: pip install httpx")
            else:
                raise ImportError("OpenAI library not installed. Run: pip install openai")
        
        self.api_key = api_key
        self.base_url = base_url
        self.proxy = proxy
        self._client = None
        
    def _get_client(self):
        """Get or create OpenAI client"""
        if self._client:
            return self._client
            
        import openai
        import httpx
        
        client_kwargs = {'api_key': self.api_key}
        
        if self.base_url:
            client_kwargs['base_url'] = self.base_url
        
        if self.proxy:
            # Create httpx client with proxy
            http_client = httpx.Client(proxy=self.proxy)
            client_kwargs['http_client'] = http_client
        
        self._client = openai.OpenAI(**client_kwargs)
        return self._client
    
    async def call(self, messages: list, **kwargs) -> str:
        """Make a call to OpenAI"""
        client = self._get_client()
        
        # Build request parameters
        params = {
            'model': kwargs.get('model', 'gpt-4'),
            'messages': messages,
        }
        
        # Add optional parameters
        if 'temperature' in kwargs and kwargs['temperature'] is not None:
            params['temperature'] = kwargs['temperature']
        
        if 'max_tokens' in kwargs and kwargs['max_tokens'] is not None:
            params['max_tokens'] = kwargs['max_tokens']
        
        params["extra_body"] = {
            "extra_body": {
                "google": {
                    "thinking_config": {
                        "thinking_budget": -1,
                        "include_thoughts": True
                    }
                }
            }
        }
        # print("params", params)
        response = client.chat.completions.create(**params)
        content = response.choices[0].message.content.strip()
        thinking_content, content = parse_content(content)
        # print("thinking_content", thinking_content)
        # print("content", content)
        return {
            "thinking_content": thinking_content,
            "content": content
        }


class AnthropicProvider(LLMProvider):
    """Anthropic provider implementation"""
    
    def __init__(self, api_key: str):
        try:
            import anthropic
        except ImportError:
            raise ImportError("Anthropic library not installed. Run: pip install anthropic")
        
        self.api_key = api_key
        self._client = None
        
    def _get_client(self):
        """Get or create Anthropic client"""
        if self._client:
            return self._client
            
        import anthropic
        self._client = anthropic.Anthropic(api_key=self.api_key)
        return self._client
    
    async def call(self, messages: list, **kwargs) -> str:
        """Make a call to Anthropic"""
        client = self._get_client()
        
        # Build request parameters
        params = {
            'model': kwargs.get('model', 'claude-3-5-sonnet-20241022'),
            'messages': messages,
        }
        
        # Add optional parameters
        if 'temperature' in kwargs and kwargs['temperature'] is not None:
            params['temperature'] = kwargs['temperature']
        
        if 'max_tokens' in kwargs and kwargs['max_tokens'] is not None:
            params['max_tokens'] = kwargs['max_tokens']
        
        response = client.messages.create(**params)
        content = response.content[0].text.strip()
        thinking_content, content = parse_content(content)
        return {
            "thinking_content": thinking_content,
            "content": content
        }