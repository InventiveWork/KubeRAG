import os
import semantic_kernel as sk
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion, OpenAIChatCompletion
from semantic_kernel.connectors.ai.google import GoogleGeminiChatCompletion
from semantic_kernel.connectors.ai.groq import GroqChatCompletion
from .base import Agent
from dotenv import load_dotenv

load_dotenv()

class SemanticKernelAgent(Agent):
    def __init__(self):
        self.kernel = sk.Kernel()
        llm_provider = os.getenv('LLM_PROVIDER')

        if llm_provider == "azure_openai":
            self.kernel.add_service(
                AzureChatCompletion(
                    service_id="azure_openai",
                    deployment_name=os.getenv("AZURE_LLM_MODEL_DEPLOYMENT"),
                    endpoint=os.getenv("AZURE_ENDPOINT"),
                    api_key=os.getenv("AZURE_API_KEY"),
                ),
            )
        elif llm_provider == "openai":
            self.kernel.add_service(
                OpenAIChatCompletion(
                    service_id="openai",
                    ai_model_id="gpt-3.5-turbo",
                    api_key=os.getenv("OPENAI_API_KEY"),
                ),
            )
        elif llm_provider == "gemini":
            self.kernel.add_service(
                GoogleGeminiChatCompletion(
                    service_id="gemini",
                    ai_model_id="gemini-1.5-flash",
                    api_key=os.getenv("GEMINI_API_KEY"),
                ),
            )
        elif llm_provider == "groq":
            self.kernel.add_service(
                GroqChatCompletion(
                    service_id="groq",
                    ai_model_id="llama3-8b-8192",
                    api_key=os.getenv("GROQ_API_KEY"),
                ),
            )
        else:
            raise ValueError(f"Unknown LLM provider: {llm_provider}")

    async def chat(self, query):
        result = await self.kernel.invoke_prompt(query)
        return str(result)
