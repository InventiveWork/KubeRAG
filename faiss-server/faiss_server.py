#!/usr/bin/env python3
"""
FAISS Server - A REST API wrapper for FAISS vector operations
"""
import os
import json
import pickle
import numpy as np
import faiss
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import uvicorn

app = FastAPI(title="FAISS Vector Store Server")

# Configuration
FAISS_INDEX_PATH = os.getenv("FAISS_INDEX_PATH", "/data/faiss_index")
FAISS_METADATA_PATH = os.getenv("FAISS_METADATA_PATH", "/data/faiss_metadata.pkl")
DIMENSION = int(os.getenv("DIMENSION", "384"))

# Global variables
index = None
metadata = {}

class VectorRequest(BaseModel):
    id: str
    vector: List[float]
    payload: Dict[str, Any]

class SearchRequest(BaseModel):
    vector: List[float]
    limit: int = 5

class SearchResult(BaseModel):
    id: str
    score: float
    payload: Dict[str, Any]

def load_index():
    """Load FAISS index and metadata"""
    global index, metadata

    try:
        if os.path.exists(FAISS_INDEX_PATH):
            index = faiss.read_index(FAISS_INDEX_PATH)
        else:
            # Create new index
            index = faiss.IndexFlatL2(DIMENSION)

        if os.path.exists(FAISS_METADATA_PATH):
            with open(FAISS_METADATA_PATH, 'rb') as f:
                metadata = pickle.load(f)
        else:
            metadata = {}

    except Exception as e:
        print(f"Error loading index: {e}")
        index = faiss.IndexFlatL2(DIMENSION)
        metadata = {}

def save_index():
    """Save FAISS index and metadata"""
    try:
        os.makedirs(os.path.dirname(FAISS_INDEX_PATH), exist_ok=True)
        faiss.write_index(index, FAISS_INDEX_PATH)

        os.makedirs(os.path.dirname(FAISS_METADATA_PATH), exist_ok=True)
        with open(FAISS_METADATA_PATH, 'wb') as f:
            pickle.dump(metadata, f)
    except Exception as e:
        print(f"Error saving index: {e}")

@app.on_event("startup")
async def startup():
    """Initialize FAISS index on startup"""
    load_index()

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy", "index_size": index.ntotal if index else 0}

@app.post("/add")
async def add_vector(request: VectorRequest):
    """Add a vector to the index"""
    try:
        vector = np.array([request.vector], dtype=np.float32)

        # Add to index
        index.add(vector)

        # Store metadata
        vector_id = index.ntotal - 1  # Use index position as ID
        metadata[vector_id] = {
            "id": request.id,
            "payload": request.payload
        }

        # Save to disk
        save_index()

        return {"status": "success", "vector_id": vector_id}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search")
async def search_vectors(request: SearchRequest):
    """Search for similar vectors"""
    try:
        if index.ntotal == 0:
            return {"results": []}

        query_vector = np.array([request.vector], dtype=np.float32)

        # Search
        distances, indices = index.search(query_vector, min(request.limit, index.ntotal))

        results = []
        for i, (distance, idx) in enumerate(zip(distances[0], indices[0])):
            if idx >= 0 and idx in metadata:  # Valid result
                result = SearchResult(
                    id=metadata[idx]["id"],
                    score=1.0 / (1.0 + distance),  # Convert distance to similarity
                    payload=metadata[idx]["payload"]
                )
                results.append(result)

        return {"results": results}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/count")
async def get_count():
    """Get the number of vectors in the index"""
    return {"count": index.ntotal if index else 0}

@app.delete("/clear")
async def clear_index():
    """Clear the entire index"""
    global index, metadata
    try:
        index = faiss.IndexFlatL2(DIMENSION)
        metadata = {}
        save_index()
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)