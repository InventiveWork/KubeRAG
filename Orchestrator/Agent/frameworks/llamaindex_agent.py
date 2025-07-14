from llama_index.core.agent import ReActAgent
from llama_index.core.tools import FunctionTool
from llama_index.llms.azure_openai import AzureOpenAI
from llama_index.embeddings.azure_openai import AzureOpenAIEmbedding
from llama_index.core import Settings
from dotenv import load_dotenv
import os
from .base import Agent
from ..tools import (
    AnalyzeTextTool,
    SearchTextTool,
    GenerateTextTool,
    ExpandTextTool,
    FormatTextTool,
    GmailSendMessageTool,
)

load_dotenv()
api_key = os.getenv('AZURE_API_KEY')
azure_endpoint = os.getenv('AZURE_ENDPOINT')
api_version = os.getenv('AZURE_API_VERSION')

llm = AzureOpenAI(
    model="gpt-4-32k",
    deployment_name="gpt-4-32k",
    api_key=api_key,
    azure_endpoint=azure_endpoint,
    api_version=api_version,
)

embed_model = AzureOpenAIEmbedding(
    model="text-embedding-ada-002",
    deployment_name="text-embedding-ada-002",
    api_key=os.getenv('AZURE_API_KEY_EMBED'),
    azure_endpoint=os.getenv('AZURE_ENDPOINT_EMBED'),
    api_version=os.getenv('AZURE_ENDPOINT_VERSION_EMBED'),
)

Settings.llm = llm
Settings.embed_model = embed_model

class LlamaIndexAgent(Agent):
    def __init__(self):
        analyze_tool = FunctionTool.from_defaults(AnalyzeTextTool().execute)
        search_tool = FunctionTool.from_defaults(SearchTextTool().execute)
        generate_tool = FunctionTool.from_defaults(GenerateTextTool().execute)
        expand_tool = FunctionTool.from_defaults(ExpandTextTool().execute)
        format_tool = FunctionTool.from_defaults(FormatTextTool().execute)
        email_tool = FunctionTool.from_defaults(GmailSendMessageTool().execute)

        self.agent = ReActAgent.from_tools([analyze_tool, search_tool, generate_tool, expand_tool, format_tool, email_tool ], llm=llm, verbose=True, max_iterations=15)

    def chat(self, query):
        return self.agent.chat(query)
