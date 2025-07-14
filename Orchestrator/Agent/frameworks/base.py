from abc import ABC, abstractmethod

class Agent(ABC):
    @abstractmethod
    def chat(self, query):
        pass

class Tool(ABC):
    @abstractmethod
    def execute(self, *args, **kwargs):
        pass
