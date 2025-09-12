
from sentence_transformers import SentenceTransformer
import os

def download_model():
    model_name = 'sentence-transformers/all-MiniLM-L6-v2'
    # This path needs to be accessible from within the Docker container.
    # We'll place it in a known directory.
    cache_dir = "/app/models"
    
    print(f"Downloading sentence transformer model: {model_name} to {cache_dir}")
    
    # The SentenceTransformer library will download and cache the model here.
    model = SentenceTransformer(model_name, cache_folder=cache_dir)
    
    # Save the model to the expected location
    save_path = os.path.join(cache_dir, "all-MiniLM-L6-v2")
    model.save(save_path)
    
    print(f"Model downloaded and saved to {save_path}")

if __name__ == "__main__":
    download_model()
