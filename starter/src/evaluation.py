"""Evaluate retrieved evidence and preserve per-query traces."""
import re
import unicodedata
from typing import Any


def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).lower()
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _is_hit(question: dict[str, Any], hit: dict[str, Any]) -> bool:
    """A hit requires the gold source/page AND the evidence quote present in the chunk."""
    if hit["document_id"] != question["gold_source_id"]:
        return False
    if hit["page"] != question["gold_page"]:
        return False
    evidence = _normalize(question["evidence_quote"])
    return evidence in _normalize(hit["text"])


def evaluate_query(question: dict[str, Any], hits: list[dict[str, Any]]) -> dict[str, Any]:
    """Check source/page + evidence; return a full trace with hit@1 and hit@3 flags."""
    hit_flags = [_is_hit(question, h) for h in hits]
    hit_at_1 = bool(hit_flags[0]) if hit_flags else False
    hit_at_3 = any(hit_flags[:3])

    return {
        "question_id": question["id"],
        "split": question["split"],
        "question": question["question"],
        "gold_source_id": question["gold_source_id"],
        "gold_page": question["gold_page"],
        "evidence_quote": question["evidence_quote"],
        "filter": question.get("filter"),
        "top_k": [
            {
                "rank": i + 1,
                "chunk_id": h["chunk_id"],
                "document_id": h["document_id"],
                "page": h["page"],
                "section": h.get("section"),
                "mien": h.get("mien"),
                "score": h["score"],
                "text_preview": h["text"][:300],
                "is_hit": hit_flags[i],
            }
            for i, h in enumerate(hits)
        ],
        "hit_at_1": hit_at_1,
        "hit_at_3": hit_at_3,
    }


def summarize(traces: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate Hit@1 and Evidence Hit@3 by split, reporting numerator/denominator."""
    summary: dict[str, Any] = {}
    for split in sorted({t["split"] for t in traces}):
        split_traces = [t for t in traces if t["split"] == split]
        n = len(split_traces)
        hit1 = sum(1 for t in split_traces if t["hit_at_1"])
        hit3 = sum(1 for t in split_traces if t["hit_at_3"])
        summary[split] = {
            "n": n,
            "hit_at_1": f"{hit1}/{n}",
            "hit_at_1_rate": round(hit1 / n, 4) if n else None,
            "hit_at_3": f"{hit3}/{n}",
            "hit_at_3_rate": round(hit3 / n, 4) if n else None,
        }

    filter_traces = [t for t in traces if t.get("filter")]
    if filter_traces:
        compliant = 0
        for t in filter_traces:
            flt = t["filter"]
            key, value = next(iter(flt.items()))
            ok = all(hit.get(key) == value for hit in t["top_k"]) if t["top_k"] else False
            compliant += int(ok)
        summary["filter_compliance"] = f"{compliant}/{len(filter_traces)}"
    else:
        summary["filter_compliance"] = "N/A (no filter questions in this set)"

    return summary
