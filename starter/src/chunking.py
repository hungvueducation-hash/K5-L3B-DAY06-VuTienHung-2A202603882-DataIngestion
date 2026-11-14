"""Fixed-size and structure-aware (paragraph) chunking strategies."""
import re

from .models import Chunk, DocumentPage


def fixed_size(page: DocumentPage, size: int, overlap: int) -> list[Chunk]:
    """Split text into overlapping fixed-size windows, retaining page metadata."""
    text = page.text
    if not text:
        return []
    step = size - overlap
    if step <= 0:
        raise ValueError("overlap must be smaller than size")

    chunks: list[Chunk] = []
    start = 0
    idx = 0
    n = len(text)
    while start < n:
        end = min(start + size, n)
        piece = text[start:end].strip()
        if piece:
            chunk_id = f"{page.document_id}:p{page.page}:fixed:{idx}"
            chunks.append(
                Chunk(
                    chunk_id=chunk_id,
                    document_id=page.document_id,
                    source=page.source,
                    page=page.page,
                    text=piece,
                    metadata={**page.metadata, "chunk_method": "fixed_size", "size": size, "overlap": overlap},
                )
            )
            idx += 1
        if end == n:
            break
        start += step
    return chunks


def by_paragraph(page: DocumentPage, max_size: int) -> list[Chunk]:
    """Group paragraphs sequentially, splitting any paragraph bigger than max_size."""
    text = page.text
    if not text:
        return []

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: list[Chunk] = []
    buf: list[str] = []
    buf_len = 0
    idx = 0

    def flush() -> None:
        nonlocal buf, buf_len, idx
        if not buf:
            return
        piece = "\n\n".join(buf)
        chunk_id = f"{page.document_id}:p{page.page}:para:{idx}"
        chunks.append(
            Chunk(
                chunk_id=chunk_id,
                document_id=page.document_id,
                source=page.source,
                page=page.page,
                text=piece,
                metadata={**page.metadata, "chunk_method": "by_paragraph", "max_size": max_size},
            )
        )
        idx += 1
        buf, buf_len = [], 0

    for para in paragraphs:
        if len(para) > max_size:
            flush()
            for start in range(0, len(para), max_size):
                sub = para[start : start + max_size].strip()
                if sub:
                    buf = [sub]
                    buf_len = len(sub)
                    flush()
            continue

        if buf_len + len(para) + 2 > max_size and buf:
            flush()
        buf.append(para)
        buf_len += len(para) + 2

    flush()
    return chunks
