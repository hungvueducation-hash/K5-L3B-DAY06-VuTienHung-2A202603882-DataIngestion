"""Demo retrieval chatbot UI for the Day 06 lab (NOT required by the assignment).

Not an LLM-answer chatbot: it is a thin UI over the real pipeline (src.embeddings
+ src.store) so you can type a question, pick strategy A/B/C, and see the actual
top-3 retrieved chunks with page/section/mien/score -- the same "grounding"
evidence the benchmark measures, just interactive instead of batch.
"""
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src.embeddings import MyEmbedder
from src.store import PgVectorStore
from webapp.answer import is_configured, synthesize_answer

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

app = FastAPI(title="Day 06 Retrieval Chatbot (demo)")

_embedder: MyEmbedder | None = None
_store: PgVectorStore | None = None


def get_embedder() -> MyEmbedder:
    global _embedder
    if _embedder is None:
        _embedder = MyEmbedder()
    return _embedder


def get_store() -> PgVectorStore:
    global _store
    if _store is None:
        _store = PgVectorStore(os.environ["DATABASE_URL"], dimensions=get_embedder().dimensions)
    return _store


class AskRequest(BaseModel):
    question: str
    strategy: str = "c"
    mien: str | None = None
    top_k: int = 3
    generate_answer: bool = False


@app.post("/api/ask")
def ask(req: AskRequest):
    embedder = get_embedder()
    store = get_store()
    query_vector = embedder.embed_query(req.question)
    filters = {"mien": req.mien} if req.mien else None
    hits = store.search(req.strategy, query_vector, top_k=req.top_k, filters=filters)

    answer = None
    answer_error = None
    if req.generate_answer:
        if not is_configured():
            answer_error = "OPENAI_API_KEY chưa được cấu hình trong starter/.env"
        else:
            try:
                answer = synthesize_answer(req.question, hits)
            except Exception as exc:  # surface to UI instead of silently failing
                answer_error = str(exc)

    return {
        "question": req.question,
        "strategy": req.strategy,
        "filter": filters,
        "hits": hits,
        "answer": answer,
        "answer_error": answer_error,
    }


@app.get("/api/llm_status")
def llm_status():
    return {"configured": is_configured()}


@app.get("/api/health")
def health():
    get_store()
    return {"status": "ok", "model": get_embedder().model_name}


STATIC_DIR = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
def index():
    return FileResponse(str(STATIC_DIR / "index.html"))
