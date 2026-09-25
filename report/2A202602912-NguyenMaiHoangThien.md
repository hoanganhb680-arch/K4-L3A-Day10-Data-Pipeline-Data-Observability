# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Nguyễn Mai Hoàng Thiện |
| MSSV | 2A202602912 |
| Khóa/Lớp | K4 |
| Tên nhóm |  |
| Vai trò chính | Data Engineer & Data Observability Specialist |
| Repository | hoanganhb680-arch/K4-L3A-Day10-Data-Pipeline-Data-Observability |
| Ngày hoàn thành | 2026-09-25 |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Data Ingestion & Parsing | `src/ingestion/crossref.py` (`fetch_source_records`, `parse_crossref_payload`) | Crossref REST API JSON Payload / Local Snapshot | List[`PaperRecord`] & `data/raw/crossref_records.json` | Hoàn thành |
| Data Cleaning & Normalization | `src/ingestion/cleaning.py` (`build_clean_dataframe`, `clean_html_tags`) | List[`PaperRecord`] | Clean `pandas.DataFrame` & `data/clean/papers_clean.json` | Hoàn thành |
| Data Observability & Quality | `src/observability/quality.py` (`run_data_quality_checks`, `build_freshness_report`) | `pandas.DataFrame`, `Settings` | Quality dict (`success`, `expectations`), `freshness_report.json` | Hoàn thành |
| Data Corruption & Automated Repair | `src/ingestion/corruption.py` (`corrupt_clean_dataframe`), `src/pipelines/corruption_flow.py` | Clean `DataFrame`, Snapshot | Corrupted DataFrame, Repair pipeline flow, `corruption_report.md` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Pipeline Orchestration & End-to-End | `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py` | Tích hợp hoàn chỉnh luồng RAG Baseline, Data Quality Checks, LLM Evaluation và Báo cáo so sánh |
| Troubleshooting & Python 3.11 Compatibility | Toàn bộ dự án | Thiết lập Virtual Environment Python 3.11, khắc phục xung đột dependency `pyproject.toml` và bổ sung `sentence-transformers` |

---

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Thu thập & Chuẩn hóa dữ liệu nghiên cứu | `src/ingestion/crossref.py`, `src/ingestion/cleaning.py` | 24 bản ghi nghiên cứu chất lượng cao, xóa bỏ thẻ HTML, chuẩn hóa ngày ISO UTC | `.\.venv\Scripts\python.exe script/run_phase1.py` |
| Xây dựng hệ thống Data Quality Checks | `src/observability/quality.py` | Bộ 6 quy tắc kiểm định Great Expectations (Null, Unique ID, Date Range, Category Set) | `data/quality/baseline_quality_report.json` |
| Theo dõi độ tươi của dữ liệu (Data Freshness) | `src/observability/quality.py` | Đánh giá độ trễ xuất bản so với ngưỡng 180 ngày | `data/quality/freshness_report.json` |
| Giả lập sự cố dữ liệu & Luồng tự động sửa chữa | `src/ingestion/corruption.py`, `src/pipelines/corruption_flow.py` | Kịch bản phá hoại dữ liệu (xóa dòng, rỗng summary, mốc ngày) và tự động kéo lại snapshot để Repair | `.\.venv\Scripts\python.exe script/run_corruption_flow.py` |

**Mô tả Output cụ thể:**
- Báo cáo so sánh `data/reports/corruption_report.md` minh chứng sự sụt giảm metric khi dữ liệu bị phá hoại (`Hit Rate` giảm từ 1.00 xuống 0.80, `Token F1` giảm từ 0.52 xuống 0.37) và sự phục hồi hoàn toàn sau khi chạy pipeline Repair.

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
Dữ liệu thô từ các nguồn như Crossref REST API thường chứa nhiễu (thẻ HTML trong abstract, thiếu tác giả, ngày tháng không thống nhất, dữ liệu cũ trễ hạn). Nếu đưa trực tiếp dữ liệu này vào Vector Database (ChromaDB) cho RAG Agent, chất lượng truy xuất và câu trả lời của LLM sẽ bị suy giảm nghiêm trọng mà không có cảnh báo trước.

### Cách triển khai
1. **Parsing & Cleaning:** Sử dụng Regular Expression để bóc tách triệt để các thẻ HTML (`<jats:p>`, `<b>`...), chuyển đổi ngày về ISO UTC (`YYYY-MM-DDTHH:MM:SS`), sinh UUID duy nhất cho từng bài báo và lọc bỏ bản ghi thiếu tiêu đề/tóm tắt.
2. **Data Observability:** Áp dụng Great Expectations (GX 1.x Ephemeral Data Context) để tạo bộ quy tắc kiểm tra (Expectations Suite) gồm: `expect_column_values_to_not_be_null`, `expect_column_values_to_be_unique`, `expect_column_values_to_be_in_set`,...
3. **Freshness Monitoring:** Tính khoảng cách ngày giữa thời điểm hiện tại và ngày xuất bản (`published`). Nếu `age_days > 180`, bản ghi bị đánh dấu là `stale`. Nếu tỷ lệ `stale > 50%`, toàn bộ tập dữ liệu bị gắn nhãn `Is Fresh = False`.
4. **Data Corruption & Repair:** Tạo ra 5 loại thảm họa dữ liệu ngẫu nhiên (drop dòng, rỗng tóm tắt, dời ngày xuất bản về quá khứ 200 ngày, nhân bản dòng, cắt xén tiêu đề). Khi phát hiện Quality Check thất bại, hệ thống khôi phục dữ liệu bằng cách tải lại snapshot thô nguyên bản và chạy lại quy trình làm sạch.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | JSON Payload từ Crossref API hoặc local snapshot `data/raw/crossref_response.json` |
| Output | `pandas.DataFrame` đã dọn dẹp, `data/clean/papers_clean.json`, `data/reports/*.md` |
| Module phụ thuộc | `core.config`, `requests`, `great_expectations`, `pandas` |
| Module sử dụng output | `retrieval.index` (tạo vector embeddings), `evaluation.testset`, `evaluation.metrics` |
| Điều kiện lỗi cần xử lý | API trả về 429 Too Many Requests -> Chuyển sang đọc Local Snapshot; Bản ghi thiếu DOI/title -> Bỏ qua an toàn. |

### Cách xác minh

```bash
$env:PYTHONIOENCODING="utf-8"
$env:PYTHONPATH="src"
.\.venv\Scripts\python.exe script/run_phase1.py
.\.venv\Scripts\python.exe script/run_corruption_flow.py
```

- **Kết quả mong đợi:** Cả hai script chạy thành công không có lỗi, sinh ra file `data/reports/phase1_report.md` và `data/reports/corruption_report.md`.
- **Kết quả thực tế:** Dữ liệu được xử lý 24 bản ghi sạch; Great Expectations kiểm định 6/6 quy tắc thành công; RAG Hit Rate đạt 1.00 trên tập sạch.
- **Artifact/log:** [phase1_report.md](file:///e:/dev.nmht.ai/K4-L3A-Day10-Data-Pipeline-Data-Observability/data/reports/phase1_report.md), [corruption_report.md](file:///e:/dev.nmht.ai/K4-L3A-Day10-Data-Pipeline-Data-Observability/data/reports/corruption_report.md).

---

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Lựa chọn phương pháp tích hợp Great Expectations cho pipeline Data Observability.
- **Các phương án đã cân nhắc:**
  1. *Phương án A:* Khởi tạo thư mục dự án GX truyền thống (`gx/` với file `great_expectations.yml` cố định trên đĩa).
  2. *Phương án B (Đã chọn):* Sử dụng **Ephemeral Data Context (GX 1.x)** trong bộ nhớ, tự định nghĩa `ExpectationSuite` bằng mã Python ngắn gọn.
- **Phương án đã chọn:** Phương án B.
- **Lý do:** 
  - GX 1.x Ephemeral Context không yêu cầu cấu hình các file YAML phức tạp, dễ bảo trì, mã nguồn gọn nhẹ và tương thích hoàn toàn với luồng CI/CD hoặc các script chạy tự động.
  - Tốc độ thực thi kiểm định nhanh hơn, dễ dàng tùy biến cho cả 3 giai đoạn: Baseline, Corrupted và Repaired.
- **Bằng chứng quyết định phù hợp:** `run_data_quality_checks` thực thi tức thì (<0.5s) cho 24 bản ghi và tạo ra báo cáo JSON chất lượng rõ ràng trong `data/quality/`.

---

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:**
  ```text
  ImportError: cannot import name 'save_raw_records' from 'ingestion.crossref'
  AttributeError: 'Paths' object has no attribute 'phase1_report'
  ```
- **Lệnh hoặc bước tái hiện:** `.\.venv\Scripts\python.exe script/run_phase1.py`
- **Nguyên nhân gốc:**
  - `save_raw_records` đã được tích hợp trực tiếp vào bên trong hàm `fetch_source_records` trong `crossref.py` nhưng file `phase1.py` vẫn giữ lệnh import từ phiên bản cũ.
  - Trong `src/core/config.py`, thuộc tính lưu đường dẫn báo cáo được đặt tên là `baseline_report`, nhưng trong `phase1.py` lại truy cập biến `phase1_report`.
- **Cách xử lý:**
  - Cập nhật `phase1.py`: Bỏ import `save_raw_records`, điều chỉnh truy cập `settings.paths.baseline_report` và `settings.paths.baseline_metrics`.
- **Cách xác minh sau khi sửa:** Chạy lại `script/run_phase1.py` -> Tiến trình hoàn thành 100% không bắn ra exception.
- **Điều học được:** Cần kiểm tra kỹ hợp đồng dữ liệu (data contract/dataclass attributes) giữa module cấu hình (`config.py`) và module điều phối (`pipelines/`) trước khi thực thi.

---

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?**
   - Dữ liệu thô JSON từ Crossref REST API được kéo về -> Hàm `parse_crossref_payload` giải mã và chuẩn hóa thành các đối tượng `PaperRecord` -> `build_clean_dataframe` làm sạch HTML và format ngày -> Chuyển thành `pandas.DataFrame` -> Hàm `LocalEmbeddingIndex.build` lấy văn bản (`title` + `summary`), dùng model `sentence-transformers/all-MiniLM-L6-v2` để biến đổi thành các vector embedding (384 chiều) và lưu trữ vào ChromaDB Collection.

2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**
   - Hàm `build_test_set` lấy ngẫu nhiên các bài báo trong tập dữ liệu sạch để tạo ra 10 câu hỏi kiểm thử thuộc 4 nhóm (Summary, Authors, Date, Category), lưu kèm `ground_truth_doc_id`. Khi chạy evaluation, RAG Agent thực hiện tìm kiếm Top-K vector. Nếu `ground_truth_doc_id` nằm trong danh sách K tài liệu được trả về, `Hit Rate = 1`. Nội dung câu trả lời của LLM được so sánh với Ground Truth để tính điểm `Token F1` và điểm số từ `LLM Judge` (1-5).

3. **Quality checks khác freshness monitoring ở điểm nào trong bài lab?**
   - **Quality checks (Great Expectations):** Kiểm tra tính hợp lệ về cấu trúc và kiểu dữ liệu tại một thời điểm (Data Schema Integrity): không chứa null ở các trường bắt buộc, ID không trùng lặp, danh mục thuộc tập hợp hợp lệ.
   - **Freshness monitoring:** Kiểm tra tính hợp lệ về thời gian (Data Timeliness): đo đạc xem dữ liệu trong pipeline có bị "mốc" (stale) hay không bằng cách so sánh tuổi xuất bản của bài báo với ngưỡng cho phép (180 ngày).

4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**
   - Để đảm bảo tính công bằng và nhất quán trong thực nghiệm (Controlled Experimentation). Khi giữ nguyên tập câu hỏi kiểm thử và Ground Truth, bất kỳ sự thay đổi nào về chỉ số (Hit Rate, F1, Judge Score) giữa 3 giai đoạn đều phản ánh chính xác tác động của chất lượng dữ liệu (Data Quality), loại bỏ được sai số do câu hỏi biến động.

5. **Repair được xem là thành công dựa trên artifact và metric nào?**
   - **Data Quality Artifacts:** `data/quality/repaired_quality_report.json` đạt `Success = True` (tất cả các quy tắc kiểm định Great Expectations đều pass) và `Is Fresh = True`.
   - **Agent Metrics:** Các chỉ số RAG được phục hồi hoàn toàn về mức bằng hoặc tương đương Baseline: `Retrieval Hit Rate` tăng từ 0.80 lên 1.00, `Mean Token F1` tăng từ 0.37 lên 0.52, và `Mean Judge Score` tăng từ 2.50 lên 3.00.

---

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.00 | 0.80 | 1.00 | Data bị drop 10% dòng làm giảm khả năng tìm thấy tài liệu gốc. Sau repair khôi phục lại 100%. |
| `mean_token_f1` | 0.52 | 0.37 | 0.52 | Khi trường summary bị xóa rỗng, LLM thiếu ngữ cảnh nên điểm F1 giảm mạnh. Phục hồi hoàn toàn sau repair. |
| `judge_accuracy` | 0.50 | 0.40 | 0.50 | Độ chính xác của LLM Judge phản ánh trực tiếp chất lượng tài liệu được truy xuất. |
| `mean_judge_score` | 3.00 | 2.50 | 3.00 | Điểm đánh giá chất lượng câu trả lời sụt giảm 0.5 điểm khi dữ liệu bị phá hoại. |
| Quality checks | Passed (True) | Failed (False) | Passed (True) | Great Expectations bắt chính xác lỗi rỗng summary và trùng lặp ID ở tập Corrupted. |
| Freshness status | Is Fresh (True) | Stale (False) | Is Fresh (True) | Tập Corrupted dời ngày về 200 ngày trước khiến 100% dòng bị gắn nhãn Stale. |

### Kết luận từ số liệu

1. **[Data corruption] → [quality/freshness signal thay đổi] → [agent metric thay đổi]:**
   - Khi cố tình làm rỗng trường `summary` và dời ngày xuất bản, Great Expectations lập tức báo lỗi `Success = False`, Freshness báo 23/23 dòng trễ hạn. Việc thiếu thông tin ngữ cảnh khiến `Retrieval Hit Rate` sụt giảm từ **1.00 xuống 0.80** và `Mean Token F1` giảm từ **0.52 xuống 0.37**.

2. **[Repair action] → [quality/freshness signal phục hồi] → [agent metric phục hồi hoặc chưa phục hồi]:**
   - Hành động tự động kéo lại bản ghi thô chuẩn và chạy lại Data Cleaning đã giúp khôi phục Data Quality (`Success = True`). Ngay lập tức, `Retrieval Hit Rate` phục hồi về **1.00** và `Mean Token F1` quay trở lại mức **0.52**.

**Corruption nào ảnh hưởng rõ nhất và vì sao?**
- Việc **xóa rỗng trường `summary` (Empty Abstract)** ảnh hưởng nặng nề nhất đến hiệu năng của RAG Agent. Lý do là vì Vector Database sử dụng chuỗi `title + summary` để tính toán embedding. Khi `summary` bị rỗng, thông tin ngữ cảnh cốt lõi bị mất hoàn toàn, khiến câu trả lời của LLM bị suy thoái nặng nề (Hallucination hoặc trả lời chung chung).

**Kết quả nào khác với kỳ vọng ban đầu?**
- Kỳ vọng ban đầu là khi dữ liệu trễ hạn (`stale`), chỉ số `Retrieval Hit Rate` sẽ giảm. Tuy nhiên thực tế thực nghiệm cho thấy ngày xuất bản bị cũ không làm giảm `Hit Rate` (vì vector embedding dựa trên ngữ nghĩa văn bản), nhưng nó kích hoạt Cảnh báo độ tươi (`Freshness Alert`), giúp Data Engineer ngăn chặn dữ liệu lỗi thời trước khi nó gây ảnh hưởng tới người dùng cuối.

---

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Về Data Pipeline:** Pipeline xử lý dữ liệu cần có tính chất Idempotent (chạy lại nhiều lần cho ra cùng kết quả) và khả năng lưu trữ Snapshot thô để sẵn sàng cho việc khôi phục tự động (Automated Repair) khi gặp sự cố.
2. **Về Data Quality/Observability:** Kiểm tra dữ liệu (Observability) phải được thực thi tự động ngay trên luồng trung chuyển (In-flight Data Check), kết hợp cả Schema Validation (Great Expectations) và Timeliness Monitoring (Freshness).
3. **Về ảnh hưởng của Data đến RAG Agent:** "Garbage in, Garbage out" — Mô hình LLM hay Vector Search tiên tiến đến đâu cũng sẽ thất bại nếu dữ liệu đầu vào bị khuyết thiếu, nhiễu thẻ HTML hoặc mất ngữ cảnh.

### Nếu có thêm thời gian
- Thiết lập cơ chế **Dead Letter Queue (DLQ)** để tự động cô lập riêng các bản ghi lỗi thay vì phải chạy lại toàn bộ dữ liệu, đồng thời tích hợp thông báo qua Slack/Telegram Webhook khi Quality Check bị thất bại.

---

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** [Họ và tên]  
**Ngày xác nhận:** 2026-09-25
