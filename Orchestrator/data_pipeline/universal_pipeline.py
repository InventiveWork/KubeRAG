from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
import logging
import numpy as np
from sentence_transformers import SentenceTransformer
import io
import re
import time
from llama_index.core import SimpleDirectoryReader
from llama_index.readers.file import (
    PDFReader,
    DocxReader,
    UnstructuredReader,
    MarkdownReader,
    CSVReader
)
import json
from datetime import datetime
import uuid
from pathlib import Path
import asyncio

# Import vector store system
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from vector_stores import get_vector_store, list_available_stores, get_store_info
from config import VectorStoreConfigFactory

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="KubeRAG Universal Data Pipeline", version="1.0.0")

# Configuration
VECTOR_STORE_TYPE = os.getenv("VECTOR_STORE_TYPE", "qdrant")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L12-v2")
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "500"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "50"))


_chunk_config_lock: Optional[asyncio.Lock] = None


def _get_chunk_lock() -> asyncio.Lock:
    global _chunk_config_lock
    if _chunk_config_lock is None:
        _chunk_config_lock = asyncio.Lock()
    return _chunk_config_lock

# Initialize embedding model
embedder = None
try:
    logger.info(f"Initializing embedding model: {EMBEDDING_MODEL}")
    model_dir_name = EMBEDDING_MODEL.replace('/', '_')
    packaged_model_path = Path('/app/models') / model_dir_name
    cache_root = Path(os.getenv('TRANSFORMERS_CACHE', '/home/nonroot/.cache/huggingface'))
    cache_root.mkdir(parents=True, exist_ok=True)

    if packaged_model_path.exists():
        embedder = SentenceTransformer(str(packaged_model_path))
        logger.info(f"Embedding model {EMBEDDING_MODEL} loaded successfully from {packaged_model_path}")
    else:
        embedder = SentenceTransformer(EMBEDDING_MODEL, cache_folder=str(cache_root))
        logger.info(
            "Embedding model %s downloaded to cache %s and initialized successfully",
            EMBEDDING_MODEL,
            cache_root,
        )
except Exception as e:
    logger.error(f"Failed to initialize embedding model {EMBEDDING_MODEL}: {e}")
    logger.error("Embedding functionality will be disabled. Document upload may fail.")

# Initialize vector store
vector_store = None
connect_attempts = int(os.getenv("VECTOR_STORE_CONNECT_RETRIES", "5"))
connect_backoff = float(os.getenv("VECTOR_STORE_CONNECT_BACKOFF", "2.0"))

logger.info(f"Creating vector store config for type: {VECTOR_STORE_TYPE}")
config = VectorStoreConfigFactory.from_env(VECTOR_STORE_TYPE)
logger.info("Config created successfully")
config_dict = config.to_dict()
logger.info(f"Vector store config: {config_dict}")

for attempt in range(1, connect_attempts + 1):
    try:
        logger.info("Creating vector store instance (attempt %s/%s)...", attempt, connect_attempts)
        vector_store = get_vector_store(VECTOR_STORE_TYPE, **config_dict)
        logger.info("Vector store %s initialized successfully", VECTOR_STORE_TYPE)
        break
    except Exception as exc:
        logger.error("Failed to initialize vector store: %s", exc)
        if attempt == connect_attempts:
            import traceback

            logger.error("Full traceback: %s", traceback.format_exc())
            vector_store = None
        else:
            sleep_seconds = connect_backoff * attempt
            logger.warning(
                "Retrying vector store initialization in %.1f seconds...", sleep_seconds
            )
            time.sleep(sleep_seconds)

if vector_store is None:
    raise RuntimeError("Vector store initialization failed after retries")

class DocumentRequest(BaseModel):
    text: str
    metadata: Optional[Dict[str, Any]] = {}
    chunk: Optional[bool] = True
    id: Optional[str] = None

class BatchDocumentRequest(BaseModel):
    documents: List[DocumentRequest]

class ProcessingResponse(BaseModel):
    status: str
    message: str
    documents_processed: int
    chunks_created: Optional[int] = None
    index_size: int
    vector_store_used: str

class ConfigUpdateRequest(BaseModel):
    vector_store_type: str
    config: Dict[str, Any]

class ChunkingConfig(BaseModel):
    chunk_size: int = 500
    chunk_overlap: int = 50
    method: str = "words"  # words, sentences, characters

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP, method: str = "words") -> List[str]:
    """Split text into overlapping chunks"""
    if method == "words":
        words = text.split()
        chunks = []
        
        for i in range(0, len(words), chunk_size - overlap):
            chunk = ' '.join(words[i:i + chunk_size])
            if chunk.strip():
                chunks.append(chunk)
        
        return chunks if chunks else [text]
    
    elif method == "sentences":
        sentences = text.split('.')
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            if len(current_chunk) + len(sentence) < chunk_size * 5:  # Rough character estimate
                current_chunk += sentence + "."
            else:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence + "."
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks if chunks else [text]
    
    elif method == "characters":
        chunks = []
        for i in range(0, len(text), chunk_size - overlap):
            chunk = text[i:i + chunk_size]
            if chunk.strip():
                chunks.append(chunk)
        
        return chunks if chunks else [text]
    
    else:
        raise ValueError(f"Unknown chunking method: {method}")

def extract_text_from_pdf(file_content: bytes) -> str:
    """Extract text from PDF file using LlamaIndex PDFReader"""
    try:
        # Create a temporary file for LlamaIndex to read
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
            tmp_file.write(file_content)
            tmp_file_path = tmp_file.name
        
        try:
            # Use LlamaIndex PDFReader for better extraction
            pdf_reader = PDFReader()
            documents = pdf_reader.load_data(file=tmp_file_path)
            
            # Combine all document texts
            text_parts = []
            for doc in documents:
                if doc.text and len(doc.text.strip()) > 50:
                    cleaned_text = clean_extracted_text(doc.text)
                    if cleaned_text:
                        text_parts.append(cleaned_text)
            
            return "\n\n".join(text_parts)
        finally:
            # Clean up temp file
            import os
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)
                
    except Exception as e:
        logger.error(f"Error extracting PDF text with LlamaIndex: {e}")
        # Fallback to basic extraction if LlamaIndex fails
        try:
            import pypdf
            pdf_reader = pypdf.PdfReader(io.BytesIO(file_content))
            text_parts = []
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    cleaned = clean_extracted_text(page_text)
                    if cleaned and len(cleaned) > 50:
                        text_parts.append(cleaned)
            return "\n\n".join(text_parts)
        except Exception as fallback_error:
            logger.error(f"Fallback PDF extraction also failed: {fallback_error}")
            raise

def clean_extracted_text(text: str) -> str:
    """Clean extracted text to remove artifacts and improve readability"""
    if not text:
        return ""
    
    # Remove non-printable characters except newlines and tabs
    text = ''.join(char for char in text if char.isprintable() or char in '\n\t ')
    
    # Fix common extraction issues
    text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
    text = re.sub(r'(\w)-\s+(\w)', r'\1\2', text)  # Fix word breaks
    text = re.sub(r'\n{3,}', '\n\n', text)  # Limit consecutive newlines
    
    # Remove potential binary/corrupted content
    # If more than 30% of the text is non-alphanumeric, it's likely corrupted
    alphanumeric_ratio = sum(c.isalnum() or c.isspace() for c in text) / max(len(text), 1)
    if alphanumeric_ratio < 0.3:
        logger.warning(f"Text appears corrupted (alphanumeric ratio: {alphanumeric_ratio:.2f})")
        return ""
    
    return text.strip()

def extract_text_from_docx(file_content: bytes) -> str:
    """Extract text from DOCX file using LlamaIndex DocxReader"""
    try:
        # Create a temporary file for LlamaIndex to read
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as tmp_file:
            tmp_file.write(file_content)
            tmp_file_path = tmp_file.name
        
        try:
            # Use LlamaIndex DocxReader
            docx_reader = DocxReader()
            documents = docx_reader.load_data(file=tmp_file_path)
            
            # Combine all document texts
            text_parts = []
            for doc in documents:
                if doc.text and doc.text.strip():
                    text_parts.append(doc.text.strip())
            
            return "\n\n".join(text_parts)
        finally:
            # Clean up temp file
            import os
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)
                
    except Exception as e:
        logger.error(f"Error extracting DOCX text with LlamaIndex: {e}")
        # Fallback to python-docx if LlamaIndex fails
        try:
            import docx
            doc = docx.Document(io.BytesIO(file_content))
            text = "\n".join([paragraph.text for paragraph in doc.paragraphs if paragraph.text.strip()])
            return text.strip() if text else ""
        except Exception as fallback_error:
            logger.error(f"Fallback DOCX extraction also failed: {fallback_error}")
            raise

def extract_text_from_file(file_content: bytes, filename: str) -> str:
    """Universal file text extractor using LlamaIndex readers based on file extension"""
    import tempfile
    import os
    
    # Get file extension
    ext = os.path.splitext(filename.lower())[1]
    
    # Map extensions to readers
    reader_map = {
        '.pdf': PDFReader(),
        '.docx': DocxReader(),
        '.doc': DocxReader(),
        '.md': MarkdownReader(),
        '.csv': CSVReader(),
        '.txt': None,  # Plain text, no special reader needed
    }
    
    # For plain text files
    if ext == '.txt':
        try:
            return file_content.decode('utf-8', errors='ignore').strip()
        except Exception as e:
            logger.error(f"Error decoding text file: {e}")
            return ""
    
    # For other supported formats
    if ext in reader_map and reader_map[ext]:
        try:
            # Create temporary file
            with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp_file:
                tmp_file.write(file_content)
                tmp_file_path = tmp_file.name
            
            try:
                # Use appropriate LlamaIndex reader
                reader = reader_map[ext]
                documents = reader.load_data(file=tmp_file_path)
                
                # Combine and clean document texts
                text_parts = []
                for doc in documents:
                    if doc.text and doc.text.strip():
                        cleaned_text = clean_extracted_text(doc.text)
                        if cleaned_text and len(cleaned_text) > 20:
                            text_parts.append(cleaned_text)
                
                return "\n\n".join(text_parts)
            finally:
                # Clean up temp file
                if os.path.exists(tmp_file_path):
                    os.unlink(tmp_file_path)
                    
        except Exception as e:
            logger.error(f"Error extracting text from {filename} using LlamaIndex: {e}")
            
            # Try format-specific fallback
            if ext == '.pdf':
                return extract_text_from_pdf(file_content)
            elif ext in ['.docx', '.doc']:
                return extract_text_from_docx(file_content)
            else:
                raise
    
    # For unsupported formats, try UnstructuredReader as last resort
    try:
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp_file:
            tmp_file.write(file_content)
            tmp_file_path = tmp_file.name
        
        try:
            reader = UnstructuredReader()
            documents = reader.load_data(file=tmp_file_path)
            
            text_parts = []
            for doc in documents:
                if doc.text and doc.text.strip():
                    cleaned_text = clean_extracted_text(doc.text)
                    if cleaned_text:
                        text_parts.append(cleaned_text)
            
            return "\n\n".join(text_parts)
        finally:
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)
                
    except Exception as e:
        logger.error(f"UnstructuredReader also failed for {filename}: {e}")
        raise ValueError(f"Unsupported file format: {ext}")

def process_and_index_text(text: str, metadata: Dict[str, Any], chunk: bool = True, doc_id: str = None) -> int:
    """Process text and add to vector store"""
    if not vector_store:
        raise Exception("Vector store not initialized")
    
    # Generate document ID if not provided
    if not doc_id:
        doc_id = str(uuid.uuid4())
    
    if chunk:
        chunks = chunk_text(text, CHUNK_SIZE, CHUNK_OVERLAP)
    else:
        chunks = [text]
    
    # Generate embeddings for all chunks
    if embedder is None:
        raise HTTPException(
            status_code=503, 
            detail="Embedding service not initialized. Cannot process documents without embeddings."
        )
    
    try:
        embeddings = embedder.encode(chunks)
    except Exception as e:
        logger.error(f"Error generating embeddings: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate embeddings: {str(e)}"
        )
    
    # Prepare batch data
    batch_data = []
    for i, chunk_content in enumerate(chunks):
        chunk_id = f"{doc_id}_{i}" if len(chunks) > 1 else doc_id
        chunk_metadata = metadata.copy()
        chunk_metadata['chunk_index'] = i
        chunk_metadata['total_chunks'] = len(chunks)
        chunk_metadata['parent_id'] = doc_id
        chunk_metadata['text'] = chunk_content
        chunk_metadata['indexed_at'] = datetime.utcnow().isoformat()
        
        batch_data.append({
            'id': chunk_id,
            'vector': embeddings[i].tolist(),
            'payload': chunk_metadata
        })
    
    # Add to vector store
    vector_store.batch_add(batch_data)
    
    return len(chunks)

@app.get("/")
async def root():
    return {
        "service": "KubeRAG Universal Data Pipeline",
        "version": "1.0.0",
        "status": "healthy",
        "vector_store": VECTOR_STORE_TYPE,
        "embedding_model": EMBEDDING_MODEL,
        "chunk_size": CHUNK_SIZE,
        "chunk_overlap": CHUNK_OVERLAP
    }

@app.get("/health")
async def health_check():
    status = {
        "status": "healthy",
        "vector_store": vector_store is not None and vector_store.health_check(),
        "vector_store_type": VECTOR_STORE_TYPE,
        "embedding_model": EMBEDDING_MODEL
    }
    
    if vector_store:
        try:
            status["index_size"] = vector_store.count()
        except Exception as e:
            status["vector_store_error"] = str(e)
    
    return status

@app.get("/stores")
async def get_available_stores():
    """Get information about available vector stores"""
    return {
        "availability": list_available_stores(),
        "store_info": get_store_info(),
        "current_store": VECTOR_STORE_TYPE
    }

@app.post("/ingest/text", response_model=ProcessingResponse)
async def ingest_text(request: DocumentRequest):
    try:
        chunks_created = process_and_index_text(
            request.text,
            request.metadata,
            request.chunk,
            request.id
        )
        
        return ProcessingResponse(
            status="success",
            message="Document processed and indexed",
            documents_processed=1,
            chunks_created=chunks_created,
            index_size=vector_store.count(),
            vector_store_used=VECTOR_STORE_TYPE
        )
    except Exception as e:
        logger.error(f"Error ingesting text: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ingest/batch", response_model=ProcessingResponse)
async def ingest_batch(request: BatchDocumentRequest):
    try:
        total_chunks = 0
        
        for doc in request.documents:
            chunks = process_and_index_text(
                doc.text,
                doc.metadata,
                doc.chunk,
                doc.id
            )
            total_chunks += chunks
        
        return ProcessingResponse(
            status="success",
            message="Batch processed and indexed",
            documents_processed=len(request.documents),
            chunks_created=total_chunks,
            index_size=vector_store.count(),
            vector_store_used=VECTOR_STORE_TYPE
        )
    except Exception as e:
        logger.error(f"Error ingesting batch: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/embed", response_model=ProcessingResponse)
async def ingest_file(
    file: UploadFile = File(...),
    metadata: Optional[str] = Form("{}"),
    chunk: Optional[bool] = Form(True),
    chunk_config: Optional[str] = Form("{}")
):
    try:
        # Parse metadata and chunking config
        try:
            meta_dict = json.loads(metadata)
        except:
            meta_dict = {}
        
        try:
            chunk_cfg = json.loads(chunk_config)
        except:
            chunk_cfg = {}
        
        meta_dict['filename'] = file.filename
        meta_dict['content_type'] = file.content_type
        
        # Read file content
        content = await file.read()
        meta_dict['file_size'] = len(content)
        
        # Use universal file extractor with LlamaIndex
        try:
            text = extract_text_from_file(content, file.filename)
            if not text or len(text.strip()) < 10:
                raise ValueError("No readable text content extracted from file")
        except Exception as e:
            logger.error(f"Failed to extract text from {file.filename}: {e}")
            raise HTTPException(status_code=400, detail=f"Failed to extract text from file: {str(e)}")
        
        # Apply custom chunking configuration if provided
        if chunk_cfg:
            global CHUNK_SIZE, CHUNK_OVERLAP
            lock = _get_chunk_lock()
            async with lock:
                old_chunk_size, old_chunk_overlap = CHUNK_SIZE, CHUNK_OVERLAP
                CHUNK_SIZE = chunk_cfg.get('chunk_size', CHUNK_SIZE)
                CHUNK_OVERLAP = chunk_cfg.get('chunk_overlap', CHUNK_OVERLAP)
                try:
                    chunks_created = process_and_index_text(text, meta_dict, chunk)
                finally:
                    CHUNK_SIZE, CHUNK_OVERLAP = old_chunk_size, old_chunk_overlap
        else:
            chunks_created = process_and_index_text(text, meta_dict, chunk)
        
        return ProcessingResponse(
            status="success",
            message=f"File {file.filename} processed and indexed",
            documents_processed=1,
            chunks_created=chunks_created,
            index_size=vector_store.count(),
            vector_store_used=VECTOR_STORE_TYPE
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error ingesting file: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/configure/chunking")
async def configure_chunking(config: ChunkingConfig):
    """Configure text chunking parameters"""
    try:
        global CHUNK_SIZE, CHUNK_OVERLAP
        lock = _get_chunk_lock()
        async with lock:
            CHUNK_SIZE = config.chunk_size
            CHUNK_OVERLAP = config.chunk_overlap
        
        return {
            "status": "success",
            "message": "Chunking configuration updated",
            "new_config": {
                "chunk_size": CHUNK_SIZE,
                "chunk_overlap": CHUNK_OVERLAP,
                "method": config.method
            }
        }
    except Exception as e:
        logger.error(f"Error configuring chunking: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/configure/vector_store")
async def configure_vector_store(request: ConfigUpdateRequest):
    """Dynamically reconfigure the vector store"""
    try:
        global vector_store, VECTOR_STORE_TYPE
        
        # Create new vector store with provided configuration
        new_vector_store = get_vector_store(request.vector_store_type, **request.config)
        
        # Test the new configuration
        if not new_vector_store.health_check():
            raise Exception("New vector store configuration failed health check")
        
        # Replace the current vector store
        vector_store = new_vector_store
        VECTOR_STORE_TYPE = request.vector_store_type
        
        logger.info(f"Successfully reconfigured to use {request.vector_store_type}")
        
        return {
            "status": "success",
            "message": f"Vector store reconfigured to {request.vector_store_type}",
            "new_config": request.config
        }
        
    except Exception as e:
        logger.error(f"Error reconfiguring vector store: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats")
async def get_statistics():
    try:
        stats = {
            "service": "KubeRAG Universal Data Pipeline",
            "vector_store_type": VECTOR_STORE_TYPE,
            "embedding_model": EMBEDDING_MODEL,
            "embedding_dimension": embedder.get_sentence_embedding_dimension(),
            "chunk_size": CHUNK_SIZE,
            "chunk_overlap": CHUNK_OVERLAP
        }
        
        if vector_store:
            stats["index_size"] = vector_store.count()
            stats["vector_store_healthy"] = vector_store.health_check()
        
        return stats
        
    except Exception as e:
        logger.error(f"Error getting statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/documents/{document_id}")
async def delete_document(document_id: str):
    """Delete a document and all its chunks"""
    try:
        if not vector_store:
            raise HTTPException(status_code=503, detail="Vector store not initialized")
        
        # For chunked documents, we need to delete all chunks
        # This is a simplified implementation - in practice, you might want to
        # track parent-child relationships more carefully
        try:
            vector_store.delete(document_id)
            # Also try to delete chunks
            for i in range(100):  # Assume max 100 chunks per document
                try:
                    vector_store.delete(f"{document_id}_{i}")
                except:
                    break
        except Exception as e:
            logger.warning(f"Error deleting document {document_id}: {e}")
        
        return {
            "status": "success",
            "message": f"Document {document_id} and its chunks deleted",
            "vector_store": VECTOR_STORE_TYPE
        }
        
    except Exception as e:
        logger.error(f"Error deleting document: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/optimize")
async def optimize_index():
    """Optimize the vector store index if supported"""
    try:
        if not vector_store:
            raise HTTPException(status_code=503, detail="Vector store not initialized")
        
        # Check if vector store has optimize method
        if hasattr(vector_store, 'optimize'):
            vector_store.optimize()
            message = "Index optimized"
        else:
            message = "Optimization not supported for this vector store type"
        
        return {
            "status": "success",
            "message": message,
            "vector_store": VECTOR_STORE_TYPE
        }
        
    except Exception as e:
        logger.error(f"Error optimizing index: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Text embedding endpoint for Agent service
class TextEmbeddingRequest(BaseModel):
    text: str

class EmbeddingResponse(BaseModel):
    embedding: List[float]
    dimension: int
    model: str

@app.post("/api/embed/text", response_model=EmbeddingResponse)
async def generate_text_embedding(request: TextEmbeddingRequest):
    """Generate embedding for text input (used by Agent service)"""
    try:
        if not embedder:
            raise HTTPException(status_code=503, detail="Embedding model not available")
        
        # Generate embedding
        embedding = embedder.encode(request.text).tolist()
        
        return EmbeddingResponse(
            embedding=embedding,
            dimension=len(embedding),
            model=EMBEDDING_MODEL
        )
        
    except Exception as e:
        logger.error(f"Error generating text embedding: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
