"""LanceDB vector store implementation supporting embedded and remote modes."""

from __future__ import annotations

import json
import logging
import os
import tempfile
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List

import httpx

from .base import BaseVectorStore, VectorSearchResult

logger = logging.getLogger(__name__)


@dataclass
class RemoteResponse:
    status: int
    json: Dict[str, Any]


class LanceDBVectorStore(BaseVectorStore):
    """LanceDB implementation.

    When `host` is provided in the configuration a remote LanceDB service is
    used. Otherwise, the store operates in embedded mode using the local
    LanceDB Python library.
    """

    def __init__(self, **kwargs):
        self.uri = kwargs.get("uri", tempfile.mkdtemp())
        self.table_name = kwargs.get("table_name", "documents")
        self.dimension = kwargs.get("dimension", 768)
        self.metric = kwargs.get("metric", "cosine")
        self.host = kwargs.get("host")
        self.port = int(kwargs.get("port", 8080))

        self.use_remote = bool(self.host)
        self.db = None
        self.table = None
        self.base_url = None

        super().__init__(**kwargs)

    def initialize(self):
        """Initialise LanceDB connection."""
        try:
            if self.use_remote and not self.host:
                release_name = os.getenv("HELM_RELEASE_NAME")
                if release_name:
                    self.host = f"{release_name}-lancedb-service"
                else:
                    self.use_remote = False

            if self.use_remote:
                scheme = "http"
                self.base_url = f"{scheme}://{self.host}:{self.port}"
                health_url = f"{self.base_url}/health"
                with httpx.Client(timeout=5) as client:
                    response = client.get(health_url)
                    response.raise_for_status()
                logger.info(
                    "Connected to remote LanceDB (%s) table=%s",
                    self.base_url,
                    self.table_name,
                )
                return

            import lancedb  # Local import so containers without lancedb can still run remote mode

            self.db = lancedb.connect(self.uri)
            try:
                self.table = self.db.open_table(self.table_name)
                logger.info("Opened existing LanceDB table: %s", self.table_name)
            except Exception:
                self._create_table()
                logger.info("Created new LanceDB table: %s", self.table_name)

            logger.info("LanceDB vector store initialised in embedded mode")
        except Exception as exc:
            logger.error("Failed to initialise LanceDB: %s", exc)
            raise

    def _create_table(self):
        import lancedb  # noqa: F401
        import numpy as np
        import pandas as pd

        initial = pd.DataFrame({
            "id": [str(uuid.uuid4())],
            "vector": [np.zeros(self.dimension).tolist()],
            "text": [""],
            "metadata": ["{}"],
        })

        self.table = self.db.create_table(self.table_name, initial, mode="overwrite")
        self.table.create_index(
            "vector",
            index_type="ivf_pq",
            metric=self.metric,
            num_partitions=1,
            num_sub_vectors=4,
        )
        self.table.delete(f"id = '{initial['id'].iloc[0]}'")

    # ------------------------------------------------------------------
    # Remote helpers
    # ------------------------------------------------------------------
    def _remote_post(self, path: str, payload: Dict, timeout: int = 10) -> RemoteResponse:
        with httpx.Client(timeout=timeout) as client:
            response = client.post(f"{self.base_url}{path}", json=payload)
            response.raise_for_status()
            return RemoteResponse(response.status_code, response.json())

    def _remote_get(self, path: str, timeout: int = 5) -> RemoteResponse:
        with httpx.Client(timeout=timeout) as client:
            response = client.get(f"{self.base_url}{path}")
            response.raise_for_status()
            return RemoteResponse(response.status_code, response.json())

    def _remote_delete(self, path: str, timeout: int = 5) -> RemoteResponse:
        with httpx.Client(timeout=timeout) as client:
            response = client.delete(f"{self.base_url}{path}")
            response.raise_for_status()
            return RemoteResponse(response.status_code, response.json())

    # ------------------------------------------------------------------
    # CRUD operations
    # ------------------------------------------------------------------
    def add(self, id: str, vector: List[float], payload: Dict[str, Any]):
        try:
            if self.use_remote:
                self._remote_post(
                    "/add",
                    {
                        "id": str(id),
                        "vector": vector,
                        "payload": payload,
                    },
                )
                return

            import pandas as pd

            data = pd.DataFrame(
                {
                    "id": [id],
                    "vector": [vector],
                    "text": [payload.get("text", "")],
                    "metadata": [json.dumps(payload)],
                }
            )

            try:
                existing = self.table.search().where(f"id = '{id}'").limit(1).to_pandas()
                if len(existing) > 0:
                    self.table.delete(f"id = '{id}'")
            except Exception:
                pass

            self.table.add(data)
        except Exception as exc:
            logger.error("Failed to add document to LanceDB: %s", exc)
            raise

    def search(self, query_vector: List[float], limit: int = 5) -> List[VectorSearchResult]:
        try:
            if self.use_remote:
                result = self._remote_post(
                    "/search",
                    {
                        "vector": query_vector,
                        "limit": limit,
                    },
                ).json
                return [
                    VectorSearchResult(
                        id=item.get("id"),
                        text=item.get("text", ""),
                        score=item.get("score", 0.0),
                        metadata=item.get("metadata", {}),
                    )
                    for item in result.get("results", [])
                ]

            if not self.table:
                return []

            import pandas as pd

            results = (
                self.table.search(query_vector)
                .metric(self.metric)
                .limit(limit)
                .to_pandas()
            )

            matched: List[VectorSearchResult] = []
            for _, row in results.iterrows():
                try:
                    metadata = json.loads(row.get("metadata", "{}"))
                except Exception:
                    metadata = {}
                score = 1.0 - row.get("_distance", 1.0)
                matched.append(
                    VectorSearchResult(
                        id=row.get("id"),
                        text=row.get("text", ""),
                        score=score,
                        metadata=metadata,
                    )
                )
            return matched
        except Exception as exc:
            logger.error("Failed to search in LanceDB: %s", exc)
            return []

    def delete(self, id: str):
        try:
            if self.use_remote:
                self._remote_delete(f"/documents/{id}")
                return

            if self.table:
                self.table.delete(f"id = '{id}'")
        except Exception as exc:
            logger.error("Failed to delete document from LanceDB: %s", exc)
            raise

    def update(self, id: str, vector: List[float], payload: Dict[str, Any]):
        try:
            self.delete(id)
            self.add(id, vector, payload)
        except Exception as exc:
            logger.error("Failed to update document in LanceDB: %s", exc)
            raise

    def count(self) -> int:
        try:
            if self.use_remote:
                return self._remote_get("/count").json.get("count", 0)

            if not self.table:
                return 0

            import pandas as pd

            result = self.table.search().limit(1_000_000).to_pandas()
            return len(result)
        except Exception as exc:
            logger.error("Failed to count documents in LanceDB: %s", exc)
            return 0

    def health_check(self) -> bool:
        try:
            if self.use_remote:
                health = self._remote_get("/health").json
                return health.get("status") == "healthy"

            if not self.table:
                return False

            import numpy as np

            self.table.search(np.zeros(self.dimension).tolist()).limit(1).to_pandas()
            return True
        except Exception as exc:
            logger.error("LanceDB health check failed: %s", exc)
            return False

    def batch_add(self, vectors: List[Dict[str, Any]]):
        try:
            if not vectors:
                return

            if self.use_remote:
                self._remote_post(
                    "/batch_add",
                    {
                        "items": [
                            {
                                "id": item["id"],
                                "vector": item["vector"],
                                "payload": item["payload"],
                            }
                            for item in vectors
                        ]
                    },
                    timeout=30,
                )
                return

            import pandas as pd

            rows = []
            for vector_data in vectors:
                rows.append(
                    {
                        "id": vector_data["id"],
                        "vector": vector_data["vector"],
                        "text": vector_data["payload"].get("text", ""),
                        "metadata": json.dumps(vector_data["payload"]),
                    }
                )

            df = pd.DataFrame(rows)
            for vector_data in vectors:
                try:
                    self.table.delete(f"id = '{vector_data['id']}'")
                except Exception:
                    pass

            self.table.add(df)
        except Exception as exc:
            logger.error("Failed to batch add documents to LanceDB: %s", exc)
            raise

    def optimize(self):
        if self.use_remote:
            try:
                self._remote_post("/optimize", {})
            except Exception as exc:
                logger.error("Failed to optimise remote LanceDB: %s", exc)
            return

        try:
            if self.table:
                self.table.compact_files()
        except Exception as exc:
            logger.error("Failed to optimise LanceDB table: %s", exc)
