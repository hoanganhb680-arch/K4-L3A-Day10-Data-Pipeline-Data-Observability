# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Tạ Văn Tuấn                |
| MSSV               | 2A202602806                |
| Khóa/Lớp         | K4-L3-DAY10                 |
| Tên nhóm         | Friday-25th          |
| Vai trò chính    | Data Foundation & Recovery  |
| Repository         | <https://github.com/hoanganhb680-arch/K4-L3A-Day10-Data-Pipeline-Data-Observability>         |
| Ngày hoàn thành | 2026-09-25                  |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Raw ingestion | `ingestion/crossref.py` — `parse_crossref_payload`, `fetch_source_records`, `load_raw_records` | Crossref API response / local snapshot | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` (24 records) | Hoàn thành |
| Cleaning & data modeling | `ingestion/cleaning.py` — `build_clean_dataframe`, `rebuild_derived_columns` | 24 PaperRecord thô | `data/clean/papers_clean.csv/.json` với `age_days`, `text_for_embedding` | Hoàn thành |
| Data recovery | quy trình repair trong `pipelines/corruption_flow.py` | `data/raw/crossref_records.json` | `data/clean/papers_clean_repaired.csv/.json` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| ------------------------------------ | ------------------------------------ | ---------------------------- |
| Kiểm tra dữ liệu repair đúng với baseline | `pipelines/corruption_flow.py`, Pipeline Integrator | repaired bằng baseline, 24 dòng sạch |
| Xác minh raw lineage qua hash | `core/utils.py` (`file_sha256`) | hash raw/clean/test set khớp 3 trạng thái |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Parse Crossref payload, loại JATS/HTML tag | `ingestion/crossref.py` | 24 records hợp lệ, không crash field thiếu | unittest parser pass |
| Làm sạch, dedup, tính age_days và text_for_embedding | `ingestion/cleaning.py` | 24 dòng sạch, paper_id unique | unittest cleaning pass |
| Idempotent repair từ raw | `pipelines/corruption_flow.py` | repaired metrics khớp baseline | `repaired_metrics.json` hit_rate=1.0 |

Output cụ thể: `data/clean/papers_clean.csv` có đúng schema 16 cột (gồm `age_days`, `summary_chars`, `text_for_embedding`), `paper_id` unique, ngày `published` nằm trong 2026-03-28 đến 2026-07-22.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Chuyển dữ liệu Crossref metadata lộn xộn (optional field, JATS/HTML/XML tag, whitespace, ngày tháng thiếu) thành dataset sạch, có định danh ổn định và đủ cột phục vụ embedding/evaluation, đồng thời bảo toàn bản raw để có thể phục hồi khi dữ liệu bị hỏng.

### Cách triển khai

- `parse_crossref_payload`: đọc `message.items`, trích `DOI` làm `paper_id`, `title[0]`, loại tag bằng regex `<[^>]*>` cộng `html.unescape`, normalize whitespace, map `subject` thành `categories`, chọn ngày từ `published`/`published-online`/`issued`/`created`.
- `fetch_source_records`: ưu tiên snapshot, chỉ gọi Crossref live khi `REFRESH_SOURCE`; dùng `Retry` cho 429/5xx và fallback snapshot nếu lỗi, đồng thời ghi lại raw response/records để giữ lineage.
- `build_clean_dataframe`: normalize text/date, drop record thiếu `paper_id`/`title`/`published`, nối tác giả/chuyên ngành, tính `age_days = (run_date - published).days`, ghép `text_for_embedding` theo đúng 5 phần, dedup theo `paper_id` và sort deterministic.

### Input, output và contract

| Thành phần | Mô tả |
| ------------------------------ | ------------------------------------------- |
| Input | Crossref raw response / list[PaperRecord] / raw records JSON |
| Output | list[PaperRecord] / DataFrame sạch 16 cột |
| Module phụ thuộc | `core.config`, `core.utils` |
| Module sử dụng output | `retrieval/index.py`, `observability/quality.py`, `evaluation/testset.py`, `pipelines/*` |
| Điều kiện lỗi cần xử lý | field thiếu, JSON rỗng, publish date không hợp lệ, snapshot missing khi live fail |

### Cách xác minh

```bash
uv run python -m unittest discover -s tests -v
uv run python script/run_phase1.py
uv run python script/run_corruption_flow.py
```

- **Kết quả mong đợi:** 24 record sạch, quality PASS, repair khôi phục đúng baseline.
- **Kết quả thực tế:** 24 dòng, paper_id unique, baseline quality PASS, corrupted quality FAIL, repaired quality PASS.
- **Artifact/log:** `data/raw/crossref_records.json`, `data/clean/papers_clean.csv`, `data/quality/*.json` (không chứa secret).

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Chọn cách xử lý `published_date` khi Crossref trả nhiều trường ngày khác nhau và có thể thiếu.
- **Các phương án đã cân nhắc:** (1) chỉ lấy `created` duy nhất; (2) lấy trường đầu tiên theo thứ tự ưu tiên.
- **Phương án đã chọn:** Dùng thứ tự `published`, `published-online`, `published-print`, `issued`, `created`, chuẩn hóa về `YYYY-MM-DD`, fallback chuỗi rỗng.
- **Lý do:** Ngày có ý nghĩa xuất bản nhất, đồng thời an toàn với record không đủ field.
- **Bằng chứng quyết định phù hợp:** unittest parser pass, age_days tính đúng, freshness baseline fresh (4.17% stale).

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `.venv\Scripts\python.exe -c "import chromadb"` báo `ModuleNotFoundError: No module named 'chromadb'`.
- **Lệnh hoặc bước tái hiện:** mở PowerShell, import ba thư viện trong `.venv`.
- **Nguyên nhân gốc:** venv được tạo bằng `uv` nhưng chưa chạy `uv sync`, package chưa được cài (torch 117MiB + 180 package).
- **Cách xử lý:** chạy `uv sync`, dùng `uv run python ...` để chạy pipeline.
- **Cách xác minh sau khi sửa:** import in `env ready`; cả hai pipeline exit 0.
- **Điều học được:** Đồng bộ môi trường bằng lockfile trước khi debug, tránh nhầm lỗi import với lỗi logic.

## 7. Hiểu biết về luồng end-to-end

1. Dữ liệu Crossref (API hoặc snapshot) được parse thành PaperRecord rồi lưu raw JSON; qua `build_clean_dataframe` tạo dataset sạch có `age_days` và `text_for_embedding`; MiniLM embedding rồi nạp vào ChromaDB collection tạo vector index.
2. Test set có `ground_truth_doc_ids` (DOI). Mỗi câu pipeline truy xuất doc từ index và so `retrieved_doc_ids` với ground truth để tính hit rate; câu trả lời so với `ground_truth` để tính token F1 và judge score.
3. Quality checks (GX) kiểm tra cấu trúc/schema (null, unique, length, row count); freshness monitoring theo dõi độ tươi của `published` qua `age_days` và ngưỡng 180 ngày.
4. Dùng cùng test set để so sánh công bằng; đổi test set thì chênh lệch metric không còn phản ánh đúng tác động corruption/repair.
5. Repair thành công khi nạp lại raw, re-clean ra dataset bằng baseline, quality PASS, freshness fresh và metrics quay về xấp xỉ baseline.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` | 1.0 | 0.7 | 1.0 | drop/noise/dup làm mất 3 câu, repair phục hồi hoàn toàn |
| `mean_token_f1` | 1.0 | 0.6 | 1.0 | blank summary + truncate title làm answer lệch |
| `judge_accuracy` | 1.0 | 0.6 | 1.0 | judge heuristic tỉ lệ thuận với token F1 |
| `mean_judge_score` | 5.0 | 3.4 | 5.0 | điểm giảm đúng kỳ vọng |
| Quality checks | PASS | FAIL | PASS | unique/summary/title detect đúng corruption |
| Freshness status | Fresh | Stale | Fresh | 4.17% > 47.62% > 4.17% |

### Kết luận từ số liệu

1. Data corruption (blank summary + truncate title + duplicate + stale date + drop + noise) tạo Quality Gate FAIL + Freshness Stale (47.62%), làm retrieval hit rate tụt 1.0 xuống 0.7, token F1 1.0 xuống 0.6.
2. Repair (reload raw + re-clean) tạo Quality PASS + Freshness Fresh (4.17%), làm hit rate 0.7 quay lại 1.0, token F1 0.6 quay lại 1.0.

Corruption nào ảnh hưởng rõ nhất và vì sao?
Trên dữ liệu thực tế, kết hợp `blank_summary`, `truncate_title` và `duplicate_rows` ảnh hưởng rõ nhất vì chúng phá vỡ QA path (summary trống làm mất câu trả lời, title bị cắt làm lookup lệch, duplicate làm loãng retrieval). Đây là combined experiment nên tách riêng cần ablation run.

Kết quả nào khác với kỳ vọng ban đầu?
Mong đợi khác biệt rõ hơn ở từng loại câu, nhưng do QA dùng exact-title lookup nên một số câu vẫn đúng dù record khác hỏng, điều này giải thích hit rate chỉ tụt về 0.7 thay vì thấp hơn.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Data pipeline phải bảo toàn raw snapshot, đó là nguồn duy nhất để repair idempotent và truy vết lineage.
2. Observability (GX quality + freshness) là cần thiết vì lỗi dữ liệu là "silent failure", agent vẫn trả lời tự tin dù dữ liệu hỏng.
3. Cùng test set là điều kiện tiên quyết để mọi so sánh baseline/corrupted/repaired có ý nghĩa.

### Nếu có thêm thời gian

Chạy ablation từng corruption scenario để đo tác động riêng lẻ, và bật LLM judge thật (khi có API key) để so sánh judge heuristic với judge semantic.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Tạ Văn Tuấn
**Ngày xác nhận:** 2026-09-25
