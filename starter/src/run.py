"""Day 06 pipeline: build strategies A/B/C, embed, store, run the benchmark."""
import json
import os
import time
from pathlib import Path

from dotenv import load_dotenv

from .chunking import by_paragraph, fixed_size
from .embeddings import MyEmbedder
from .evaluation import evaluate_query, summarize
from .ingestion import load_text_units
from .models import Chunk
from .store import PgVectorStore

ROOT = Path(__file__).resolve().parent.parent.parent  # Lab6/
STARTER = ROOT / "starter"
CORPUS_PATH = STARTER / "data" / "corpus.json"
QUESTIONS_PATH = ROOT / "benchmark" / "questions.json"
RESULTS_DIR = STARTER / "results"

MIN_CONTENT_PAGES = 30
FIXED_SIZE, FIXED_OVERLAP = 500, 50
PARAGRAPH_MAX_SIZE = 500
TOP_K = 3


def build_strategy_chunks(pages, strategy: str) -> list[Chunk]:
    chunks: list[Chunk] = []
    for page in pages:
        if strategy == "a":
            chunks.extend(fixed_size(page, size=FIXED_SIZE, overlap=FIXED_OVERLAP))
        else:  # b and c share the same chunking; c only differs at search time (filter)
            chunks.extend(by_paragraph(page, max_size=PARAGRAPH_MAX_SIZE))
    return chunks


def main() -> None:
    load_dotenv(STARTER / ".env")
    database_url = os.environ["DATABASE_URL"]

    pages = load_text_units(CORPUS_PATH)
    if len(pages) < MIN_CONTENT_PAGES:
        raise ValueError(f"corpus has only {len(pages)} units, need >= {MIN_CONTENT_PAGES}")

    questions = json.loads(QUESTIONS_PATH.read_text(encoding="utf-8"))

    embedder = MyEmbedder()
    store = PgVectorStore(database_url, dimensions=embedder.dimensions)
    store.create_schema()

    run_meta = {
        "embedding_model": embedder.model_name,
        "dimensions": embedder.dimensions,
        "vector_store": "pgvector 0.8.7 (PostgreSQL 16, Docker, metric=cosine)",
        "corpus_units": len(pages),
        "strategies": {},
    }

    configs = {
        "a": {"chunking": "fixed_size(500,50)", "filter_on_search": False},
        "b": {"chunking": "by_paragraph(max=500)", "filter_on_search": False},
        "c": {"chunking": "by_paragraph(max=500)", "filter_on_search": True},
    }

    all_traces = {}
    for strategy, cfg in configs.items():
        t0 = time.time()
        chunks = build_strategy_chunks(pages, strategy)
        texts = [c.text for c in chunks]
        vectors = embedder.embed_documents(texts)
        store.upsert(strategy, chunks, vectors)
        ingest_seconds = time.time() - t0

        lengths = [len(c.text) for c in chunks]
        run_meta["strategies"][strategy] = {
            **cfg,
            "n_chunks": len(chunks),
            "total_chars": sum(lengths),
            "min_len": min(lengths) if lengths else 0,
            "max_len": max(lengths) if lengths else 0,
            "avg_len": round(sum(lengths) / len(lengths), 1) if lengths else 0,
            "ingest_seconds": round(ingest_seconds, 2),
            "embedding_cost_usd": 0.0,
            "stored_count_after_reload_check": store.count(strategy),
        }

        traces = []
        for q in questions:
            query_vector = embedder.embed_query(q["question"])
            filters = None
            if cfg["filter_on_search"] and q.get("filter"):
                filters = q["filter"]
            hits = store.search(strategy, query_vector, top_k=TOP_K, filters=filters)
            traces.append(evaluate_query(q, hits))
        all_traces[strategy] = traces

    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    (RESULTS_DIR / "run_meta.json").write_text(
        json.dumps(run_meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    summary = {}
    for strategy, traces in all_traces.items():
        (RESULTS_DIR / f"trace_{strategy}.json").write_text(
            json.dumps(traces, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        summary[strategy] = summarize(traces)

    (RESULTS_DIR / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(json.dumps({"run_meta": run_meta, "summary": summary}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
