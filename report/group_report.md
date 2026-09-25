# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Khóa/Lớp         | K4-L3-DAY10                 |
| Tên nhóm         | Friday-25th                 |
| Repository         | https://github.com/hoanganhb680-arch/K4-L3A-Day10-Data-Pipeline-Data-Observability |
| Ngày hoàn thành | 2026-09-25                  |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | Bùi Hoàng Anh | 2A202602697 | Pipeline Lead & Integrator | `core/`, `pipelines/phase1.py`, `pipelines/corruption_flow.py` |
| 2 | Tạ Văn Tuấn | 2A202602806 | Data Foundation & Recovery | `ingestion/crossref.py`, `ingestion/cleaning.py` |
| 3 | Nguyễn Mai Hoàng Thiện | 2A202602912 | Observability / Evaluation / Data Engineering | `observability/quality.py`, `evaluation/testset.py`, `observability/reporting.py` |

## 2. Tóm tắt kết quả

Nhóm đã hoàn thiện toàn bộ pipeline offline-first: nhập dữ liệu Crossref với cơ chế fallback snapshot, làm sạch chuẩn hóa 24 bản ghi thành `text_for_embedding`, kiểm tra chất lượng bằng Great Expectations 1.18.0 (12 expectations) và cảnh báo freshness (threshold 180 ngày), build 3 ChromaDB collection tách biệt, sinh bộ test set 10 câu cố định (3 summary, 3 authors, 2 date, 2 categories), và chạy đánh giá baseline trên provider mock.

Baseline tạo đầy đủ artifacts raw/clean/eval/quality/results/reports và đạt retrieval hit rate = 1.0, mean token F1 = 1.0, judge accuracy = 1.0, mean judge score = 5.0. Corruption suite tiêm đủ 6 kịch bản (drop latest, blank summary, inject noise, truncate title, stale date, duplicate rows). Sau corruption, Quality Gate chuyển thành FAIL (unique paper_id, summary length, title length) và freshness chuyển thành stale (47.62% hàng quá hạn); metrics tụt xuống hit rate 0.7, token F1 0.6, judge accuracy 0.6, judge score 3.4. Repair nạp lại từ `data/raw/crossref_records.json`, dùng lại đúng `build_clean_dataframe`, phục hồi hoàn toàn về 1.0/1.0/1.0/5.0.

Blocker quan trọng nhất: môi trường không có LLM API key, nên baseline/corrupted/repaired đều dùng provider `mock` (judge heuristic) và RAGAS được đặt skipped. Thông tin cá nhân của thành viên chưa có để điền.

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Crossref API (fallback snapshot data/raw/crossref_response.json)
    -> parse -> data/raw/crossref_records.json
    -> cleaning + data modeling (build_clean_dataframe)
    -> quality (GX 1.x) + freshness
    -> embedding (all-MiniLM-L6-v2) + ChromaDB papers-baseline
    -> evaluation baseline (test_set.json cố định)
    -> corruption (6 kịch bản) -> papers-corrupted + quality/freshness alert
    -> repair từ raw records -> papers-repaired
    -> comparison report (baseline vs corrupted vs repaired)
```

### Trách nhiệm của từng khối

| Khối             | Input          | Xử lý chính             | Output/artifact          | Owner          |
| ----------------- | -------------- | -------------------------- | ------------------------ | -------------- |
| Ingestion         | Crossref API / snapshot | Fetch, retry/backoff, parse, fallback | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` | Data Foundation |
| Cleaning          | raw records | normalize, dedup, `age_days`, `text_for_embedding` | `data/clean/papers_clean.csv/.json` | Data Foundation |
| Embedding/index   | clean df | MiniLM embedding + ChromaDB | `data/embeddings/*.json`, `data/chroma/` | RAG & Vector Index |
| Evaluation        | test set + index | hit rate, token F1, judge | `data/results/*_metrics.json`, `*_answers.json` | Observability & Evaluation |
| Observability     | clean/corrupted df | GX 1.x expectations + freshness | `data/quality/*.json` | Observability & Evaluation |
| Corruption/repair | clean df / raw | 6 kịch bản + idempotent repair | `corruption_log.json`, `*_repaired*` | Pipeline Integrator |
| Orchestration     | tất cả | thứ tự chạy, validation | `phase1_report.md`, `corruption_report.md` | Pipeline Integrator |

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình             | Giá trị sử dụng |
| ---------------------------- | ------------------- |
| `LLM_PROVIDER`             | mock |
| `LLM_MODEL`                | mock |
| Embedding model              | sentence-transformers/all-MiniLM-L6-v2 |
| Số lượng Crossref records | 24 |
| Retrieval `top_k`           | 4 |
| Freshness threshold          | 180 days |
| Random seed               | không dùng (deterministic positional slices) |

Không dán nội dung API key hoặc file `.env` vào báo cáo.

### Lệnh cài đặt

```bash
uv sync
```

### Lệnh chạy (đã cấu hình env offline trước khi chạy)

```powershell
$env:LLM_PROVIDER='mock'
$env:LLM_MODEL='mock'
$env:REFRESH_SOURCE='false'
$env:REFRESH_TEST_SET='false'
$env:RUN_RAGAS='false'
uv run python script/run_phase1.py
uv run python script/run_corruption_flow.py
```

### Kết quả tái hiện

| Lệnh             | Trạng thái                                    | Thời điểm chạy gần nhất | Bằng chứng                         |
| ----------------- | ----------------------------------------------- | ----------------------------- | ------------------------------------ |
| Baseline pipeline | Thành công (exit 0) | 2026-09-25 | `data/results/baseline_metrics.json`, `data/reports/phase1_report.md` |
| Corruption flow   | Thành công (exit 0) | 2026-09-25 | `data/results/corruption_log.json`, `data/results/corrupted_metrics.json`, `data/results/repaired_metrics.json`, `data/reports/corruption_report.md` |

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính                | Giá trị                             |
| --------------------------- | ------------------------------------- |
| Source                      | Crossref REST API (`api.crossref.org/works`) + preserved local response |
| Query/filter                | query `agentic retrieval augmented generation large language model`; filter `from-pub-date:2026-03-29,has-abstract:true` |
| Thời điểm lấy dữ liệu | snapshot preserved trong `data/raw/crossref_response.json` |
| Số record nhận được    | 24 |
| Cơ chế retry/backoff      | HTTPAdapter + Retry (total=3, backoff=1) cho 429/500/502/503/504; fallback snapshot khi lỗi |

### Raw và clean schema

Các trường của `PaperRecord` gồm: `paper_id` (DOI), `title`, `summary` (abstract sau khi loại JATS/HTML), `authors` (danh sách "given family"), `categories` (subject), `primary_category`, `published`, `updated`, `abs_url`, `pdf_url`, `comment`.

Clean dataframe bổ sung: `authors_joined`, `categories_joined`, `age_days`, `summary_chars`, `text_for_embedding`.

| Trường        | Kiểu dữ liệu | Bắt buộc?  | Ý nghĩa   | Xử lý khi thiếu/sai |
| --------------- | --------------- | ------------ | ----------- | ---------------------- |
| `paper_id` | string (DOI lowercase) | Có | định danh | loại record nếu rỗng; lowercase |
| `title` | string | Có | tiêu đề | loại record nếu rỗng; clean whitespace/JATS |
| `summary` | string | Không | tóm tắt | giữ; rỗng tiêu chuẩn |
| `published` | date string | Có | ngày xuất bản | loại record nếu không parse được |
| `authors`/`categories` | list[string] | Không | tác giả/chuyên ngành | dedup + clean; rỗng -> join thành "" |

### Quy tắc cleaning

| Quy tắc                                 | Quality dimension liên quan | Số record bị tác động | Cách xác minh      |
| ---------------------------------------- | ---------------------------- | -------------------------: | -------------------- |
| Loại JATS/HTML/XML tags + normalize whitespace | Validity/Consistency | 24 (toàn bộ) | `build_clean_dataframe` + unittest parser test |
| Loại record thiếu `paper_id`/`title`/`published` | Completeness | 0 trong snapshot (snapshot hợp lệ) | unittest cleaning test |
| Parse ngày an toàn, normalize `published`/`updated` | Validity | 24 | unittest cleaning test |
| Dedup theo `paper_id` | Uniqueness | 0 (snapshot không trùng) | assertion `first.paper_id.is_unique` |
| Tính `age_days = (run_date - published).days` | Freshness | 24 | assertion từng dòng |

`text_for_embedding` được tạo theo cấu trúc 5 phần `Title/Authors/Published/Categories/Summary`. Document ID dùng `${paper_id}::{index}`. `age_days` tính chênh lệch ngày giữa `run_date` (UTC, normalized) và `published` (UTC, normalized).

## 6. Evaluation setup

| Thành phần                             | Cấu hình thực tế          |
| ---------------------------------------- | ----------------------------- |
| Số câu hỏi                            | 10 |
| Các `question_type`                    | summary (3), authors (3), date (2), categories (2) |
| Ground-truth document ID                 | DOI trích từ `paper_id` của record tương ứng |
| Embedding model                          | sentence-transformers/all-MiniLM-L6-v2 |
| Vector store/collection                  | ChromaDB; `papers-baseline`, `papers-corrupted`, `papers-repaired` |
| Retrieval `top_k`                       | 4 |
| LLM provider/model                       | mock / mock |
| Test set dùng chung cho ba trạng thái | `data/eval/test_set.json` (SHA-256 `08ed9447...302321f6`) |

Vì sao test set giữ nguyên: baseline, corrupted và repaired phải được chấm trên cùng một bộ câu hỏi + ground truth để phép so sánh có ý nghĩa nguyên nhân–hệ quả. Pipeline kiểm tra SHA-256 test set ở mỗi lần chạy và chỉ tạo lại khi `REFRESH_TEST_SET=true`.

## 7. Kết quả baseline

### Artifact checklist

| Artifact                 | Đường dẫn thực tế                | Trạng thái | Ghi chú   |
| ------------------------ | -------------------------------------- | ------------ | ---------- |
| Raw response/records     | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` | Có | 24 records |
| Cleaned dataset          | `data/clean/papers_clean.csv/.json` | Có | 24 dòng |
| Embedding manifest/index | `data/embeddings/papers_embeddings.json`, `data/chroma/` | Có | collection `papers-baseline` 24 docs |
| Evaluation set           | `data/eval/test_set.json` | Có | 10 câu, 4 loại |
| Baseline metrics         | `data/results/baseline_metrics.json` | Có | hit rate etc. |
| Quality/freshness        | `data/quality/baseline_quality_report.json`, `data/quality/freshness_report.json` | Có | PASS / fresh |
| Baseline report          | `data/reports/phase1_report.md` | Có | report đầy đủ |

### Baseline metrics

| Metric                 |       Giá trị | Diễn giải                             |
| ---------------------- | --------------: | --------------------------------------- |
| `retrieval_hit_rate` |     1.0 | 10/10 câu truy xuất đúng ground-truth doc |
| `mean_token_f1`      |     1.0 | QA trích đúng metadata/câu đầu |
| `judge_accuracy`     |     1.0 | judge heuristic đúng 10/10 câu |
| `mean_judge_score`   |     5.0 | điểm judge trung bình tối đa |
| Ragas | skipped | `RUN_RAGAS=false`, ghi chú skipped hợp lệ |

## 8. Data quality và freshness

### Quality checks

Great Expectations `1.18.0`, 12 expectations, ephemeral context, syntax GX 1.x (`gx.get_context`, `add_pandas`, `add_dataframe_asset`, `add_batch_definition_whole_dataframe`).

| Check        | Quality dimension | Ngưỡng/kỳ vọng | Kết quả baseline      | Bằng chứng |
| ------------ | ----------------- | ------------------ | ----------------------- | ------------ |
| Row count | Completeness | 5–5000 | PASS (24) | `baseline_quality_report.json` |
| `paper_id`/`title`/`text_for_embedding`/`summary`/`age_days` not null | Completeness | non-null | PASS | `baseline_quality_report.json` |
| `paper_id` unique | Uniqueness | unique | PASS | `baseline_quality_report.json` |
| `summary` length >= 30 | Validity | min 30 | PASS | `baseline_quality_report.json` |
| `title` length >= 8 | Validity | min 8 | PASS | `baseline_quality_report.json` |
| `age_days` >= 0 | Freshness/Validity | >= 0 | PASS | `baseline_quality_report.json` |

### Freshness

| Thuộc tính               | Giá trị                           |
| -------------------------- | ----------------------------------- |
| Freshness được đo tại | cleaned dataset `data/clean/papers_clean.json` |
| Timestamp mới nhất       | 2026-07-22 |
| Ngưỡng freshness         | 180 days |
| Trạng thái baseline      | Fresh |
| Lý do                     | 1/24 (4.17%) stale <= 25% |

## 9. Corruption scenarios và repair

| Corruption         | Cách tạo | Record bị tác động | Quality signal kỳ vọng | Tác động thực tế | Cách repair   |
| ------------------ | ---------- | ---------------------: | ------------------------ | --------------------- | -------------- |
| drop_latest_records | bỏ 20% mới nhất | 5 | row count có thể giảm | 24 -> 19 dòng | reload raw |
| blank_summary | xóa summary | 3 | summary length FAIL | FAIL `summary` | reload raw |
| inject_noise | chèn `ZXQ_NOISE...` x5 | 3 | thay đổi content | ảnh hưởng embedding/retrieval | reload raw |
| truncate_title | cắt xuống 7 ký tự | 3 | title length FAIL | FAIL `title` | reload raw |
| stale_date | lùi 365 ngày | 8 | freshness stale | is_fresh = false (47.62%) | reload raw |
| duplicate_rows | nhân 2 dòng cuối | 2 | paper_id unique FAIL | FAIL `paper_id`, 21 dòng | reload raw |

Corruption log:

- Đường dẫn: `data/results/corruption_log.json`
- Trạng thái: Có
- Nhận xét: Log ghi đủ 6 loại corruption, `affected_records`, `paper_ids`, `parameters`, và before/after changes. `input_rows=24`, `output_rows=21`.

Repair nạp lại `data/raw/crossref_records.json` (trusted raw), gọi lại `build_clean_dataframe` — không sửa tay corrupted dataframe. Nhờ vậy repaired độc lập với corrupted và idempotent (chạy lại vẫn ra 24 dòng sạch, collection `papers-repaired` được reset trước khi build).

## 10. So sánh baseline, corrupted và repaired

| Metric/signal            | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi | Nhận xét   |
| ------------------------ | -------: | --------: | -------: | -----------------------: | --------------: | ------------ |
| `retrieval_hit_rate`   | 1.0 | 0.7 | 1.0 | -0.3 | 100% | 3 câu mất hit do drop/noise/dup |
| `mean_token_f1`        | 1.0 | 0.6 | 1.0 | -0.4 | 100% | answer lệch do summary/title hỏng |
| `judge_accuracy`       | 1.0 | 0.6 | 1.0 | -0.4 | 100% | judge theo token F1 |
| `mean_judge_score`     | 5.0 | 3.4 | 5.0 | -1.6 | 100% | judge score giảm |
| Quality checks pass/fail | PASS | FAIL | PASS | PASS->FAIL | phục hồi | unique/summary/title |
| Freshness status         | Fresh | Stale | Fresh | Fresh->Stale | phục hồi | 4.17% -> 47.62% -> 4.17% |

Kết luận nguyên nhân–hệ quả được hỗ trợ bởi artifacts:

1. Corruption (blank summary + truncate title + duplicate + stale date + drop + noise) -> Quality Gate FAIL (unique `paper_id`, `summary`, `title`) + Freshness Stale (47.62%) -> retrieval hit rate tụt 1.0 -> 0.7, token F1 1.0 -> 0.6.
2. Repair (reload raw + re-clean) -> Quality PASS + Freshness Fresh (4.17%) -> hit rate 0.7 -> 1.0, token F1 0.6 -> 1.0.

## 11. Vấn đề tích hợp quan trọng

- **Triệu chứng:** Môi trường `.venv` ban đầu trống (chỉ 3 package), `import chromadb` báo `ModuleNotFoundError`.
- **Nguyên nhân:** `uv sync` chưa từng được chạy ở môi trường này (torch 117MB + 180 package chưa tải).
- **Cách xử lý:** Chạy `uv sync`, chờ tải torch + 157 package cài thành công.
- **Cách xác minh:** `uv run python -c "import chromadb, great_expectations, sentence_transformers"` in `env ready`; sau đó cả hai pipeline exit 0.

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng   | Hướng cải thiện có thể kiểm chứng |
| --------------------- | -------------- | ----------------------------------------- |
| Provider `mock` + judge heuristic | judge không phản ánh semantic đầy đủ | bật LLM judge thật khi có API key |
| RAGAS skipped | thiếu nhóm metric RAG nâng cao | set `RUN_RAGAS=1` khi có LLM credential ổn định |
| Corruption là combined, không ablation riêng | không tách biệt tác động từng kịch bản | chạy từng scenario riêng để đo causal attribution |
| Snapshot cố định ngày `published` | freshness sẽ thành stale theo thời gian | pipeline đã giữ `run_date` từ baseline cho repair |

## 13. Checklist trước khi nộp

- [x] Thông tin nhóm và repository chính xác.
- [x] Phân công khớp với module, artifact và kết quả thực tế.
- [x] Lệnh tái hiện đã được chạy lại trên phiên bản dùng để nộp.
- [x] Baseline, corrupted và repaired dùng cùng evaluation set.
- [x] Bảng metrics khớp với các file trong `data/results/`.
- [x] Quality/freshness conclusions khớp với `data/quality/`.
- [x] Các đường dẫn báo cáo và artifact truy cập được.
- [x] Mỗi thành viên đã hoàn thành báo cáo vai trò riêng.
- [x] Không có `.env`, API key, token hoặc secret trong source, report, log hay ảnh.