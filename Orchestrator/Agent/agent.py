
import os
from dotenv import load_dotenv

load_dotenv()

def get_agent():
    llm_framework = os.getenv('LLM_FRAMEWORK')
    if llm_framework == "llamaindex":
        from .frameworks.llamaindex_agent import LlamaIndexAgent
        return LlamaIndexAgent()
    elif llm_framework == "langchain":
        from .frameworks.langchain_agent import LangChainAgent
        return LangChainAgent()
    else:
        raise ValueError(f"Unknown LLM framework: {llm_framework}")

def chat(input):
    agent = get_agent()
    return agent.chat(input)