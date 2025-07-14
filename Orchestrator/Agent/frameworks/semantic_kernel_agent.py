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
        ai_model_id = os.getenv('AI_MODEL_ID')
        service_id = os.getenv('SERVICE_ID')

        if llm_provider == "azure_openai":
            self.kernel.add_service(
                AzureChatCompletion(
                    service_id=service_id,
                    deployment_name=os.getenv("AZURE_LLM_MODEL_DEPLOYMENT"),
                    endpoint=os.getenv("AZURE_ENDPOINT"),
                    api_key=os.getenv("AZURE_API_KEY"),
                ),
            )
        elif llm_provider == "openai":
            self.kernel.add_service(
                OpenAIChatCompletion(
                    service_id=service_id,
                    ai_model_id=ai_model_id,
                    api_key=os.getenv("OPENAI_API_KEY"),
                ),
            )
        elif llm_provider == "gemini":
            self.kernel.add_service(
                GoogleGeminiChatCompletion(
                    service_id=service_id,
                    ai_model_id=ai_model_id,
                    api_key=os.getenv("GEMINI_API_KEY"),
                ),
            )
        elif llm_provider == "groq":
            self.kernel.add_service(
                GroqChatCompletion(
                    service_id=service_id,
                    ai_model_id=ai_model_id,
                    api_key=os.getenv("GROQ_API_KEY"),
                ),
            )
        else:
            raise ValueError(f"Unknown LLM provider: {llm_provider}")

    async def chat(self, query):
        result = await self.kernel.invoke_prompt(query)
        return str(result)
