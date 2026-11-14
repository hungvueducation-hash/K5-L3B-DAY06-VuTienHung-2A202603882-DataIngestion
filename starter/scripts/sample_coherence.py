"""Pull, for the first 10 sorted source page IDs, the chunk(s) in each strategy
that cover that page -- for manual coherence scoring (GUIDE.md section 4.2).
Chosen BEFORE looking at any score, per the rule: fixed positions = pages 1-10.
"""
import json
import os
from pathlib import Path

import psycopg
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

PAGES = list(range(1, 11))
OUT = ROOT / "results" / "coherence_sample.json"


def main() -> None:
    database_url = os.environ["DATABASE_URL"]
    sample = {}
    with psycopg.connect(database_url) as conn:
        for strategy in ["a", "b", "c"]:
            table = f"chunks_{strategy}"
            rows = []
            for page in PAGES:
                recs = conn.execute(
                    f"SELECT chunk_id, page, text FROM {table} WHERE page = %s ORDER BY chunk_id",
                    (page,),
                ).fetchall()
                rows.append(
                    {
                        "page": page,
                        "chunks": [{"chunk_id": r[0], "text": r[2]} for r in recs],
                    }
                )
            sample[strategy] = rows
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(sample, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
