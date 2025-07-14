from dotenv import load_dotenv
from vector_store import get_vector_store
import sys

load_dotenv()

def load_index(engineType):
    vector_store = get_vector_store(engineType)
    vector_store.load_index()
    return True

sys.modules[__name__] = load_index