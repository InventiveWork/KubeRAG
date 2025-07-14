import google.generativeai as genai
from .base import Agent
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.getenv('GEMINI_API_KEY')

genai.configure(api_key=api_key)

class GeminiAgent(Agent):
    def __init__(self):
        self.model = genai.GenerativeModel('gemini-1.5-flash')

    def chat(self, query):
        response = self.model.generate_content(query)
        return response.text
