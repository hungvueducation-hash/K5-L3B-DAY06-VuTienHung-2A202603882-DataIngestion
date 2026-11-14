# Audit thủ công — Day 06 Data Ingestion

**Người chấm:** Vũ Tiến Hùng (tác giả bài làm). Toàn bộ nhãn dưới đây do chính tác giả gán thủ công
bằng cách đọc trực tiếp `results/coherence_sample.json` và `results/audit_sample_{a,b,c}.json`
(trích từ trace thật `trace_a/b/c.json` do `src/run.py` sinh ra, không tự suy diễn). Nguy cơ thiên
lệch: người chấm cũng là người thiết kế benchmark và code, nên có thể vô thức ưu ái cấu hình mà
mình kỳ vọng tốt hơn (ở đây là B/C so với A) — xem phần "Hạn chế" ở báo cáo cá nhân.

## 1. Chunk coherence (thang 0–2, 10 vị trí = page 1–10, chọn trước khi xem điểm)

Quy tắc: xét chunk đầu tiên bao phủ vị trí đó trong mỗi chiến lược (`...:0`). 0 = cắt giữa câu/từ,
mất chủ thể, không hiểu được; 1 = hiểu một phần nhưng thiếu ngữ cảnh hoặc câu bị cắt ở ranh giới mệnh
đề/liệt kê; 2 = tự hiểu được, giữ trọn ý.

| Page | Strategy A (fixed 500/50) | Lý do | Strategy B/C (by_paragraph, max 500) | Lý do |
|---|---|---|---|---|
| 1 | 2 | Trang ngắn (264 ký tự), trọn trong 1 chunk, câu hoàn chỉnh | 2 | Giống A |
| 2 | 0 | Cắt giữa từ: "...nho sinh họ Đỗ tên Bá soạn v" | 0 | Trang là 1 đoạn văn dài liên tục (không có dòng trống ngăn đoạn), nên bị buộc hard-split giống A, cắt cùng điểm |
| 3 | 0 | Cắt giữa từ: "...Thị trấn Nha Trang h" | 0 | Cùng lý do trang 2 — văn bản hành chính dạng liệt kê liên tục không có ranh giới đoạn rõ |
| 4 | 0 | Cắt giữa câu, bỏ lửng mốc thời gian "...năm 1977," | 0 | Tương tự A |
| 5 | 1 | Cắt giữa liệt kê phường, còn hiểu được phần đầu | 1 | Giống A |
| 6 | 2 | Trang ngắn (161 ký tự), trọn câu | 2 | Giống A |
| 7 | 0 | Cắt giữa từ: "...đảo Phú Quốc b" | 2 | **Khác biệt rõ nhất:** trang này có heading con ("Vị trí địa lý", "Địa hình"...) ngăn bằng dòng trống → by_paragraph tách đúng theo heading, chunk đầu "Vị trí địa lý..." trọn ý hoàn chỉnh |
| 8 | 2 | Trang rất ngắn (59 ký tự) | 2 | Giống A |
| 9 | 0 | Trang rất dài (5578 ký tự) văn xuôi liên tục, cắt giữa từ "...phái đoà" | 0 | Cùng lý do — không có dòng trống để chia đoạn, hard-split trùng điểm cắt với A |
| 10 | 0 | Cắt giữa câu | 0 | Tương tự A |

**Điểm trung bình /2:** Strategy A = 0.7/2 (7/20) · Strategy B = C = 0.9/2 (9/20).

**Nhận xét quan trọng (khác với thử nghiệm trước trên văn bản tiếng Anh có đoạn ngắn):** corpus
Wikipedia tiếng Việt này có nhiều đoạn lịch sử/hành chính viết liền một mạch, **không có dòng trống
ngăn đoạn** trong phần lớn nội dung. Vì `by_paragraph` chỉ tách tại ranh giới `\n\n`, khi cả trang là
một "đoạn" khổng lồ, nó buộc phải hard-split giống fixed-size và mất lợi thế coherence. Lợi thế của
B/C chỉ rõ ràng ở những phần có heading con tạo ranh giới đoạn thật (ví dụ trang 7 — "Vị trí địa lý/
Địa hình/Khí hậu"). Đây là phát hiện thật, không phải giả định: **hiệu quả của chiến lược chunking
phụ thuộc cấu trúc đoạn của nguồn**, không phải lúc nào by_paragraph cũng thắng tuyệt đối.

## 2. Metadata usefulness (5 câu test đầu × top-3 = 15 bản ghi/chiến lược)

Kiểm tra `document_id`, `source`, `page`, `section`, `mien` của 15 bản ghi mỗi chiến lược (q21–q25,
xem `results/audit_sample_{a,b,c}.json`) đối chiếu `data/manifest.json`. Cả 3 chiến lược:
**15/15 bản ghi có đủ và đúng** `document_id`/`source`/`page`/`section`/`mien` — các trường này được
giữ nguyên từ `DocumentPage` lúc ingest tới lúc lưu (`store.py` không sửa giá trị), không có đường
nào làm sai lệch. Trường `mien` (miền Bắc/Trung/Nam) hữu dụng thật: cho phép người dùng chỉ hỏi
trong phạm vi một miền (ví dụ chỉ muốn kết quả về Vũng Tàu/Phú Quốc ở miền Nam, loại Sa Pa miền Bắc)
— hạn chế: `mien` chỉ phân biệt ở mức miền (3 giá trị), còn `section` (heading) phân biệt mịn hơn
trong từng bài (ví dụ "Nguồn gốc" vs "Những thay đổi trong lịch sử") nhưng không phân biệt được giữa
các bài khác nhau có cùng tên heading.

**Filter compliance** (top-3 tuân thủ filter khi câu hỏi có filter, tính trên toàn bộ 11 câu filter
dev+test, lấy từ `results/summary.json` do `run.py` sinh ra):
- Strategy A: 6/11 (không chủ động filter, trùng ngẫu nhiên vì mỗi bài thường tự nhất quán 1 miền)
- Strategy B: 6/11 (không chủ động filter, cùng lý do)
- Strategy C: 11/11 (chủ động filter theo `mien`/`section` trong SQL — đúng như thiết kế)

## 3. Grounding quality (thang 0–2, 5 câu test đầu × top-3)

0 = top-3 không có bằng chứng liên quan; 1 = có nhưng thiếu điều kiện/ngữ cảnh; 2 = đủ để trả lời và
truy nguồn đúng.

| Câu | Gold page | A | B | C | Lý do |
|---|---|---|---|---|---|
| q21 | 31 (filter Nam) | 2 | 2 | 2 | Cả 3 đều có chunk page 31 trong top-3 chứa đúng câu "Vũng Tàu là một địa danh... TP.HCM" |
| q22 | 32 | 2 | 2 | 2 | Cả 3 đều top-1 trúng page 32, chứa đúng trích dẫn Phủ biên tạp lục |
| q23 | 33 (filter Nam) | 2 | 2 | 2 | Cả 3 đều top-1 trúng page 33, chứa đúng câu "Cap Saint-Jacques" |
| q24 | 34 | 2 | 2 | 2 | A: hit ở rank-3 (chunk lớn chứa cả đoạn Minh Mạng); B/C: hit ngay rank-1 |
| q25 | 34 | 0 | 2 | 2 | A: top-3 không chunk nào chứa đúng câu "khai hỏa súng thần công... Rigault de Genouilly" (bị tách sang chunk khác do fixed-size cắt cơ học); B/C: top-1 trúng ngay, chunk theo đoạn giữ nguyên cả câu |

**Trung bình /2:** A = 1.6/2 (4/5 câu đạt 2, 1 câu đạt 0) · B = C = 2.0/2 (5/5 câu đạt 2).

**Lưu ý (per GUIDE.md):** đây chỉ đo độ đủ của bằng chứng truy xuất, không phải độ chính xác câu trả
lời LLM — lab này không bắt buộc xây chatbot và không có bước LLM sinh câu trả lời.

## 4. Data strategy impact — A vs B, B vs C

- **A → B** (đổi chunking, giữ nguyên metadata/không filter): Hit@3 dev tăng 0.35 → 0.50, Hit@1 test
  tăng mạnh 0.43 → 0.71; coherence tăng nhẹ 0.7 → 0.9/2 (do phần lớn nội dung không có ranh giới đoạn
  rõ — xem mục 1); grounding tăng rõ 1.6 → 2.0/2 nhờ tránh được lỗi cắt-chunk làm mất câu bằng chứng
  (q25). Đánh đổi: ingest B chậm hơn A một chút (23.86s vs 15.73s) vì nhiều chunk nhỏ hơn cần
  encode riêng, nhưng ít chunk hơn tổng (129 vs 132) do không có overlap.
- **B → C** (giữ chunking, thêm filter theo `mien`/`section` khi câu hỏi có filter): Hit@1/Hit@3
  không đổi trên mẫu audit 5 câu (vì top-1 thật đã đúng miền ngay cả không filter ở các câu mẫu),
  nhưng Hit@1 dev toàn bộ tăng 0.30 → 0.35 nhờ các câu filter dev khác ngoài mẫu audit được lọc đúng
  miền. Tác động rõ nhất của C: **filter compliance nhảy từ 6/11 lên 11/11** trên toàn bộ câu filter
  dev+test — đảm bảo tuân thủ phạm vi tìm kiếm tuyệt đối, thay vì chỉ "ăn may" vì mỗi bài tự nhất
  quán 1 miền.
- **Trường hợp thất bại/đáng chú ý:**
  - q25 ở strategy A: bằng chứng ("khai hỏa súng thần công... Rigault de Genouilly") bị fixed-size
    cắt rời khỏi câu dẫn, khiến A không tìm được trong top-3 dù B/C tìm được ngay — ví dụ cụ thể cho
    thấy chunking cơ học có thể phá hỏng bằng chứng mà chunking theo cấu trúc giữ được.
  - Trang 2, 3, 9, 10 (văn bản hành chính liệt kê liên tục, không dòng trống): B/C không có lợi thế
    gì so với A về coherence — cho thấy lợi ích của by_paragraph phụ thuộc cấu trúc đoạn thật của
    nguồn, không phải một quy luật tuyệt đối.
- **Sai số do mẫu nhỏ:** test set chỉ 7 câu — một câu đổi kết quả có thể lệch Hit@1 tới ~14 điểm %,
  không nên suy rộng "chiến lược C luôn tốt hơn" ngoài 4 bài Wikipedia cụ thể này.
