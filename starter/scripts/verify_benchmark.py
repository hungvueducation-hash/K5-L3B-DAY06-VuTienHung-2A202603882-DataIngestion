"""Verify every benchmark question's evidence_quote and filter exist on its gold page."""
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
CORPUS = ROOT / "starter" / "data" / "corpus.json"
QUESTIONS = ROOT / "benchmark" / "questions.json"


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def main() -> None:
    records = json.loads(CORPUS.read_text(encoding="utf-8"))
    pages = {p["page"]: p["text"] for p in records}
    meta = {p["page"]: p for p in records}
    questions = json.loads(QUESTIONS.read_text(encoding="utf-8"))

    splits = {"dev": 0, "test": 0}
    filter_qs = {"dev": 0, "test": 0}
    failures = []
    for q in questions:
        page_text = pages.get(q["gold_page"])
        if page_text is None:
            failures.append(f"{q['id']}: gold_page {q['gold_page']} not in corpus")
            continue
        if q["gold_source_id"] != meta[q["gold_page"]]["document_id"]:
            failures.append(f"{q['id']}: gold_source_id mismatch with gold page's actual document_id")
        if normalize(q["evidence_quote"]) not in normalize(page_text):
            failures.append(f"{q['id']}: evidence_quote not found verbatim on page {q['gold_page']}")
        if q.get("filter"):
            for key, value in q["filter"].items():
                actual = meta[q["gold_page"]].get(key)
                if actual != value:
                    failures.append(
                        f"{q['id']}: filter {key}={value!r} mismatch with gold page's actual {key}={actual!r}"
                    )
        splits[q["split"]] += 1
        if q.get("filter"):
            filter_qs[q["split"]] += 1

    print(f"Total questions: {len(questions)}")
    print(f"Dev/Test split: {splits}")
    print(f"Filter questions by split: {filter_qs}")
    if failures:
        print("FAILURES:")
        for f in failures:
            print(" -", f)
        raise SystemExit(1)
    print("All evidence quotes and filters verified OK.")


if __name__ == "__main__":
    main()
