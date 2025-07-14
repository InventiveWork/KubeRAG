from langchain_openai import AzureChatOpenAI
from .base import Agent
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.getenv('AZURE_API_KEY')
azure_endpoint = os.getenv('AZURE_ENDPOINT')
api_version = os.getenv('AZURE_API_VERSION')

class LangChainAgent(Agent):
    def __init__(self):
        self.llm = AzureChatOpenAI(
            openai_api_version=api_version,
            azure_deployment="gpt-4-32k",
            azure_endpoint=azure_endpoint,
            api_key=api_key,
        )

    def chat(self, query):
        return self.llm.invoke(query).content
