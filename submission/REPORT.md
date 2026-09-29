# Báo cáo cá nhân — K4-L3A Day 13 Monitoring & LLMOps

> Mỗi học viên hoàn thiện một file duy nhất này. Khi dẫn evidence, dùng đường dẫn tương đối, ví dụ `evidence/07-trace-waterfall.png`.

## 1. Thông tin học viên

- **Họ và tên: Nguyễn Lê Phúc Thắng**
- **MSSV:** 2A202602638
- **Lớp:** K4-L3A
- **Repository URL:** Chưa tạo repo cá nhân
- **Commit SHA cuối:** Điền sau commit cuối
- **Challenge ID:** Chưa được Lab Coach release
- **Tên project Langfuse cá nhân:** `day13-k4-l3a-2A202602638`

## 2. Evidence index

Điền đúng đường dẫn tới evidence thực tế. Có thể đổi tên hoặc dùng nhiều ảnh nếu cần.

Baseline được tái dựng từ starter commit `13b6066` trong thư mục tạm cô lập;
output đầy đủ nằm tại `evidence/00-baseline-reconstructed.txt`.

| Evidence | Đường dẫn |
|---|---|
| Pytest cuối | `evidence/01-pytest.txt` |
| Log validator | `evidence/02-log-validator.txt` |
| Dashboard validator | `evidence/03-dashboard-validator.txt` |
| Structured log | `evidence/04-structured-log.txt` |
| PII redaction | `evidence/05-pii-redaction.txt` |
| Trace list | `evidence/06-trace-list.png` |
| Trace waterfall | `evidence/07-trace-waterfall.png` |
| Trace metadata | `evidence/08-trace-metadata.png`, `evidence/08a-root-observation.png`, `evidence/08-trace-metadata.txt` |
| Prompt versions | `evidence/09-prompt-versions.png` |
| Prompt rollback | `evidence/10-prompt-rollback.png`, `evidence/10-prompt-rollback.txt` |
| Dashboard runtime | `evidence/11-dashboard-overview.png` |
| Incident metric | `evidence/12-incident-metric.png` |
| Incident log | `evidence/13-incident-log.png` |
| Incident trace | `evidence/14-incident-trace.png` |

## 3. Kết quả kỹ thuật

| Nội dung | Baseline | Kết quả cuối | Nhận xét |
|---|---|---|---|
| `validate_logs.py` | 30/100 | 100/100 | Baseline thiếu correlation/enrichment; final không thiếu trường và có 10 correlation ID |
| `validate_dashboard.py` | 6/6 panel | 6/6 panel | Starter đã có contract; final bổ sung dashboard runtime đọc trực tiếp `data/logs.jsonl` |
| `pytest` | 22 passed | 26 passed | Bổ sung test correlation ID, dashboard runtime và PII |
| Số traces hợp lệ | 0 | ≥10 | Final workload có 10 root traces và 30 observations |
| Số PII leak | 0 | 0 | Validator độc lập kiểm tra email/phone/CCCD/card; final bổ sung scrub toàn event |
| Latency P95 / TTFT P95 | 165 ms / 51 ms | 990 ms / 50 ms | Baseline không gọi Langfuse; final có managed-prompt/tracing network nhưng vẫn dưới SLO 3,000 ms |
| Retrieval success rate | 100% | 100% | 10/10 retrieval thành công ở cả hai lượt |

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:** Middleware xóa contextvars ở đầu mỗi request, giữ `x-request-id` nếu đúng format `req-<8-hex>`, nếu không sẽ sinh ID mới bằng UUID. ID được bind vào structlog, lưu trong `request.state` và trả lại ở header `x-request-id`; response còn có `x-response-time-ms`.
- **Các metadata được ghi vào structured log:** `correlation_id`, `user_id_hash`, `session_id`, `feature`, `model`, `env`, trace/prompt metadata, latency, TTFT, tokens, cost, quality và trạng thái retrieval.
- **Cách bảo đảm PII được scrub trước khi ghi:** `scrub_event` đệ quy toàn bộ event và được đặt trước `JsonlFileProcessor` lẫn JSON renderer. User ID chỉ ghi dưới dạng SHA-256 rút gọn; prompt/trace chỉ nhận dữ liệu đã scrub hoặc preview.
- **Cách kiểm chứng kết quả:** Final workload chứa email, số điện thoại và thẻ mẫu; log hiện marker redaction và validator báo 0 PII leak, 100/100.

## 5. Tracing và prompt versioning

- **Cách xác nhận traces do chính tôi tạo trong project cá nhân:** Workload được chạy với key của project `day13-k4-l3a-2A202602638`; ảnh trace list cho thấy 10 root agent, 10 retrieval và 10 generation observations của final workload.
- **Cấu trúc root/retrieval/generation observations:** `lab-agent-run` là root agent; `retrieval` và `llm-generation` là hai child observations. Generation chứa model, managed prompt, TTFT, input/output tokens và cost.
- **Cách nối trace với log:** `correlation_id` có trong structured log và metadata của cả trace/retrieval/generation; `response_sent` còn ghi trực tiếp `trace_id`.
- **Prompt name:** `day13-chat`
- **Version/label baseline:** v1 — `baseline`, `production` (trạng thái cuối sau rollback)
- **Version/label candidate:** v2 — `candidate`, `latest`
- **Trace ID của mỗi version:** candidate v2 `323d01d3b23f301b13f291b852265fa8`; production v2 `ddb0a73c27234204b3cfccbf7ce50ac8`; production v1 sau rollback `60536317e5cfb31709825e9442b5e420`.
- **Cách promote và rollback `production`:** Chuyển `production` từ v1 sang v2, chạy cùng input và xác nhận trace v2; sau đó chuyển label về v1, chạy lại và xác nhận trace v1. Evidence API nằm tại `evidence/10-prompt-rollback.txt`.

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:** Endpoint `/dashboard` đọc log của 60 phút gần nhất, refresh 30 giây và hiển thị latency/TTFT, traffic, error/retrieval, cost, tokens và quality cùng đơn vị/threshold. Final: P95 990 ms, TTFT P95 50 ms, 0% error, retrieval 100%, cost $0.0224, 1,767 tokens, quality 0.88.
- **SLO và lý do chọn:** 99.5% request phải thành công trong tối đa 3,000 ms trên cửa sổ 28 ngày. Ngưỡng này đo trực tiếp trải nghiệm người dùng và được dùng nhất quán trong dashboard/alert.
- **Cách tính error budget:** 0.5% tổng request; với 10,000 request cho phép 50 bad events. Quy đổi liên tục tương đương 3 giờ 21 phút 36 giây trong 28 ngày.
- **Ba alert và runbook tương ứng:** P95 >3,000 ms trong 5 phút; error rate >2% trong 5 phút; retrieval success <90% trong 10 phút. Tất cả gửi Slack `#llmops-alerts`, có severity, owner, ba bước điều tra và mitigation trong `docs/alerts.md`.

## 7. Điều tra challenge

- **Challenge ID:** Chưa được Lab Coach release
- **Khoảng thời gian điều tra:** Chờ challenge chính thức
- **Triệu chứng từ metrics:** Chờ challenge chính thức
- **Log line và correlation ID liên quan:** Chờ challenge chính thức
- **Trace ID và span gây ảnh hưởng:** Chờ challenge chính thức
- **Root cause:** Chờ challenge chính thức
- **Fix action:** Chờ challenge chính thức
- **Preventive measure:** Chờ challenge chính thức

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:** Scrub đệ quy toàn bộ event ngay trước file/JSON output thay vì chỉ scrub `payload`; cách này giữ an toàn khi schema log được mở rộng và tránh field mới vô tình bỏ qua PII processor.
- **Một lỗi/blocker đã gặp:** Regex passport ban đầu có thể bắt nhầm phần hex của correlation ID; lần chạy sandbox đầu tiên cũng không kết nối được Langfuse Cloud.
- **Cách tìm nguyên nhân và xử lý:** Đối chiếu log runtime phát hiện ID bị biến đổi, sau đó yêu cầu keyword `passport` trong regex và thêm regression test. Workload Cloud được chạy lại khi có network access, sau đó kiểm tra observations qua Langfuse API v2.
- **Cách hiểu luồng Metrics → Logs → Traces:** Metrics xác định loại triệu chứng và cửa sổ thời gian; structured log lọc ra request cụ thể cùng `correlation_id`; trace cùng ID cho biết retrieval hay generation là span chậm/lỗi, từ đó mới kết luận root cause.
- **Vai trò của prompt version, token/cost, SLO hoặc rollback trong vận hành LLM:** Prompt version cho biết chính xác logic nào phục vụ request; token/cost kiểm soát chi phí; SLO biến trải nghiệm thành mục tiêu đo được; rollback label giúp quay lại prompt ổn định mà không đổi source/deploy lại ứng dụng.
- **Điều quan trọng nhất đã học:** Một tín hiệu riêng lẻ không đủ để điều tra; correlation giữa metric, log và trace mới tạo thành bằng chứng vận hành.
- **Hạn chế hoặc phần chưa hoàn thành, nếu có:** Chưa có challenge chính thức, họ tên/repository URL/commit SHA cuối và ba evidence incident. Baseline không được chụp tại thời điểm trước khi sửa; số liệu baseline trong bảng được tái dựng minh bạch từ đúng starter commit `13b6066` và lưu output riêng.

## 9. Checklist trước khi nộp

- [ ] Kết quả và evidence thuộc commit SHA cuối.
- [x] Tất cả ảnh/output hiện có mở được bằng đường dẫn tương đối.
- [ ] Incident evidence nối đúng metric → log → trace.
- [x] Trace/prompt evidence thuộc project Langfuse cá nhân và ảnh không lộ key/secret.
- [x] Repository chạy lại được theo README.
- [x] Không có secret, API key, PII thô hoặc evidence của người khác/lớp khác.
- [ ] URL repo và commit SHA cuối đã được nộp trên LMS/Codelabs.
