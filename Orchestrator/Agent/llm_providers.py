#!/usr/bin/env python3
"""
LLM Provider implementations for KubeRAG Chat Agent
Supports Azure OpenAI, OpenAI, Gemini, Anthropic, and other providers
"""

import os
import logging
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class BaseLLMProvider(ABC):
    """Base class for all LLM providers"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.initialize()
    
    @abstractmethod
    def initialize(self):
        """Initialize the LLM provider"""
        pass
    
    @abstractmethod
    async def generate_response(self, prompt: str) -> Optional[str]:
        """Generate a response from the LLM"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is available and configured"""
        pass

class AzureOpenAIProvider(BaseLLMProvider):
    """Azure OpenAI provider"""
    
    def initialize(self):
        try:
            from openai import AsyncAzureOpenAI
            
            self.api_key = self.config.get('api_key') or os.getenv('AZURE_OPENAI_API_KEY')
            self.endpoint = self.config.get('endpoint') or os.getenv('AZURE_OPENAI_ENDPOINT')
            self.deployment = self.config.get('deployment') or os.getenv('AZURE_OPENAI_DEPLOYMENT', 'gpt-4o-mini')
            self.api_version = self.config.get('api_version') or os.getenv('AZURE_API_VERSION', '2025-01-01-preview')
            
            if self.api_key and self.endpoint:
                self.client = AsyncAzureOpenAI(
                    api_key=self.api_key,
                    azure_endpoint=self.endpoint,
                    api_version=self.api_version
                )
                self.available = True
                logger.info("Azure OpenAI provider initialized successfully")
            else:
                self.available = False
                logger.warning("Azure OpenAI provider missing configuration")
                
        except ImportError:
            self.available = False
            logger.error("Azure OpenAI library not available. Install with: pip install openai")
        except Exception as e:
            self.available = False
            logger.error(f"Failed to initialize Azure OpenAI: {e}")
    
    async def generate_response(self, prompt: str) -> Optional[str]:
        if not self.available:
            return None
            
        try:
            response = await self.client.chat.completions.create(
                model=self.deployment,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.7
            )
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Azure OpenAI generation failed: {e}")
            return None
    
    def is_available(self) -> bool:
        return self.available

class OpenAIProvider(BaseLLMProvider):
    """OpenAI provider"""
    
    def initialize(self):
        try:
            from openai import AsyncOpenAI
            
            self.api_key = self.config.get('api_key') or os.getenv('OPENAI_API_KEY')
            self.model = self.config.get('model') or os.getenv('OPENAI_MODEL', 'gpt-4o-mini')
            self.base_url = self.config.get('base_url') or os.getenv('OPENAI_BASE_URL')
            
            if self.api_key:
                client_kwargs = {"api_key": self.api_key}
                if self.base_url:
                    client_kwargs["base_url"] = self.base_url
                    
                self.client = AsyncOpenAI(**client_kwargs)
                self.available = True
                logger.info("OpenAI provider initialized successfully")
            else:
                self.available = False
                logger.warning("OpenAI provider missing API key")
                
        except ImportError:
            self.available = False
            logger.error("OpenAI library not available. Install with: pip install openai")
        except Exception as e:
            self.available = False
            logger.error(f"Failed to initialize OpenAI: {e}")
    
    async def generate_response(self, prompt: str) -> Optional[str]:
        if not self.available:
            return None
            
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.7
            )
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"OpenAI generation failed: {e}")
            return None
    
    def is_available(self) -> bool:
        return self.available

class AnthropicProvider(BaseLLMProvider):
    """Anthropic Claude provider"""
    
    def initialize(self):
        try:
            import anthropic
            
            self.api_key = self.config.get('api_key') or os.getenv('ANTHROPIC_API_KEY')
            self.model = self.config.get('model') or os.getenv('ANTHROPIC_MODEL', 'claude-3-5-sonnet-20241022')
            
            if self.api_key:
                self.client = anthropic.AsyncAnthropic(api_key=self.api_key)
                self.available = True
                logger.info("Anthropic provider initialized successfully")
            else:
                self.available = False
                logger.warning("Anthropic provider missing API key")
                
        except ImportError:
            self.available = False
            logger.error("Anthropic library not available. Install with: pip install anthropic")
        except Exception as e:
            self.available = False
            logger.error(f"Failed to initialize Anthropic: {e}")
    
    async def generate_response(self, prompt: str) -> Optional[str]:
        if not self.available:
            return None
            
        try:
            response = await self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return response.content[0].text
            
        except Exception as e:
            logger.error(f"Anthropic generation failed: {e}")
            return None
    
    def is_available(self) -> bool:
        return self.available

class GeminiProvider(BaseLLMProvider):
    """Google Gemini provider"""
    
    def initialize(self):
        try:
            import google.generativeai as genai
            
            self.api_key = self.config.get('api_key') or os.getenv('GOOGLE_API_KEY')
            self.model_name = self.config.get('model') or os.getenv('GEMINI_MODEL', 'gemini-1.5-flash')
            
            if self.api_key:
                genai.configure(api_key=self.api_key)
                self.model = genai.GenerativeModel(self.model_name)
                self.available = True
                logger.info("Gemini provider initialized successfully")
            else:
                self.available = False
                logger.warning("Gemini provider missing API key")
                
        except ImportError:
            self.available = False
            logger.error("Gemini library not available. Install with: pip install google-generativeai")
        except Exception as e:
            self.available = False
            logger.error(f"Failed to initialize Gemini: {e}")
    
    async def generate_response(self, prompt: str) -> Optional[str]:
        if not self.available:
            return None
            
        try:
            # Note: google-generativeai doesn't have async support yet
            # This is a synchronous call wrapped for async compatibility
            import asyncio
            
            def _generate():
                response = self.model.generate_content(
                    prompt,
                    generation_config={
                        'max_output_tokens': 1000,
                        'temperature': 0.7,
                    }
                )
                return response.text
            
            # Run in thread to avoid blocking
            response_text = await asyncio.get_event_loop().run_in_executor(None, _generate)
            return response_text
            
        except Exception as e:
            logger.error(f"Gemini generation failed: {e}")
            return None
    
    def is_available(self) -> bool:
        return self.available

class OllamaProvider(BaseLLMProvider):
    """Ollama local provider"""
    
    def initialize(self):
        try:
            self.base_url = self.config.get('base_url') or os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
            self.model = self.config.get('model') or os.getenv('OLLAMA_MODEL', 'llama2')
            
            # Test if Ollama is available by making a connection test
            import httpx
            import asyncio
            
            async def test_connection():
                try:
                    async with httpx.AsyncClient(timeout=5.0) as client:
                        response = await client.get(f"{self.base_url}/api/tags")
                        return response.status_code == 200
                except:
                    return False
            
            # Run the connection test
            loop = None
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            if loop.is_running():
                # If we're in an async context, we can't test synchronously
                # Mark as available but it will fail at runtime if not reachable
                self.available = True
                logger.info("Ollama provider initialized (connection not tested in async context)")
            else:
                self.available = loop.run_until_complete(test_connection())
                if self.available:
                    logger.info("Ollama provider initialized successfully")
                else:
                    logger.warning("Ollama provider not available - connection test failed")
                
        except Exception as e:
            self.available = False
            logger.error(f"Failed to initialize Ollama: {e}")
    
    async def generate_response(self, prompt: str) -> Optional[str]:
        if not self.available:
            return None
            
        try:
            import httpx
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self.base_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.7,
                            "num_predict": 1000
                        }
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get("response", "")
                else:
                    logger.error(f"Ollama API error: {response.status_code}")
                    return None
            
        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            return None
    
    def is_available(self) -> bool:
        return self.available

class LLMProviderFactory:
    """Factory for creating LLM providers"""
    
    PROVIDERS = {
        'azure_openai': AzureOpenAIProvider,
        'openai': OpenAIProvider,
        'anthropic': AnthropicProvider,
        'gemini': GeminiProvider,
        'ollama': OllamaProvider,
    }
    
    @classmethod
    def create_provider(cls, provider_type: str, config: Dict[str, Any]) -> Optional[BaseLLMProvider]:
        """Create an LLM provider instance"""
        if provider_type not in cls.PROVIDERS:
            logger.error(f"Unknown provider type: {provider_type}")
            return None
        
        try:
            provider_class = cls.PROVIDERS[provider_type]
            return provider_class(config)
        except Exception as e:
            logger.error(f"Failed to create provider {provider_type}: {e}")
            return None
    
    @classmethod
    def get_available_providers(cls, configs: Dict[str, Dict[str, Any]]) -> Dict[str, BaseLLMProvider]:
        """Get all available and configured providers"""
        available_providers = {}
        
        for provider_type, provider_config in configs.items():
            provider = cls.create_provider(provider_type, provider_config)
            if provider and provider.is_available():
                available_providers[provider_type] = provider
                
        return available_providers