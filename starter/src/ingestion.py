"""Read and normalize source data."""
import json
import re
import unicodedata
from pathlib import Path

from .models import DocumentPage


def load_pdf(path: Path, document_id: str, source: str) -> list[DocumentPage]:
    """Extract each physical page of a PDF, keeping its page number and source.

    Pages with no extractable text are recorded with empty text and a
    ``metadata["empty"] = True`` flag instead of being silently dropped.
    """
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    pages: list[DocumentPage] = []
    for i, page in enumerate(reader.pages, start=1):
        raw = page.extract_text() or ""
        text = normalize_text(raw)
        meta = {"empty": len(text) == 0}
        pages.append(
            DocumentPage(document_id=document_id, source=source, page=i, text=text, metadata=meta)
        )
    return pages


def load_text_units(path: Path) -> list[DocumentPage]:
    """Load pre-segmented plain-text units produced by scripts/build_corpus.py.

    Used for non-paginated sources: each JSON record is one independent unit
    of >=1500 normalized characters (see data/manifest.json for the rule).
    """
    records = json.loads(Path(path).read_text(encoding="utf-8"))
    pages: list[DocumentPage] = []
    for rec in records:
        text = normalize_text(rec["text"])
        meta = {
            "section": rec["section"],
            "mien": rec["mien"],
            "char_count": len(text),
            "empty": len(text) == 0,
        }
        pages.append(
            DocumentPage(
                document_id=rec["document_id"],
                source=rec["source"],
                page=rec["page"],
                text=text,
                metadata=meta,
            )
        )
    return pages


def normalize_text(text: str) -> str:
    """Normalize Unicode and collapse incidental whitespace, keeping paragraph breaks."""
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = "\n".join(line.strip() for line in text.split("\n"))
    return text.strip()
