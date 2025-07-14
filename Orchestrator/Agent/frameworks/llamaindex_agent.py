import os
from dotenv import load_dotenv
from .base import Agent
from llama_index.llms.azure_openai import AzureOpenAI
from llama_index.llms.openai import OpenAI
from llama_index.llms.groq import Groq
from llama_index.llms.gemini import Gemini

load_dotenv()

class LlamaIndexAgent(Agent):
    def __init__(self):
        llm_provider = os.getenv('LLM_PROVIDER')
        if llm_provider == "azure_openai":
            self.llm = AzureOpenAI(
                model=os.getenv("AZURE_LLM_MODEL"),
                deployment_name=os.getenv("AZURE_LLM_MODEL_DEPLOYMENT"),
                api_key=os.getenv("AZURE_API_KEY"),
                azure_endpoint=os.getenv("AZURE_ENDPOINT"),
                api_version=os.getenv("AZURE_API_VERSION"),
            )
        elif llm_provider == "openai":
            self.llm = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        elif llm_provider == "groq":
            self.llm = Groq(api_key=os.getenv("GROQ_API_KEY"))
        elif llm_provider == "gemini":
            self.llm = Gemini(api_key=os.getenv("GEMINI_API_KEY"))
        else:
            raise ValueError(f"Unknown LLM provider: {llm_provider}")

    def chat(self, query):
        return self.llm.complete(query).text
