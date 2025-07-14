import semantic_kernel as sk
from semantic_kernel.connectors.ai.open_ai import AzureChatCompletion
from .base import Agent
from dotenv import load_dotenv
import os

load_dotenv()

class SemanticKernelAgent(Agent):
    def __init__(self):
        self.kernel = sk.Kernel()
        service_id = "default"
        self.kernel.add_service(
            AzureChatCompletion(
                service_id=service_id,
            ),
        )

    async def chat(self, query):
        chat_function = self.kernel.add_function(
            function_name="chat",
            plugin_name="chatPlugin",
            prompt="{{$input}}",
        )
        result = await self.kernel.invoke(chat_function, sk.KernelArguments(input=query))
        return str(result)
