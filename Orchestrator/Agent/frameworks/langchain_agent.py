from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.prompts import PromptTemplate
from langchain_openai import AzureChatOpenAI
from ..tools import (
    AnalyzeTextTool,
    SearchTextTool,
    GenerateTextTool,
    ExpandTextTool,
    FormatTextTool,
    GmailSendMessageTool,
)
from .base import Agent
from langchain.tools import Tool
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.getenv('AZURE_API_KEY')
azure_endpoint = os.getenv('AZURE_ENDPOINT')
api_version = os.getenv('AZURE_API_VERSION')

class LangChainAgent(Agent):
    def __init__(self):
        llm = AzureChatOpenAI(
            openai_api_version=api_version,
            azure_deployment="gpt-4-32k",
            azure_endpoint=azure_endpoint,
            api_key=api_key,
        )

        tools = [
            Tool(
                name="Analyze Text",
                func=AnalyzeTextTool().execute,
                description="Analyzes text and returns a list of topics.",
            ),
            Tool(
                name="Search Text",
                func=SearchTextTool().execute,
                description="Searches for text on the web.",
            ),
            Tool(
                name="Generate Text",
                func=GenerateTextTool().execute,
                description="Generates text from a given prompt.",
            ),
            Tool(
                name="Expand Text",
                func=ExpandTextTool().execute,
                description="Expands on a given text.",
            ),
            Tool(
                name="Format Text",
                func=FormatTextTool().execute,
                description="Formats text as HTML.",
            ),
            Tool(
                name="Send Email",
                func=GmailSendMessageTool().execute,
                description="Sends an email.",
            ),
        ]

        template = '''Answer the following questions as best you can. You have access to the following tools:

{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

Begin!

Question: {input}
Thought:{agent_scratchpad}'''

        prompt = PromptTemplate.from_template(template)
        agent = create_react_agent(llm, tools, prompt)
        self.agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)

    def chat(self, query):
        return self.agent_executor.invoke({"input": query})
