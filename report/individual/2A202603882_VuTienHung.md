# Báo cáo cá nhân — Day 6

## Dữ liệu và pipeline
- **Chủ đề, nguồn/quyền, số trang và quy tắc tính trang:** 4 bài Wikipedia tiếng Việt — *Nha Trang*,
  *Phú Quốc*, *Sa Pa*, *Vũng Tàu* (vi.wikipedia.org), nội dung văn bản theo giấy phép **CC BY-SA 4.0
  / GFDL**, được phép sao chép/sửa đổi/tái phân phối nếu ghi nguồn. Nguồn là text thuần không có số
  trang cố định; lấy nguyên văn phần nội dung chính qua MediaWiki API (`explaintext=1`), loại các
  mục không phải nội dung (Hình ảnh, Chú thích, Xem thêm, Tham khảo), rồi chia tuần tự theo heading
  cấp 2 thành các unit ≥1500 ký tự chuẩn hóa, không trùng lặp, không chồng lấn — tổng **34 unit,
  52.351 ký tự** (nhẹ, đúng yêu cầu 30–40 unit). Chi tiết ở `data/manifest.json`.
- **Chuẩn hóa, lỗi và giới hạn:** chuẩn hóa Unicode NFKC + gộp khoảng trắng dư, giữ nguyên xuống dòng
  đoạn (`src/ingestion.py::normalize_text`). Không gặp lỗi OCR vì nguồn là văn bản số. Giới hạn: bài
  Phú Quốc rất dài (62% tổng corpus) và phần "Lịch sử" có nhiều đoạn liệt kê hành chính lặp lại
  (đổi tên khu phố) — nội dung thật nhưng kém đa dạng về mặt câu hỏi so với phần địa lý/văn hóa.
- **Embedding model/provider/version/số chiều, vector store/version, metric, lệnh chạy và chi phí:**
  `sentence-transformers/all-MiniLM-L6-v2` (local, không cần API key), 384 chiều, cùng model cho
  document và query (`src/embeddings.py`). Vector store: PostgreSQL 16 + pgvector 0.8.7 (Docker),
  metric cosine, exact search. Lệnh chạy: `docker compose -p day6_student_starter up -d --wait` rồi
  `python -m src.run` từ `starter/`. Chi phí: **$0**.
- **Metadata bắt buộc, trường lọc bổ sung, nguồn giá trị và lý do chọn:** `document_id`, `source`,
  `page` bắt buộc; bổ sung `section` (heading cấp 2 trong bài, lấy trực tiếp lúc tách — không tự
  đoán) và **`mien`** (miền Bắc/Trung/Nam, gán theo vị trí địa lý thật của từng thành phố/đảo) làm
  trường lọc chính vì có 3 giá trị phân biệt rõ, đại diện nhu cầu thực tế "chỉ tìm trong 1 miền".

## Cấu hình và benchmark
- **A / B / C:** A = `fixed_size(size=500, overlap=50)`, không filter. B = `by_paragraph(max_size=500)`,
  không filter. C = giống B về chunking, chỉ khác: áp filter `mien` hoặc `section` trong SQL khi câu
  hỏi có trường `filter`. A–B đổi đúng 1 yếu tố (chunking); B–C đổi đúng 1 yếu tố (filter khi tìm
  kiếm) — xem `artifacts/experiment_log.csv`.
- **≥20 câu:** 27 câu (`benchmark/questions.json`), chia **20 dev / 7 test** trước khi chạy, trong đó
  **11 câu có `filter`** (7 dev, 4 test — dùng `mien` và 1 câu dùng `section`). Mỗi câu có
  `evidence_quote` được xác minh bằng script (`starter/scripts/verify_benchmark.py`) khớp đúng ký tự
  (sau chuẩn hóa) với trang gold, và filter được xác minh khớp đúng `mien`/`section` thật của trang
  gold — trước khi chạy bất kỳ truy xuất nào.
- **Tiêu chí chọn chiến lược đã chốt trước khi xem test:** ưu tiên Hit@3 trên dev, sau đó grounding
  (ảnh hưởng khả năng con người xác minh bằng chứng), sau đó filter compliance, cuối cùng thời
  gian/chi phí ingest.

## Kết quả

| Strategy | Split | Hit@1 (n/N) | Evidence Hit@3 (n/N) | Chunk count | Thời gian | Chi phí |
|---|---|---|---|---|---|---|
| A | dev | 4/20 | 7/20 | 132 | 15.73s | $0 |
| A | test | 3/7 | 5/7 | 132 | 15.73s | $0 |
| B | dev | 6/20 | 10/20 | 129 | 23.86s | $0 |
| B | test | 5/7 | 6/7 | 129 | 23.86s | $0 |
| C | dev | 7/20 | 12/20 | 129 | 11.38s | $0 |
| C | test | 5/7 | 6/7 | 129 | 11.38s | $0 |

| Strategy | Coherence trung bình /2 (n) | Metadata đủ và đúng (n/N) | Filter tuân thủ (n/N) | Grounding 0/1/2 (số câu) và trung bình /2 |
|---|---|---|---|---|
| A | 0.7/2 (10) | 15/15 | 6/11 | 0:1, 1:0, 2:4 (n=5) · TB 1.6/2 |
| B | 0.9/2 (10) | 15/15 | 6/11 | 0:0, 1:0, 2:5 (n=5) · TB 2.0/2 |
| C | 0.9/2 (10, giống B — chunking không đổi) | 15/15 | 11/11 | 0:0, 1:0, 2:5 (n=5) · TB 2.0/2 |

Đường dẫn trace: `starter/results/trace_{a,b,c}.json` (top-3 đầy đủ cho mọi câu dev+test),
`starter/results/summary.json` (Hit@1/Hit@3/filter-compliance tổng hợp), `starter/results/run_meta.json`
(tham số, số chunk, thời gian, chi phí). Nhãn thủ công + cách chọn mẫu (10 vị trí page 1–10 cho
coherence, 5 câu test đầu q21–q25 cho metadata/grounding, chọn trước khi xem điểm):
`starter/results/manual_audit.md`.

## Phân tích và kết luận
- **A–B:** đổi chunking từ fixed-size sang theo đoạn cải thiện Hit@3 dev (0.35→0.50) và grounding
  (1.6→2.0/2) rõ rệt, nhưng coherence chỉ nhích nhẹ (0.7→0.9/2). Lý do cụ thể: phần lớn văn bản
  Wikipedia tiếng Việt về lịch sử/hành chính viết liền mạch, **không có dòng trống ngăn đoạn** —
  `by_paragraph` chỉ tách tại `\n\n`, nên khi cả trang là một khối văn bản dài, nó buộc hard-split
  giống fixed-size và mất lợi thế. Lợi thế chỉ rõ ràng ở trang có heading con thật (ví dụ trang 7 —
  "Vị trí địa lý/Địa hình/Khí hậu" của Phú Quốc).
- **B–C:** không đổi Hit@1/Hit@3 trên 5 câu trong mẫu audit (top-1 đã đúng miền ngay cả không
  filter, vì mỗi bài Wikipedia thường tự nhất quán 1 miền), nhưng filter compliance nhảy từ 6/11 lên
  11/11 trên toàn bộ 11 câu filter dev+test — giá trị thật của C là đảm bảo tuân thủ phạm vi tìm
  kiếm một cách **chắc chắn bằng SQL**, không phải "ăn may" như B/A.
- **2 ví dụ sai/đáng chú ý:**
  - q25 ở strategy A (gold page 34, về sự kiện 10/2/1859 tại pháo đài Phước Thắng) — top-3 của A
    không chunk nào chứa đủ câu "khai hỏa... Rigault de Genouilly" vì fixed-size cắt câu đó rời khỏi
    phần dẫn; B/C giữ trọn câu trong 1 chunk theo đoạn, tìm đúng ngay rank-1.
  - Trang 2, 3, 9, 10 (toàn corpus) — cả A và B/C đều cắt giữa từ ở vị trí coherence-sample vì không
    có ranh giới đoạn thật, cho thấy hạn chế chung của cả 2 cách chunk trên văn bản liệt kê dày đặc.
- **Chiến lược chọn, đánh đổi, điều kiện áp dụng:** chọn **C** cho sản phẩm cuối vì giữ nguyên lợi
  ích grounding của B và thêm filter compliance tuyệt đối khi người dùng chỉ định phạm vi (miền) —
  phù hợp nếu ứng dụng cho phép người dùng/agent cung cấp context phạm vi trước khi truy xuất. Nếu
  không cần lọc phạm vi, B đã đủ.
- **Hạn chế:** (1) test set chỉ 7 câu, 1 câu đổi có thể lệch Hit@1 tới ~14 điểm % — không suy rộng
  ngoài 4 bài Wikipedia cụ thể này; (2) người chấm thủ công = tác giả benchmark/code, có nguy cơ
  thiên lệch ưu ái B/C; (3) corpus mất cân đối: Phú Quốc chiếm 62% unit, có nhiều đoạn liệt kê hành
  chính lặp lại làm giảm đa dạng ngữ nghĩa; (4) embedding 384 chiều (MiniLM) là model nhỏ, chưa thử
  model lớn hơn hoặc model tiếng Việt chuyên biệt.
- **Nếu làm lại hoặc mở rộng:** (1) thử embedding model tiếng Việt chuyên biệt (ví dụ
  `keepitreal/vietnamese-sbert` hoặc API đa ngữ lớn hơn) để so sánh với MiniLM đa ngữ hiện tại;
  (2) tiền xử lý thêm để chèn ranh giới đoạn giả (theo câu/theo chủ đề) cho các khối văn bản liệt kê
  dày đặc, giúp `by_paragraph` phát huy tác dụng đều hơn; (3) cân bằng lại corpus (bớt phần liệt kê
  hành chính lặp của Phú Quốc, thêm bài khác) để tránh một tài liệu chiếm áp đảo.
