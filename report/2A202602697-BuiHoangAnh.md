# Member Role Report - Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Bùi Hoàng Anh |
| MSSV | 2A202602697 |
| Khóa/Lớp | K4 |
| Tên nhóm | Friday-25th |
| Vai trò chính | Leader |
| Repository | https://github.com/hoanganhb680-arch/K4-L3A-Day10-Data-Pipeline-Data-Observability/tree/main |
| Ngày hoàn thành | 2026-09-25 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

Là leader của nhóm Friday-25th, tôi chịu trách nhiệm chính cho việc tích hợp toàn bộ pipeline và bảo đảm các pha chạy end-to-end.

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Cấu hình chung | `src/core/config.py` | `.env`, cấu hình project | `Settings`, các đường dẫn artifact | Hoàn thành |
| Baseline orchestration | `src/pipelines/phase1.py` | Raw records, clean dataset, embedding | `baseline_metrics.json`, `phase1_report.md` | Hoàn thành |
| Corruption/repair orchestration | `src/pipelines/corruption_flow.py` | Clean dataset, raw records | `corrupted_metrics.json`, `repaired_metrics.json`, `corruption_report.md` | Hoàn thành |
| Reporting | `src/observability/reporting.py` | Metrics, quality, freshness | Markdown report cho baseline và corruption | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Kiểm tra module contract | `ingestion`, `retrieval`, `evaluation`, `observability` | Toàn bộ pipeline chạy exit code 0 |
| Khắc phục import phụ thuộc | `retrieval`, `evaluation` | Pipeline không bị chặn bởi SDK LLM chưa cài |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Chạy baseline | `script/run_phase1.py` | `baseline_metrics.json` | `retrieval_hit_rate = 1.0` |
| Chạy corruption/repair | `script/run_corruption_flow.py` | Metrics 3 trạng thái | Bảng `Corrupted [0.7], Repaired [1.0]` |
| Kiểm định dữ liệu | `src/observability/quality.py` | `quality/freshness` | GX `success = true` ở baseline |
| Tổng hợp báo cáo | `src/observability/reporting.py` | `data/reports/*.md` | Exit code 0 |

Ví dụ output do phần việc của tôi kết nối: `data/reports/corruption_report.md` thể hiện Hit Rate giảm từ `1.000` xuống `0.700` khi dữ liệu bị lỗi và quay lại `1.000` sau repair.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Pipeline phải ghép nhiều module khác nhau: ingestion, cleaning, embedding, evaluation, quality/freshness và reporting, đồng thời phải chạy được cả khi chưa có API key hoặc SDK LLM.

### Cách triển khai

Tôi dùng cùng một `Settings` cho toàn bộ các khối, giữ contract qua `core/utils.py` và `core/config.py`. Phase 1 đọc bản ghi raw, tạo clean dataframe, build Chroma index, chạy evaluation trên bộ 10 câu, kiểm GX rồi ghi report. Corruption flow giữ test set cố định để so sánh công bằng giữa baseline, corrupted và repaired.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | `crossref_records.json`, `papers_clean.csv`, ChromaDB |
| Output | `baseline_metrics.json`, `corrupted_metrics.json`, `repaired_metrics.json`, Markdown report |
| Module phụ thuộc | `ingestion`, `retrieval`, `evaluation`, `observability` |
| Module sử dụng output | `reporting.py` |
| Điều kiện lỗi cần xử lý | Missing GUI/LLM SDK cũng phải có fallback judge |

### Cách xác minh

```powershell
.\.venv\Scripts\python.exe script\run_phase1.py
.\.venv\Scripts\python.exe script\run_corruption_flow.py
```

- **Kết quả mong đợi:** Câu lệnh chạy không lỗi, có đầy đủ metric ba trạng thái.
- **Kết quả thực tế:** Cả hai lệnh exit code 0; hit rate baseline/repaired `1.0`, corrupted `0.7`.
- **Artifact/log:** `data/results/*.json`, `data/reports/*.md`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Import `retrieval/__init__.py` ban đầu kéo theo `langchain_*` SDK, làm pipeline hỏng khi chưa cài provider.
- **Các phương án đã cân nhắc:** Cài hết SDK LLM, hoặc chuyển import sang lazy.
- **Phương án đã chọn:** Chuyển provider SDK thành lazy import và cho LLM judge dùng fallback token F1.
- **Lý do:** Pipeline vẫn chạy end-to-end để sinh đủ artifact khi chưa có API key, đồng thời giữ khả năng dùng provider thật khi cấu hình sau.
- **Bằng chứng quyết định phù hợp:** `run_phase1.py` và `run_corruption_flow.py` đều exit code 0, sinh đủ metrics.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng:** `ModuleNotFoundError: No module named 'langchain_anthropic'`.
- **Lệnh hoặc bước tái hiện:** `python script/run_phase1.py`.
- **Nguyên nhân gốc:** `build_llm` import SDK ở top-level, package chưa cài.
- **Cách xử lý:** Chuyển import vào từng nhánh provider, bổ sung fallback cho LLM judge.
- **Cách xác minh sau khi sửa:** Chạy lại `run_phase1.py`, exit code 0 và có `baseline_metrics.json`.
- **Điều học được:** Import module nặng nên để lazy để không biến dependency tùy chọn thành blocker.

## 7. Hiểu biết về luồng end-to-end

1. Dữ liệu đi từ Crossref API, được lưu raw, làm sạch, tạo `text_for_embedding`, encode bằng `all-MiniLM-L6-v2` rồi nạp vào ChromaDB.
2. Evaluation set gồm câu hỏi, ground truth và `ground_truth_doc_ids`; retrieval kiểm tra doc đúng có nằm trong top-k, còn token F1 kiểm tra độ tương đồng câu trả lời.
3. Quality checks đánh giá schema, null, unique, độ dài summary; freshness monitoring đo tỷ lệ bài quá 180 ngày.
4. Dùng cùng test set để baseline, corrupted và repaired khác biệt chỉ do trạng thái dữ liệu, phép so sánh mới có ý nghĩa.
5. Repair thành công khi đọc lại từ raw và cả quality/freshness lẫn metrics quay về giá trị baseline.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.000 | 0.700 | 1.000 | Đúng kỳ vọng: corruption làm sót tài liệu. |
| `mean_token_f1` | 1.000 | 0.600 | 1.000 | Answer quality giảm rõ rệt rồi phục hồi đầy đủ. |
| `judge_accuracy` | 1.000 | 0.600 | 1.000 | Judge fallback cho thấy mức suy giảm. |
| `mean_judge_score` | 5.000 | 3.400 | 5.000 | Đồng bộ với accuracy. |
| Quality checks | Pass | Fail | Pass | GX duy nhất metric cho corrupted. |
| Freshness status | Fresh | Not fresh | Fresh | Stale date làm trạng thái đổi rõ. |

### Kết luận từ số liệu

1. Data corruption → quality/freshness xuống → Hit Rate từ `1.000` còn `0.700`, F1 từ `1.000` còn `0.600`.
2. Repair từ raw → quality/freshness phục hồi → mọi metric trở về baseline.

Corruption ảnh hưởng rõ nhất là `stale_date` hoặc `duplicate_rows`, vì chúng làm freshness và uniqueness cùng lúc, tác động trực tiếp đến retrieval và answer.

Kết quả phục hồi hoàn toàn về baseline cũng là điều tôi muốn xác minh kỹ: repaired metrics phải bằng baseline chứ không chỉ tăng hơn corrupted.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Hiểu được từng mắt xích dữ liệu phải khớp schema trước khi ghép pipeline.
2. Quality gate và freshness giúp phát hiện silent failure trước khi RAG trả lời sai.
3. Data corruption ảnh hưởng rõ đến vector retrieval và chất lượng câu trả lời.

### Nếu có thêm thời gian

Tôi sẽ cấu hình thêm API key và bật `RUN_RAGAS=1` để bổ sung metric LLM-based, đồng thời viết pytest cho các module ingestion, cleaning, quality và retrieval nhằm tăng độ tin cậy khi refactor.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Bùi Hoàng Anh
**Ngày xác nhận:** 2026-09-25
