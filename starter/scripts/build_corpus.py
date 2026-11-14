"""Build the Day 06 corpus from 4 Vietnamese Wikipedia articles (Sa Pa, Nha Trang,
Vung Tau, Phu Quoc) fetched by scripts/fetch_vn_wiki.py.

Splits each article's content into source units of at least 1500 normalized
characters each (GUIDE.md's rule for non-paginated text/HTML sources). Each
unit keeps its top-level Wikipedia heading (`== ... ==`) as `section`, and the
article's region as `mien` -- the metadata filter field, with 2 distinct
values (Bac/Trung/Nam collapsed to 2 groups is not needed: 3 real values are
present: Bac, Trung, Nam).
"""
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WIKI_RAW = ROOT / "data" / "wiki_raw"
OUT = ROOT / "data" / "corpus.json"
MANIFEST = ROOT / "data" / "manifest.json"

MIN_UNIT_CHARS = 1500
DROP_HEADINGS = {"Hình ảnh", "Chú thích", "Xem thêm", "Tham khảo", "Liên kết ngoài"}
HEADING_RE = re.compile(r"^(={2,3})\s*(.+?)\s*\1$")


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def split_sections(extract: str) -> list[tuple[str, str]]:
    """Split a Wikipedia plaintext extract into (top-level heading, body) pairs."""
    lines = extract.split("\n")
    sections: list[tuple[str, list[str]]] = []
    current_title = "Giới thiệu"
    current_lines: list[str] = []
    for line in lines:
        m = HEADING_RE.match(line.strip())
        if m:
            level, title = len(m.group(1)), m.group(2)
            if level == 2:  # top-level heading starts a new section
                if current_lines:
                    sections.append((current_title, current_lines))
                current_title = title
                current_lines = []
                continue
            # level 3 (sub-heading): keep as part of current section, drop the marker
            current_lines.append(title)
            continue
        current_lines.append(line)
    if current_lines:
        sections.append((current_title, current_lines))
    return [
        (title, "\n".join(body))
        for title, body in sections
        if title not in DROP_HEADINGS
    ]


def split_into_units(text: str, min_chars: int) -> list[str]:
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    units: list[str] = []
    buf: list[str] = []
    buf_len = 0
    for para in paragraphs:
        buf.append(para)
        buf_len += len(para) + 2
        if buf_len >= min_chars:
            units.append("\n\n".join(buf))
            buf, buf_len = [], 0
    if buf:
        if units and buf_len < min_chars // 3:
            units[-1] = units[-1] + "\n\n" + "\n\n".join(buf)
        else:
            units.append("\n\n".join(buf))
    return units


def main() -> None:
    pages = []
    page_no = 1
    manifest_sources = []

    for raw_path in sorted(WIKI_RAW.glob("*.json")):
        article = json.loads(raw_path.read_text(encoding="utf-8"))
        document_id = article["slug"]
        source = article["url"]
        region = article["region"]
        extract = normalize_text(article["extract"])
        sections = split_sections(extract)

        article_unit_count = 0
        for title, body in sections:
            for unit_text in split_into_units(body, MIN_UNIT_CHARS):
                pages.append(
                    {
                        "document_id": document_id,
                        "source": source,
                        "page": page_no,
                        "section": title,
                        "mien": region,
                        "char_count": len(unit_text),
                        "text": unit_text,
                    }
                )
                page_no += 1
                article_unit_count += 1

        manifest_sources.append(
            {
                "source_id": document_id,
                "title": article["title"],
                "source_path_or_url": source,
                "mien": region,
                "unit_count": article_unit_count,
                "char_count": article["char_count"],
            }
        )

    OUT.write_text(json.dumps(pages, ensure_ascii=False, indent=2), encoding="utf-8")

    manifest = {
        "license_or_permission": (
            "Wikipedia tiếng Việt (vi.wikipedia.org), nội dung văn bản theo giấy phép "
            "CC BY-SA 4.0 và GFDL; được phép sao chép/sửa đổi/tái phân phối nếu ghi nguồn "
            "(xem https://vi.wikipedia.org/wiki/Wikipedia:Bản_quyền)."
        ),
        "accessed_at": "2026-11-14",
        "pagination_rule": (
            "Nguồn là 4 bài Wikipedia tiếng Việt (văn bản thuần, không có số trang cố định). "
            "Lấy nguyên văn phần nội dung chính qua MediaWiki API (action=query, "
            "prop=extracts, explaintext=1) bằng scripts/fetch_vn_wiki.py, loại các mục "
            "không phải nội dung (Hình ảnh, Chú thích, Xem thêm, Tham khảo, Liên kết "
            "ngoài). Mỗi mục (heading cấp 2 '== ... ==') được chia tuần tự thành các unit "
            "độc lập >=1500 ký tự chuẩn hóa (theo đoạn, không chồng lấn, không nhân bản). "
            "Số unit (page) đánh số liên tục qua 4 bài."
        ),
        "sources": manifest_sources,
        "unit_count": len(pages),
        "total_chars": sum(p["char_count"] for p in pages),
        "mien_values": sorted({p["mien"] for p in pages}),
        "sections": sorted({p["section"] for p in pages}),
        "units": [
            {
                "page": p["page"],
                "document_id": p["document_id"],
                "section": p["section"],
                "mien": p["mien"],
                "char_count": p["char_count"],
            }
            for p in pages
        ],
    }
    MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Units: {len(pages)}  Total chars: {manifest['total_chars']}")
    print(f"Mien values: {manifest['mien_values']}")


if __name__ == "__main__":
    main()
