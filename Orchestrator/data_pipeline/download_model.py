
from sentence_transformers import SentenceTransformer
import os


def download_model():
    model_name = os.getenv('EMBEDDING_MODEL', 'all-MiniLM-L12-v2')
    cache_dir = os.getenv('MODEL_CACHE_DIR', "/app/models")
    save_dir = os.path.join(cache_dir, model_name.replace('/', '_'))

    print(f"Downloading sentence transformer model: {model_name} to {cache_dir}")

    model = SentenceTransformer(model_name, cache_folder=cache_dir)
    os.makedirs(save_dir, exist_ok=True)
    model.save(save_dir)

    print(f"Model downloaded and saved to {save_dir}")

if __name__ == "__main__":
    download_model()
