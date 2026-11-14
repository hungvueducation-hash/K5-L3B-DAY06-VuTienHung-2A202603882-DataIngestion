"""Fetch plain-text extracts of a few Vietnamese Wikipedia articles (CC BY-SA 4.0 /
GFDL, redistribution with attribution permitted) and save raw JSON per title.
"""
import json
import time
import urllib.parse
import urllib.request
from pathlib import Path

OUT_DIR = Path(__file__).resolve().parent.parent / "data" / "wiki_raw"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# (title, slug, region)
ARTICLES = [
    ("Sa Pa", "sa-pa", "Bắc"),
    ("Nha Trang", "nha-trang", "Trung"),
    ("Vũng Tàu", "vung-tau", "Nam"),
    ("Phú Quốc", "phu-quoc", "Nam"),
]

API = "https://vi.wikipedia.org/w/api.php"


def fetch(title: str) -> dict:
    params = {
        "action": "query",
        "prop": "extracts",
        "explaintext": "1",
        "format": "json",
        "titles": title,
    }
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "day6-lab-student-script/1.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def main() -> None:
    for title, slug, region in ARTICLES:
        data = fetch(title)
        page = next(iter(data["query"]["pages"].values()))
        extract = page.get("extract", "")
        out = {
            "title": page.get("title", title),
            "slug": slug,
            "region": region,
            "url": f"https://vi.wikipedia.org/wiki/{urllib.parse.quote(page.get('title', title))}",
            "extract": extract,
            "char_count": len(extract),
        }
        (OUT_DIR / f"{slug}.json").write_text(
            json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(f"{slug}: {len(extract)} chars")
        time.sleep(0.5)


if __name__ == "__main__":
    main()
