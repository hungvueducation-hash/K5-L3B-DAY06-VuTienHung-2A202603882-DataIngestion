# Day 06 · Data Ingestion Engineering

**Lab cá nhân** · **4 giờ** · **Dữ liệu tự chọn**

Biến tài liệu thành kho tri thức có thể truy xuất cho AI agent, rồi đo xem cách chuẩn bị dữ liệu nào hiệu quả nhất.

| 📄 Dữ liệu | 🧩 Chiến lược | 🎯 Benchmark |
|---|---|---|
| Tối thiểu **30 trang nội dung** | Tối thiểu **3 cấu hình** | Tối thiểu **20 câu hỏi** |

## Bắt đầu nhanh

Dùng [starter PostgreSQL + pgvector](starter/README.md) để dựng database và hoàn thiện các hàm TODO, hoặc tự chọn vector store tương đương. Starter chỉ là khung: **bạn tự hiện thực pipeline và benchmark**.

## 1. Xây pipeline

![Đọc tài liệu, chuẩn hóa, chia chunk, tạo vector, lưu và kiểm tra](assets/ingestion-pipeline.svg)

Chọn tài liệu được phép sử dụng; giữ **ID tài liệu, nguồn, trang/vị trí** và metadata phù hợp. Dùng embedding model thật qua API hoặc chạy local; lưu và truy xuất bằng pgvector, Qdrant, Chroma hoặc một store tương đương.

## 2. So sánh và đánh giá

![Ba chiến lược được đánh giá trên cùng corpus và benchmark dev/test](assets/benchmark-workflow.svg)

Dùng cùng dữ liệu, model và câu hỏi cho cả ba cấu hình. Tách **15 câu dev / 5 câu test** trước khi chạy; chọn cấu hình trên dev, rồi đánh giá test sau khi cố định. Mỗi câu hỏi cần có đoạn bằng chứng và trang nguồn; thiết kế bộ câu hỏi và đánh giá theo [BENCHMARK.md](BENCHMARK.md).

Đánh giá theo năm khía cạnh: **độ chính xác truy xuất**, **tính mạch lạc của chunk**, **tính hữu dụng của metadata**, **chất lượng grounding** và **tác động của chiến lược dữ liệu**. Giải thích lựa chọn bằng kết quả, ví dụ lỗi và các đánh đổi.

## 3. Chuẩn bị bài nộp

1. Chạy pipeline và lưu cấu hình, kết quả top-3, trace cùng nhãn đánh giá thủ công.
2. Điền [thông tin học viên](STUDENT.md), [nhật ký thí nghiệm](artifacts/experiment_log.csv) và bản sao [mẫu báo cáo cá nhân](report/individual/MSSV_HoTen.md).
3. Kiểm tra mã nguồn, cách chạy, manifest dữ liệu và checklist trong [SUBMISSION.md](SUBMISSION.md).

## Tài liệu hướng dẫn

| Bạn cần tìm | Tài liệu |
|---|---|
| Setup baseline PostgreSQL + pgvector | [starter/README.md](starter/README.md) |
| Các bước làm và cách tính chỉ số | [GUIDE.md](GUIDE.md) |
| Tiến độ trong 4 giờ | [CHECKPOINTS.md](CHECKPOINTS.md) |
| Năm tiêu chí benchmark và bộ câu hỏi | [BENCHMARK.md](BENCHMARK.md) |
| Tiêu chí chấm điểm | [RUBRIC.md](RUBRIC.md) |
| Quy tắc sử dụng dữ liệu, AI và API | [RULES.md](RULES.md) |
| Cách nộp bài | [SUBMISSION.md](SUBMISSION.md) |

[data/format-example.json](data/format-example.json) chỉ minh họa định dạng, không phải corpus đủ điều kiện. Phần xử lý và benchmark do bạn tự hiện thực; không bắt buộc xây chatbot.

---

## Bài làm của Vũ Tiến Hùng (2A202603882) — cách chạy

Corpus: 4 bài Wikipedia tiếng Việt — Nha Trang, Phú Quốc, Sa Pa, Vũng Tàu (CC BY-SA 4.0/GFDL),
34 unit / 52.351 ký tự (xem [data/manifest.json](data/manifest.json)). Metadata filter: `mien`
(Bắc/Trung/Nam). 27 câu benchmark ở [benchmark/questions.json](benchmark/questions.json)
(20 dev / 7 test, 11 câu có filter). Code pipeline ở [starter/src/](starter/src/).

```bash
cd starter
python -m venv .venv
.venv\Scripts\Activate.ps1          # Windows PowerShell
pip install -r requirements.txt     # psycopg, pypdf, python-dotenv, sentence-transformers, torch
Copy-Item .env.example .env         # giữ nguyên, không cần API key (dùng model local)

docker compose -p day6_student_starter up -d --wait
python scripts/check_setup.py       # kiểm tra hạ tầng

# (một lần) tải 4 bài Wikipedia sạch (plaintext qua MediaWiki API) rồi tách thành corpus
python scripts/fetch_vn_wiki.py
python scripts/build_corpus.py
python -I scripts/verify_benchmark.py   # kiểm chứng evidence_quote + filter của cả 27 câu

python -m src.run                   # chạy pipeline thật: embed + lưu pgvector + benchmark 3 chiến lược
python scripts/sample_coherence.py  # lấy mẫu 10 vị trí page 1-10 cho coherence (đã chấm ở results/manual_audit.md)
```

Kết quả: `starter/results/run_meta.json`, `summary.json`, `trace_{a,b,c}.json`, `manual_audit.md`
(audit thủ công 5 khía cạnh). Báo cáo cá nhân đầy đủ:
[report/individual/2A202603882_VuTienHung.md](report/individual/2A202603882_VuTienHung.md).
Experiment log: [artifacts/experiment_log.csv](artifacts/experiment_log.csv).

Chi phí: $0 (embedding model chạy local, `sentence-transformers/all-MiniLM-L6-v2`, không gọi API trả phí).

### Giao diện chatbot demo (ngoài yêu cầu bài tập)

Lab không bắt buộc xây chatbot (xem mục trên), nhưng có thêm một UI demo kiểu chat để tra cứu trực
tiếp trên pgvector thật — **không phải LLM sinh câu trả lời**, chỉ hiển thị top-3 đoạn trích + điểm
số + metadata (giống đúng cách benchmark đo grounding). Code ở [starter/webapp/](starter/webapp/).

```bash
cd starter
docker compose -p day6_student_starter up -d --wait   # nếu chưa chạy
.venv\Scripts\python.exe -m uvicorn webapp.app:app --host 127.0.0.1 --port 8099
```

Mở `http://127.0.0.1:8099`, chọn chiến lược A/B/C (+ lọc miền nếu muốn), nhập câu hỏi về Nha Trang/
Phú Quốc/Sa Pa/Vũng Tàu. Chỉ chạy local (bind `127.0.0.1`), không có xác thực — không expose ra ngoài.

**Tùy chọn — trả lời bằng GPT:** dán `OPENAI_API_KEY` thật vào `starter/.env` (file này đã bị
`.gitignore`, không bao giờ commit), tick ô "Trả lời bằng GPT" trên UI. Khi đó `webapp/answer.py`
gọi `gpt-4o-mini` đọc đúng top-3 đoạn trích đã truy xuất và tóm tắt trả lời kèm trích nguồn — **chỉ
dùng cho UI demo này**, không đụng tới pipeline/benchmark chính (`src/run.py` vẫn retrieval-only,
không gọi LLM, giữ đúng định nghĩa "grounding" của GUIDE.md). Không có key thì ô này tự vô hiệu và
chatbot vẫn hoạt động như cũ (chỉ hiện top-3 đoạn trích).
