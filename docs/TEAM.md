# Danh Sách Thành Viên & Báo Cáo Phân Công Nhóm

- **Tên Nhóm:** `Friday-25th`
- **Mã Nhóm / Lớp:** `K4-L3-DAY10`
- **Tên Repository Nộp Bài:** https://github.com/hoanganhb680-arch/K4-L3A-Day10-Data-Pipeline-Data-Observability

---

## # Thành viên

| STT | Họ và tên | MSSV | Email | Vai trò & Phân công công việc | Báo cáo cá nhân |
|---:|---|---|---|---|---|
| 1 | Bùi Hoàng Anh | 2A202602697 | | Pipeline Lead & Integrator (`core/config.py`, `pipelines/phase1.py`, `pipelines/corruption_flow.py`, final reporting) | `report/2A202602697-BuiHoangAnh.md` |
| 2 | Tạ Văn Tuấn | 2A202602806 | | Data Foundation & Recovery (`crossref.py`, `cleaning.py`, raw lineage, idempotent repair) | `report/2A202602806-TaVanTuan.md` |
| 3 | Nguyễn Mai Hoàng Thiện | 2A202602912 | | Observability / Evaluation / Data Engineering (`quality.py` GX 1.x, `testset.py`, corruption validation) | `report/2A202602912-NguyenMaiHoangThien.md` |

---

## # Cá nhân

### BuiHoangAnh-2A202602697
- **Vai trò:** Pipeline Lead & Integrator.
- **Công việc chi tiết đã hoàn thành:**
  - Thiết lập cấu hình hệ thống `core/config.py` và đường dẫn artifacts `core/utils.py`.
  - Kết nối luồng thực thi trong `src/pipelines/phase1.py` và `src/pipelines/corruption_flow.py`.
  - Chuyển import SDK LLM thành lazy, bổ sung heuristic judge để pipeline chạy offline khi chưa có API key.
  - Kiểm tra tính nhất quán của artifacts và theo dõi Contributor tracking trên GitHub nhánh `main`.
- **Điều học được / Đóng góp chính:**
  - Thiết kế Idempotent Pipeline, quản lý trạng thái luồng dữ liệu đa tầng và dependency tùy chọn.

### TaVanTuan-2A202602806
- **Vai trò:** Phụ trách Ingestion, Làm sạch & Phục hồi dữ liệu.
- **Công việc chi tiết đã hoàn thành:**
  - Xây dựng module thu thập Crossref API với cơ chế fallback offline trong `src/ingestion/crossref.py`.
  - Chuẩn hóa schema, tính toán trường `age_days` và `text_for_embedding` trong `src/ingestion/cleaning.py`.
  - Thực thi cơ chế Idempotent Repair phục hồi dữ liệu từ raw snapshot.
- **Điều học được / Đóng góp chính:**
  - Kỹ thuật truy vết nguồn gốc dữ liệu (Data Lineage) và bảo toàn raw snapshot trước khi biến đổi.

### NguyenMaiHoangThien-2A202602912
- **Vai trò:** Data Engineer & Data Observability Specialist.
- **Công việc chi tiết đã hoàn thành:**
  - Thiết lập Quality Gate theo chuẩn **Great Expectations 1.x** (ephemeral context) và giám sát Freshness SLA trong `src/observability/quality.py`.
  - Xây dựng bộ câu hỏi đánh giá benchmark trong `src/evaluation/testset.py`.
  - Giả lập sự cố dữ liệu và xác minh pipeline repair trong `src/ingestion/corruption.py`, `src/pipelines/corruption_flow.py`.
- **Điều học được / Đóng góp chính:**
  - Kết hợp Schema Validation (Great Expectations) và Timeliness Monitoring (Freshness) để chặn Silent Failure trước khi dữ liệu vào serving layer.