# Template Alert và Runbook

Mỗi alert phải dựa trên triệu chứng người dùng hoặc SLO, không dựa trực tiếp vào tên implementation nội bộ.

## Alert 1

- Tên: `user_visible_high_latency`
- Severity: warning
- Duration: 5 phút
- Kênh thông báo: Slack `#llmops-alerts`
- SLI/SLO liên quan: tỷ lệ request thành công trong 3.000 ms của SLO `fast_successful_requests`.
- Điều kiện và thời gian duy trì: latency P95 lớn hơn 3.000 ms liên tục 5 phút.
- Ảnh hưởng tới người dùng: ít nhất 5% request có thời gian chờ vượt ngưỡng trải nghiệm cho phép.
- Ba bước kiểm tra đầu tiên:
  1. Xác nhận P50/P95/P99 và TTFT trên dashboard để phân biệt nghẽn toàn hệ thống với tail latency.
  2. Lọc `response_sent` chậm trong cùng cửa sổ, lấy `correlation_id` đại diện.
  3. Mở trace cùng ID, so sánh thời lượng retrieval và generation.
- Mitigation tạm thời: giảm concurrency, chuyển traffic sang prompt/model ổn định hoặc tạm bỏ retrieval không thiết yếu tùy span gây chậm.
- Owner: `llm-platform-oncall`

## Alert 2

- Tên: `elevated_request_error_rate`
- Severity: critical
- Duration: 5 phút
- Kênh thông báo: Slack `#llmops-alerts`
- SLI/SLO liên quan: successful-request ratio và guardrail error rate tối đa 2%.
- Điều kiện và thời gian duy trì: `request_failed / request_received > 2%` liên tục 5 phút.
- Ảnh hưởng tới người dùng: request trả lỗi thay vì câu trả lời.
- Ba bước kiểm tra đầu tiên:
  1. Xem breakdown `error_type` và thời điểm tỷ lệ lỗi bắt đầu tăng.
  2. Lấy `correlation_id` từ một `request_failed` trong cửa sổ đó.
  3. Mở trace tương ứng để xác định retrieval hay generation là span lỗi.
- Mitigation tạm thời: rollback thay đổi gần nhất; nếu retrieval lỗi, bật fallback không-RAG hoặc circuit breaker trong khi phục hồi dependency.
- Owner: `api-oncall`

## Alert 3

- Tên: `degraded_retrieval_success`
- Severity: warning
- Duration: 10 phút
- Kênh thông báo: Slack `#llmops-alerts`
- SLI/SLO liên quan: guardrail retrieval success tối thiểu 90% và quality proxy.
- Điều kiện và thời gian duy trì: retrieval success thấp hơn 90% liên tục 10 phút.
- Ảnh hưởng tới người dùng: câu trả lời có thể thiếu context, sai chính sách hoặc request lỗi hoàn toàn.
- Ba bước kiểm tra đầu tiên:
  1. So sánh retrieval success với error rate và quality score trong cùng cửa sổ.
  2. Lọc log `tool_name=retrieval`, lấy một ID thất bại và một ID thành công để đối chiếu.
  3. So sánh retrieval observation của hai trace, gồm thời lượng, trạng thái và số document.
- Mitigation tạm thời: dùng corpus/cache dự phòng, tạm trả lời có cảnh báo khi không có context và giới hạn retry để tránh tăng latency.
- Owner: `rag-oncall`
