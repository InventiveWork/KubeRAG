import os
from dotenv import load_dotenv
from .base import Agent
import google.generativeai as genai
from openai import AzureOpenAI, OpenAI
from groq import Groq

load_dotenv()

class GeminiAgent(Agent):
    def __init__(self):
        llm_provider = os.getenv('LLM_PROVIDER')
        if llm_provider == "gemini":
            api_key = os.getenv('GEMINI_API_KEY')
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
        elif llm_provider == "azure_openai":
            self.model = AzureOpenAI(
                api_key=os.getenv("AZURE_API_KEY"),
                api_version="2024-02-01",
                azure_endpoint=os.getenv("AZURE_ENDPOINT")
            )
        elif llm_provider == "openai":
            self.model = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        elif llm_provider == "groq":
            self.model = Groq(api_key=os.getenv("GROQ_API_KEY"))
        else:
            raise ValueError(f"Unknown LLM provider: {llm_provider}")

    def chat(self, query):
        llm_provider = os.getenv('LLM_PROVIDER')
        if llm_provider == "gemini":
            response = self.model.generate_content(query)
            return response.text
        else:
            response = self.model.chat.completions.create(
                model=os.getenv("AZURE_LLM_MODEL_DEPLOYMENT"),
                messages=[
                    {
                        "role": "user",
                        "content": query
                    }
                ]
            )
            return response.choices[0].message.content
