"""Store and search vectors using PostgreSQL + pgvector.

Each strategy (A/B/C) is kept in its own table (`chunks_<strategy>`) so the
three configurations never share rows, and metadata filters are applied in
SQL with parameterized values. Distance metric is cosine (`<=>`), matching
the normalized document/query vectors produced by MyEmbedder.
"""
from typing import Any

import psycopg

from .models import Chunk

_VALID_STRATEGY = {"a", "b", "c"}


def _table(strategy: str) -> str:
    strategy = strategy.lower()
    if strategy not in _VALID_STRATEGY:
        raise ValueError(f"unknown strategy: {strategy!r}")
    return f"chunks_{strategy}"


class PgVectorStore:
    def __init__(self, database_url: str, dimensions: int) -> None:
        self.database_url = database_url
        self.dimensions = dimensions
        # Fail fast if the DB is unreachable instead of silently falling back.
        with psycopg.connect(self.database_url, connect_timeout=5) as conn:
            conn.execute("SELECT 1")

    def create_schema(self) -> None:
        with psycopg.connect(self.database_url) as conn:
            for strategy in sorted(_VALID_STRATEGY):
                table = _table(strategy)
                conn.execute(
                    f"""
                    CREATE TABLE IF NOT EXISTS {table} (
                        chunk_id TEXT PRIMARY KEY,
                        document_id TEXT NOT NULL,
                        source TEXT NOT NULL,
                        page INTEGER NOT NULL,
                        section TEXT,
                        mien TEXT,
                        text TEXT NOT NULL,
                        metadata JSONB NOT NULL DEFAULT '{{}}'::jsonb,
                        embedding VECTOR({self.dimensions}) NOT NULL
                    )
                    """
                )
                conn.execute(
                    f"CREATE INDEX IF NOT EXISTS {table}_section_idx ON {table} (section)"
                )
                conn.execute(
                    f"CREATE INDEX IF NOT EXISTS {table}_mien_idx ON {table} (mien)"
                )
            conn.commit()

    def upsert(self, strategy: str, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        if len(chunks) != len(vectors):
            raise ValueError("chunks and vectors length mismatch")
        for v in vectors:
            if len(v) != self.dimensions:
                raise ValueError(f"vector has {len(v)} dims, expected {self.dimensions}")

        table = _table(strategy)
        with psycopg.connect(self.database_url) as conn:
            doc_ids = sorted({c.document_id for c in chunks})
            if doc_ids:
                conn.execute(
                    f"DELETE FROM {table} WHERE document_id = ANY(%s)", (doc_ids,)
                )
            for chunk, vector in zip(chunks, vectors):
                section = chunk.metadata.get("section")
                mien = chunk.metadata.get("mien")
                conn.execute(
                    f"""
                    INSERT INTO {table}
                        (chunk_id, document_id, source, page, section, mien, text, metadata, embedding)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (chunk_id) DO UPDATE SET
                        document_id = EXCLUDED.document_id,
                        source = EXCLUDED.source,
                        page = EXCLUDED.page,
                        section = EXCLUDED.section,
                        mien = EXCLUDED.mien,
                        text = EXCLUDED.text,
                        metadata = EXCLUDED.metadata,
                        embedding = EXCLUDED.embedding
                    """,
                    (
                        chunk.chunk_id,
                        chunk.document_id,
                        chunk.source,
                        chunk.page,
                        section,
                        mien,
                        chunk.text,
                        psycopg.types.json.Json(chunk.metadata),
                        str(vector),
                    ),
                )
            conn.commit()

    def count(self, strategy: str) -> int:
        table = _table(strategy)
        with psycopg.connect(self.database_url) as conn:
            return conn.execute(f"SELECT count(*) FROM {table}").fetchone()[0]

    def search(
        self,
        strategy: str,
        query_vector: list[float],
        top_k: int = 3,
        filters: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        table = _table(strategy)
        where_sql = ""
        params: list[Any] = [str(query_vector)]
        if filters:
            clauses = []
            for key, value in filters.items():
                if key not in {"section", "mien"}:
                    raise ValueError(f"unsupported filter field: {key!r}")
                clauses.append(f"{key} = %s")
                params.append(value)
            where_sql = "WHERE " + " AND ".join(clauses)
        params.extend([str(query_vector), top_k])

        sql = f"""
            SELECT chunk_id, text, document_id, source, page, section, mien, metadata,
                   embedding <=> %s AS distance
            FROM {table}
            {where_sql}
            ORDER BY embedding <=> %s
            LIMIT %s
        """
        with psycopg.connect(self.database_url) as conn:
            rows = conn.execute(sql, params).fetchall()

        return [
            {
                "chunk_id": r[0],
                "text": r[1],
                "document_id": r[2],
                "source": r[3],
                "page": r[4],
                "section": r[5],
                "mien": r[6],
                "metadata": r[7],
                "score": 1 - float(r[8]),  # cosine similarity
            }
            for r in rows
        ]
