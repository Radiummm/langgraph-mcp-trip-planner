"""RAG service backed by PostgreSQL + pgvector."""

import hashlib
import json
import math
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

import psycopg
from langchain_openai import OpenAIEmbeddings
from sentence_transformers import SentenceTransformer

from ..config import get_settings

_rag_service: Optional["TravelRAGService"] = None


@dataclass
class RetrievedChunk:
    """A retrieved travel knowledge chunk."""

    city: str
    source: str
    content: str
    score: float


def _safe_identifier(name: str) -> str:
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name):
        raise ValueError(f"非法表名: {name}")
    return name


def _vector_literal(values: List[float]) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in values) + "]"


def _normalize_city(city: str) -> str:
    city = city.strip()
    if city.endswith("市"):
        city = city[:-1]
    return city


class TravelRAGService:
    """Travel knowledge ingestion and retrieval using pgvector."""

    def __init__(self):
        self.settings = get_settings()
        self.table_name = _safe_identifier(self.settings.rag_table_name)
        self.embedding_dimensions = self.settings.rag_embedding_dimensions
        self.embedding_provider = self.settings.rag_embedding_provider.lower()
        self.embedding_model = self.settings.rag_embedding_model
        self._embeddings: Optional[OpenAIEmbeddings] = None
        self._sentence_transformer: Optional[SentenceTransformer] = None

    @property
    def enabled(self) -> bool:
        if not self.settings.database_url:
            return False
        if self.embedding_provider in {"local_hash", "sentence_transformer"}:
            return True
        return bool(self._embedding_api_key)

    @property
    def _embedding_api_key(self) -> str:
        return (
            os.getenv("EMBEDDING_API_KEY")
            or os.getenv("LLM_API_KEY")
            or os.getenv("OPENAI_API_KEY")
            or self.settings.openai_api_key
        )

    @property
    def _embedding_base_url(self) -> str:
        return (
            os.getenv("EMBEDDING_BASE_URL")
            or os.getenv("LLM_BASE_URL")
            or self.settings.openai_base_url
        )

    def _get_embeddings(self) -> OpenAIEmbeddings:
        if self._embeddings is None:
            self._embeddings = OpenAIEmbeddings(
                api_key=self._embedding_api_key,
                base_url=self._embedding_base_url,
                model=self.embedding_model,
            )
        return self._embeddings

    def _get_sentence_transformer(self) -> SentenceTransformer:
        if self._sentence_transformer is None:
            self._sentence_transformer = SentenceTransformer(self.embedding_model)
        return self._sentence_transformer

    def _tokenize(self, text: str) -> List[str]:
        normalized = text.lower()
        tokens = re.findall(r"[a-z0-9]+|[\u4e00-\u9fff]", normalized)
        tokens.extend(
            normalized[index : index + 2]
            for index in range(max(0, len(normalized) - 1))
            if any("\u4e00" <= char <= "\u9fff" for char in normalized[index : index + 2])
        )
        return tokens

    def _embed_local_hash(self, text: str) -> List[float]:
        vector = [0.0] * self.embedding_dimensions
        for token in self._tokenize(text):
            digest = hashlib.sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.embedding_dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[index] += sign

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]

    def _embed_documents(self, texts: List[str]) -> List[List[float]]:
        if self.embedding_provider == "local_hash":
            return [self._embed_local_hash(text) for text in texts]
        if self.embedding_provider == "sentence_transformer":
            vectors = self._get_sentence_transformer().encode(
                texts,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            return [vector.tolist() for vector in vectors]
        return self._get_embeddings().embed_documents(texts)

    def _embed_query(self, text: str) -> List[float]:
        if self.embedding_provider == "local_hash":
            return self._embed_local_hash(text)
        if self.embedding_provider == "sentence_transformer":
            vector = self._get_sentence_transformer().encode(
                text,
                normalize_embeddings=True,
                show_progress_bar=False,
            )
            return vector.tolist()
        return self._get_embeddings().embed_query(text)

    def _connect(self):
        if not self.settings.database_url:
            raise RuntimeError("DATABASE_URL未配置，无法使用PostgreSQL/pgvector RAG")
        return psycopg.connect(self.settings.database_url)

    def initialize_schema(self) -> None:
        """Create pgvector extension, table and index."""
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
                cur.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS {self.table_name} (
                        id BIGSERIAL PRIMARY KEY,
                        city TEXT NOT NULL,
                        source TEXT NOT NULL,
                        chunk_index INTEGER NOT NULL,
                        content TEXT NOT NULL,
                        content_hash TEXT NOT NULL UNIQUE,
                        metadata JSONB NOT NULL DEFAULT '{{}}'::jsonb,
                        embedding vector({self.embedding_dimensions}) NOT NULL,
                        created_at TIMESTAMPTZ NOT NULL DEFAULT now()
                    )
                    """
                )
                cur.execute(
                    f"""
                    CREATE INDEX IF NOT EXISTS idx_{self.table_name}_city
                    ON {self.table_name} (city)
                    """
                )
                cur.execute(
                    f"""
                    CREATE INDEX IF NOT EXISTS idx_{self.table_name}_embedding
                    ON {self.table_name}
                    USING hnsw (embedding vector_cosine_ops)
                    """
                )

    def split_text(self, text: str) -> List[str]:
        """Split markdown into overlapping chunks."""
        chunk_size = self.settings.rag_chunk_size
        overlap = min(self.settings.rag_chunk_overlap, max(0, chunk_size // 3))

        sections = re.split(r"(?=^##\s+)", text, flags=re.MULTILINE)
        chunks: List[str] = []
        for section in sections:
            section = section.strip()
            if not section:
                continue
            start = 0
            while start < len(section):
                end = min(start + chunk_size, len(section))
                chunk = section[start:end].strip()
                if chunk:
                    chunks.append(chunk)
                if end >= len(section):
                    break
                start = max(0, end - overlap)
        return chunks

    def _city_from_path(self, path: Path) -> str:
        city_map = {
            "beijing": "北京",
            "chengdu": "成都",
            "hangzhou": "杭州",
            "shanghai": "上海",
            "xian": "西安",
        }
        return city_map.get(path.stem.lower(), path.stem)

    def load_documents(self, data_dir: Path) -> List[dict]:
        documents: List[dict] = []
        for path in sorted(data_dir.glob("*.md")):
            text = path.read_text(encoding="utf-8")
            city = _normalize_city(self._city_from_path(path))
            for index, chunk in enumerate(self.split_text(text)):
                if len(chunk) < 80:
                    continue
                documents.append(
                    {
                        "city": city,
                        "source": str(path),
                        "chunk_index": index,
                        "content": chunk,
                        "content_hash": hashlib.sha256(
                            f"{path}:{index}:{chunk}".encode("utf-8")
                        ).hexdigest(),
                    }
                )
        return documents

    def clear_documents(self) -> None:
        """Remove all indexed travel chunks."""
        self.initialize_schema()
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(f"TRUNCATE TABLE {self.table_name} RESTART IDENTITY")

    def ingest_documents(self, documents: Iterable[dict], batch_size: int = 32) -> int:
        """Embed and upsert travel guide chunks."""
        docs = list(documents)
        if not docs:
            return 0
        if not self.enabled:
            raise RuntimeError("RAG未启用，请配置DATABASE_URL和Embedding API Key")

        self.initialize_schema()
        inserted = 0

        for start in range(0, len(docs), batch_size):
            batch = docs[start : start + batch_size]
            vectors = self._embed_documents([doc["content"] for doc in batch])
            with self._connect() as conn:
                with conn.cursor() as cur:
                    for doc, vector in zip(batch, vectors):
                        cur.execute(
                            f"""
                            INSERT INTO {self.table_name}
                                (city, source, chunk_index, content, content_hash, metadata, embedding)
                            VALUES
                                (%s, %s, %s, %s, %s, %s::jsonb, %s::vector)
                            ON CONFLICT (content_hash) DO UPDATE SET
                                city = EXCLUDED.city,
                                source = EXCLUDED.source,
                                chunk_index = EXCLUDED.chunk_index,
                                content = EXCLUDED.content,
                                metadata = EXCLUDED.metadata,
                                embedding = EXCLUDED.embedding
                            """,
                            (
                                doc["city"],
                                doc["source"],
                                doc["chunk_index"],
                                doc["content"],
                                doc["content_hash"],
                                json.dumps(
                                    {
                                        "source": doc["source"],
                                        "chunk_index": doc["chunk_index"],
                                    },
                                    ensure_ascii=False,
                                ),
                                _vector_literal(vector),
                            ),
                        )
                        inserted += 1
        return inserted

    def ingest_travel_guides(self, data_dir: Optional[Path] = None) -> int:
        root = Path(__file__).resolve().parents[2]
        guide_dir = data_dir or root / "data" / "travel_guides"
        return self.ingest_documents(self.load_documents(guide_dir))

    def retrieve(
        self,
        city: str,
        preferences: Optional[List[str]] = None,
        free_text_input: str = "",
        top_k: Optional[int] = None,
    ) -> List[RetrievedChunk]:
        """Retrieve travel guide chunks by vector similarity."""
        if not self.enabled:
            return []

        normalized_city = _normalize_city(city)
        query_parts = [normalized_city, "旅行规划"]
        if preferences:
            query_parts.extend(preferences)
        if free_text_input:
            query_parts.append(free_text_input)
        query = " ".join(query_parts)
        query_vector = self._embed_query(query)
        limit = top_k or self.settings.rag_top_k

        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT city, source, content, 1 - (embedding <=> %s::vector) AS score
                    FROM {self.table_name}
                    WHERE city = %s
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                    """,
                    (
                        _vector_literal(query_vector),
                        normalized_city,
                        _vector_literal(query_vector),
                        limit,
                    ),
                )
                rows = cur.fetchall()

        return [
            RetrievedChunk(city=row[0], source=row[1], content=row[2], score=float(row[3]))
            for row in rows
        ]

    def format_context(self, chunks: List[RetrievedChunk]) -> str:
        if not chunks:
            return ""
        parts = []
        for index, chunk in enumerate(chunks, start=1):
            parts.append(
                f"[知识片段{index} | 城市:{chunk.city} | 相似度:{chunk.score:.3f}]\n"
                f"{chunk.content}"
            )
        return "\n\n".join(parts)


def get_rag_service() -> TravelRAGService:
    global _rag_service
    if _rag_service is None:
        _rag_service = TravelRAGService()
    return _rag_service
