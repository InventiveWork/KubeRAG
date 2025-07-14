from .frameworks.base import Tool
from googlesearch import search
from bs4 import BeautifulSoup
import faiss
from llama_index.vector_stores.faiss import FaissVectorStore
from llama_index.core import StorageContext, load_index_from_storage
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex
from llama_index.readers.web import SimpleWebPageReader
from llama_index.core.llms import ChatMessage
from llama_index.llms.azure_openai import AzureOpenAI
from pydantic import BaseModel, Field
import os
from dotenv import load_dotenv
import base64
from email.message import EmailMessage
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import make_msgid

load_dotenv()
api_key = os.getenv('AZURE_API_KEY')
azure_endpoint = os.getenv('AZURE_ENDPOINT')
api_version = os.getenv('AZURE_API_VERSION')

SEARCH_RESULT_NUM=3
SCOPES = ["https://www.googleapis.com/auth/gmail.send"]

llm = AzureOpenAI(
    model="gpt-4-32k",
    deployment_name="gpt-4-32k",
    api_key=api_key,
    azure_endpoint=azure_endpoint,
    api_version=api_version,
)

class Topic(BaseModel):
    topics: list

class AnalyzeTextTool(Tool):
    def execute(self, text: str) -> Topic:
        messages = [
        ChatMessage(
            role="system", content="generate 10 topics as JSON object only"
        ),
        ChatMessage(role="user", content=text),
        ]
        return llm.chat(messages)

class SearchTextTool(Tool):
    def execute(self, text: str):
        res = search(text, num=1, stop=SEARCH_RESULT_NUM)
        for i in res:
            print(i)
            store_text(i)

def store_text(page):
    # dimensions of text-ada-embedding-002
    d = 1536
    faiss_index = faiss.IndexFlatL2(d)

    documents = SimpleWebPageReader(html_to_text=True).load_data(
    [page]
)
    vector_store = FaissVectorStore(faiss_index=faiss_index)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    index = VectorStoreIndex.from_documents(
        documents, storage_context=storage_context
    )

    index.storage_context.persist()

class GenerateTextTool(Tool):
    def execute(self, text: str) -> str:
        vector_store = FaissVectorStore.from_persist_dir("./storage")
        storage_context = StorageContext.from_defaults(
            vector_store=vector_store, persist_dir="./storage"
        )
        index = load_index_from_storage(storage_context=storage_context)

        query_engine = index.as_query_engine()
        answer = query_engine.query(text)
        return answer

class ExpandTextTool(Tool):
    def execute(self, text: str) -> str:
        vector_store = FaissVectorStore.from_persist_dir("./storage")
        storage_context = StorageContext.from_defaults(
            vector_store=vector_store, persist_dir="./storage"
        )
        index = load_index_from_storage(storage_context=storage_context)

        query_engine = index.as_query_engine(
                            system_prompt="expand on the content and generate a new text"

        )
        answer = query_engine.query(text)
        return answer

class FormatTextTool(Tool):
    def execute(self, text: str):
        messages = [
        ChatMessage(
            role="system", content="generate nicely formated html from input"
        ),
        ChatMessage(role="user", content=text),
        ]
        return llm.chat(messages)

class GmailSendMessageTool(Tool):
    def execute(self, text: str, email: str):
        creds = None
        if os.path.exists("token.json"):
            creds = Credentials.from_authorized_user_file("token.json", SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    "credentials.json", SCOPES
                )
                creds = flow.run_local_server(port=0)
            with open("token.json", "w") as token:
                token.write(creds.to_json())

        try:
            service = build("gmail", "v1", credentials=creds)
            message = EmailMessage()

            asparagus_cid = make_msgid()
            message.add_alternative(text)

            part = MIMEText(text, 'html')
            message.attach(part)
            message["To"] = email
            message["From"] = "atnniya@gmail.com"
            message["Subject"] = "AI Daily News Letter "

            encoded_message = base64.urlsafe_b64encode(message.as_bytes()).decode()

            create_message = {"raw": encoded_message}
            send_message = (
                service.users()
                .messages()
                .send(userId="me", body=create_message)
                .execute()
            )
            return send_message
        except HttpError as error:
            print(f"An error occurred: {error}")
            return None
