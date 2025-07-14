import semantic_kernel as sk
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from .base import Agent
from dotenv import load_dotenv
import os

load_dotenv()

class SemanticKernelAgent(Agent):
    def __init__(self):
        self.kernel = sk.Kernel()
        self.kernel.add_service(
            AzureChatCompletion(
                service_id="default",
                deployment_name=os.getenv("AZURE_LLM_MODEL_DEPLOYMENT"),
                endpoint=os.getenv("AZURE_ENDPOINT"),
                api_key=os.getenv("AZURE_API_KEY"),
            ),
        )

    async def chat(self, query):
        result = await self.kernel.invoke_prompt(query)
        return str(result)
