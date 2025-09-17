#!/usr/bin/env python3
"""Simple LanceDB REST server used by KubeRAG deployments."""

import json
import logging
import os
from typing import Any, Dict, List

import lancedb
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("lancedb-server")

app = FastAPI(title="LanceDB Vector Store Server")

LANCEDB_PATH = os.getenv("LANCEDB_PATH", "/data/lancedb")
TABLE_NAME = os.getenv("LANCEDB_TABLE", "documents")
DIMENSION = int(os.getenv("LANCEDB_DIMENSION", "768"))
METRIC = os.getenv("LANCEDB_METRIC", "cosine")

DB = None
TABLE = None


class VectorPayload(BaseModel):
    id: str
    vector: List[float]
    payload: Dict[str, Any]


class BatchPayload(BaseModel):
    items: List[VectorPayload]


class SearchPayload(BaseModel):
    vector: List[float]
    limit: int = 5


class SearchResponse(BaseModel):
    results: List[Dict[str, Any]]


def _connect():
    global DB, TABLE

    os.makedirs(LANCEDB_PATH, exist_ok=True)
    DB = lancedb.connect(LANCEDB_PATH)

    try:
        TABLE = DB.open_table(TABLE_NAME)
        logger.info("Opened LanceDB table %s", TABLE_NAME)
    except Exception:
        logger.info("Creating LanceDB table %s", TABLE_NAME)
        initial = pd.DataFrame(
            {
                "id": ["bootstrap"],
                "vector": [np.zeros(DIMENSION).tolist()],
                "text": [""],
                "metadata": ["{}"],
            }
        )
        TABLE = DB.create_table(TABLE_NAME, initial, mode="overwrite")
        TABLE.create_index(
            "vector",
            index_type="ivf_pq",
            metric=METRIC,
            num_partitions=1,
            num_sub_vectors=4,
        )
        TABLE.delete("id = 'bootstrap'")
        logger.info("Created table %s", TABLE_NAME)


@app.on_event("startup")
async def startup_event():
    _connect()


@app.get("/health")
async def health():
    try:
        TABLE.search(np.zeros(DIMENSION).tolist()).limit(1).to_pandas()
        return {"status": "healthy", "table": TABLE_NAME}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/add")
async def add(payload: VectorPayload):
    try:
        data = pd.DataFrame(
            {
                "id": [payload.id],
                "vector": [payload.vector],
                "text": [payload.payload.get("text", "")],
                "metadata": [json.dumps(payload.payload)],
            }
        )

        TABLE.delete(f"id = '{payload.id}'")
    except Exception:
        pass

    try:
        TABLE.add(data)
        return {"status": "success"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/batch_add")
async def batch_add(payload: BatchPayload):
    if not payload.items:
        return {"status": "success", "count": 0}

    rows = []
    for item in payload.items:
        rows.append(
            {
                "id": item.id,
                "vector": item.vector,
                "text": item.payload.get("text", ""),
                "metadata": json.dumps(item.payload),
            }
        )

    df = pd.DataFrame(rows)

    for item in payload.items:
        try:
            TABLE.delete(f"id = '{item.id}'")
        except Exception:
            pass

    try:
        TABLE.add(df)
        return {"status": "success", "count": len(payload.items)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/search", response_model=SearchResponse)
async def search(payload: SearchPayload):
    try:
        results = (
            TABLE.search(payload.vector)
            .metric(METRIC)
            .limit(payload.limit)
            .to_pandas()
        )

        formatted: List[Dict[str, any]] = []
        for _, row in results.iterrows():
            try:
                metadata = json.loads(row.get("metadata", "{}"))
            except Exception:
                metadata = {}

            formatted.append(
                {
                    "id": row.get("id"),
                    "text": row.get("text", ""),
                    "score": 1.0 - row.get("_distance", 1.0),
                    "metadata": metadata,
                }
            )

        return SearchResponse(results=formatted)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/count")
async def count():
    try:
        total = TABLE.search().limit(1_000_000).to_pandas()
        return {"count": len(total)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    try:
        TABLE.delete(f"id = '{doc_id}'")
        return {"status": "success"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/optimize")
async def optimize():
    try:
        TABLE.compact_files()
        return {"status": "success"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8080")))
