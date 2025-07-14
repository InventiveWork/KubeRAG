import os
from dotenv import load_dotenv
from .base import Agent
from langchain_openai import AzureChatOpenAI, ChatOpenAI
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()

class LangChainAgent(Agent):
    def __init__(self):
        llm_provider = os.getenv('LLM_PROVIDER')
        if llm_provider == "azure_openai":
            self.llm = AzureChatOpenAI(
                openai_api_version=os.getenv("AZURE_API_VERSION"),
                azure_deployment=os.getenv("AZURE_LLM_MODEL_DEPLOYMENT"),
                azure_endpoint=os.getenv("AZURE_ENDPOINT"),
                api_key=os.getenv("AZURE_API_KEY"),
            )
        elif llm_provider == "openai":
            self.llm = ChatOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        elif llm_provider == "groq":
            self.llm = ChatGroq(api_key=os.getenv("GROQ_API_KEY"))
        elif llm_provider == "gemini":
            self.llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=os.getenv("GEMINI_API_KEY"))
        else:
            raise ValueError(f"Unknown LLM provider: {llm_provider}")

    def chat(self, query):
        return self.llm.invoke(query).content
