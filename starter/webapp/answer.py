"""LLM answer synthesis for the demo chatbot UI only (NOT part of the graded
pipeline/benchmark). Reads the real top-k retrieved chunks and asks GPT to
answer strictly from them, citing source/page -- never used in src/run.py or
the Hit@1/Hit@3 scoring, which stays retrieval-only per GUIDE.md's grounding
definition.
"""
import os
from typing import Any

SYSTEM_PROMPT = (
    "Bạn là trợ lý tra cứu. Chỉ trả lời dựa trên các đoạn trích (evidence) được "
    "cung cấp dưới đây, không dùng kiến thức ngoài. Nếu đoạn trích không đủ để "
    "trả lời, nói rõ là không tìm thấy thông tin. Luôn ghi chú nguồn (document_id, "
    "trang) cho mỗi thông tin bạn dùng. Trả lời ngắn gọn, bằng tiếng Việt."
)


def is_configured() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY"))


def synthesize_answer(question: str, hits: list[dict[str, Any]], model: str = "gpt-4o-mini") -> str:
    if not hits:
        return "Không có đoạn trích nào được truy xuất để trả lời."
    if not is_configured():
        raise RuntimeError("OPENAI_API_KEY chưa được cấu hình trong starter/.env")

    from openai import OpenAI

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    context_blocks = []
    for i, h in enumerate(hits, start=1):
        context_blocks.append(
            f"[Đoạn {i}] (nguồn: {h['document_id']}, trang {h['page']}, mục: {h.get('section')})\n{h['text']}"
        )
    context = "\n\n".join(context_blocks)

    user_prompt = f"Câu hỏi: {question}\n\nCác đoạn trích:\n\n{context}\n\nTrả lời câu hỏi dựa trên các đoạn trích trên."

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.0,
    )
    return resp.choices[0].message.content or ""
