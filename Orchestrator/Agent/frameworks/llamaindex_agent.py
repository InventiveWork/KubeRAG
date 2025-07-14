from llama_index.llms.azure_openai import AzureOpenAI
from dotenv import load_dotenv
import os
from .base import Agent

load_dotenv()
api_key = os.getenv('AZURE_API_KEY')
azure_endpoint = os.getenv('AZURE_ENDPOINT')
api_version = os.getenv('AZURE_API_VERSION')

class LlamaIndexAgent(Agent):
    def __init__(self):
        self.llm = AzureOpenAI(
            model="gpt-4-32k",
            deployment_name="gpt-4-32k",
            api_key=api_key,
            azure_endpoint=azure_endpoint,
            api_version=api_version,
        )

    def chat(self, query):
        return self.llm.complete(query).text
