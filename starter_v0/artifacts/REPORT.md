# Day 03 Lab Report — Research Agent

## Team

- Team: **NhomVip201**
- Members: **Dobit25**
- Provider/model: **OpenRouter — `openai/gpt-4o-mini`**
- Final accepted artifact: **`v4-tools+p7dc4cb261b78+t6edf66e24b4a`**

---

# PHẦN A — Giới thiệu agent

## A1. Agent này làm được gì

Research Agent hỗ trợ tìm kiếm tin tức và nội dung mạng xã hội, lấy bài đăng từ một tài khoản cụ thể, đọc URL, tìm tài liệu nghiên cứu, hợp nhất các nguồn trùng lặp và trình bày kết quả thành bản tổng hợp. Agent có thể xử lý yêu cầu nhiều lượt, hỏi lại khi thiếu thông tin và yêu cầu xác nhận trước hành động gửi hoặc đăng nội dung.

**Link dùng thử (Cloudflare Quick Tunnel):**

> https://bracelet-pages-apollo-coordinate.trycloudflare.com

URL đã được kiểm tra ngày 10/11/2026: trang gốc trả HTTP 200 và `/_stcore/health` trả `200 ok`. Đây là quick tunnel tạm thời, chỉ hoạt động khi tiến trình Streamlit và Cloudflare Tunnel của nhóm còn chạy.

## A2. Tool agent có

| Tên tool | Làm được gì | Tool mới nhóm thêm? |
|---|---|---|
| `clarify` | Hỏi lại khi thiếu/mơ hồ thông tin hoặc cần xác nhận. | Không |
| `timeline` | Lấy bài đăng gần đây từ một tài khoản mạng xã hội cụ thể. | Không |
| `social_search` | Tìm bài đăng mạng xã hội theo từ khóa, theo Latest hoặc Top. | Không |
| `lookup` | Tìm kiếm web hoặc tin tức, có hỗ trợ khoảng thời gian. | Không |
| `fetch` | Đọc nội dung từ một URL cụ thể. | Không |
| `format` | Trình bày dữ liệu đã có thành digest. | Không |
| `papers` | Tìm bài nghiên cứu. | Không |
| `paper_text` | Lấy nội dung bài nghiên cứu. | Không |
| `policy` | Tìm trong tài liệu nội bộ. | Không |
| `send` | Gửi nội dung lên Telegram sau khi được xác nhận rõ ràng. | Không |
| `merge_sources` | Chuẩn hóa URL, loại bỏ nguồn trùng, hợp nhất metadata và ưu tiên đa dạng nguồn. | **Có** |

## A3. Câu hỏi mẫu để thử

1. Tìm các tin nổi bật về AI trong tháng này.
2. Lấy 4 bài đăng mới nhất của Sam Altman.
3. Đọc và tóm tắt bài viết tại URL này: `<URL>`.
4. Tìm cả tin tức web và bài đăng Twitter mới nhất về robotics.
5. Hợp nhất danh sách nguồn này và loại bỏ các URL trùng lặp.

---

# PHẦN B — Chi tiết và bằng chứng

## B1. Version Evidence

Metric trong bảng là `case_accuracy` của base suite. Mỗi phiên bản được giữ cùng run JSON để có thể kiểm tra lại prompt hash, tools hash, tool calls và failures.

| Version | Changed Artifact | Hypothesis | Metric Before | Metric After | Run File |
|---|---|---|---:|---:|---|
| v0 | Baseline prompt và tools | Đo năng lực ban đầu trước khi tối ưu. | N/A | 0.70 | `runs/v0_B_base_openrouter_20261110T100050478487.json` |
| v1 | `system_prompt.md` | Quy tắc hỏi lại và xác nhận trước side effect sẽ giảm việc tự đoán argument. | 0.70 | 0.85 | `runs/v1_B_base_openrouter_20261110T112938937086.json` |
| v2 | `system_prompt.md` | Routing rule chi tiết cho từng tool sẽ tăng routing và argument accuracy. | 0.85 | 0.70 | `runs/v2_B_base_openrouter_20261110T115320326647.json` |
| v3 | `tools.yaml` | Contract loại trừ lẫn nhau và `clarify.response_type` bắt buộc sẽ giảm nhầm tool/argument. | 0.70 | 0.90 | `runs/v3_B_base_openrouter_20261110T120703099406.json` |
| v4 | `system_prompt.md` | Latest correction, constraint carry-over và source switching rõ ràng sẽ cải thiện multi-turn. | 0.90 | **0.95** | `runs/v4_B_base_openrouter_20261110T124457932043.json` |
| v4-tools | `tools.yaml` | Description chi tiết hơn cho format, merge, policy và paper tools sẽ giữ routing hiện tại đồng thời giảm ranh giới mơ hồ. | 0.95 | **0.95** | `runs/v4-tools_B_base_openrouter_20261110T192957943326.json` |

V2 là một regression được giữ lại làm bằng chứng: prompt dài và chi tiết hơn không tự động làm routing tốt hơn. Sau khi đọc log, nhóm chuyển phần contract phù hợp sang tool declaration ở v3, giúp base accuracy tăng từ 0.70 lên 0.90. V4 chỉ bổ sung các quy tắc quản lý trạng thái hội thoại và đạt 19/20 base cases, routing accuracy 1.00, argument accuracy 0.95 và multi-turn accuracy 1.00. Bản `v4-tools` giữ nguyên system prompt v4, làm rõ thêm contract của nhóm research/format tools và giữ nguyên toàn bộ base metrics, không có provider error.

## B2. Failure Analysis

| Case ID | Failure Type | Actual Tool Calls | What Failed | Fix/Status |
|---|---|---|---|---|
| `R12_confirm_before_send` | `wrong_boundary` / `wrong_arg_value` | `clarify(response_type="text")` | Đúng tool nhưng dùng text thay vì yes/no trước hành động đăng. | Làm rõ confirmation contract trong prompt/tools; v4 vẫn còn residual failure này. |
| `M06_switch_tool` | `wrong_tool` / `extra_tool_call` | `lookup` + `social_search` | User đã bỏ Twitter nhưng model vẫn gọi lại nguồn social cũ. | V4 quy định source mới ghi đè source bị loại bỏ; case đã PASS. |
| `G08_carryover_month` | `wrong_arg_value` | `lookup(topic="general")` + `social_search` | Không giữ đúng `topic=news` và gọi thêm nguồn social. | Giữ case làm regression evidence; group v4 vẫn FAIL case này. |
| `G09_correct_handle_and_limit` | `wrong_arg_value` | `timeline(screenname="elonmusk", limit=3)` | Limit mới được áp dụng nhưng handle correction mới nhất bị bỏ qua. | V4 thêm latest-value override và canonical handle; case đã PASS. |
| Các run đầu | `missing_tool_call` | Không gọi tool phù hợp để gộp nguồn | Agent thiếu capability chuẩn hóa và gộp danh sách nguồn trùng. | Thêm `merge_sources`, TOOL.md, đăng ký tool, test và case `G01`; case đã PASS. |

Hai lỗi còn lại của v4 được giữ nguyên trong evidence, không sửa expected sau khi xem kết quả. Điều này giúp báo cáo phản ánh đúng giới hạn hiện tại của model.

## B3. Team Eval Cases

Dataset `data/eval_group.json` có đúng **10 cases: 5 single-turn và 5 multi-turn**. Tool mới được kiểm tra trực tiếp bởi `G01`.

| Case ID | Loại | What It Tests | Expected Tool/Behavior | v4-tools Result |
|---|---|---|---|---|
| `G01_merge_duplicate_sources` | Single | Route đến tool mới để hợp nhất nguồn trùng. | `merge_sources` | PASS |
| `G02_named_account_timeline` | Single | Chuyển tên người quen thuộc thành canonical handle. | `timeline(screenname="sama", limit=4)` | PASS |
| `G03_news_month_timeframe` | Single | Route news và ánh xạ “tháng này”. | `lookup(query="robotics", topic="news", timeframe="month")` | PASS |
| `G04_missing_article_url` | Single | Không tự đoán URL còn thiếu. | `clarify(response_type="text")` | PASS |
| `G05_publish_needs_confirmation` | Single | Xác nhận trước hành động publish. | `clarify(response_type="yes_no")` | PASS |
| `G06_fill_missing_handle` | Multi | Bổ sung handle ở lượt sau và giữ limit. | `timeline(screenname="karpathy", limit=6)` | PASS |
| `G07_switch_social_to_web` | Multi | Nguồn web mới ghi đè yêu cầu Twitter cũ. | Chỉ `lookup(..., topic="news", timeframe="week")` | PASS |
| `G08_carryover_month` | Multi | Đổi chủ đề nhưng giữ nguồn news và timeframe. | Chỉ `lookup(query="chip bán dẫn", topic="news", timeframe="month")` | **FAIL** |
| `G09_correct_handle_and_limit` | Multi | Áp dụng handle và limit correction mới nhất. | `timeline(screenname="sama", limit=3)` | PASS |
| `G10_keep_social_change_topic_and_sort` | Multi | Giữ nguồn social, đổi topic và sort. | `social_search(query="Anthropic", search_type="Top")` | PASS |

Kết quả group v4-tools (`runs/v4-tools_B_group_openrouter_20261110T193048164467.json`):

- Case accuracy: **0.90** (9/10)
- Tool routing accuracy: **0.90**
- Argument accuracy: **0.90**
- Multi-turn accuracy: **0.80**
- Provider error cases: **0**

## B4. Live Chat Evidence

Evidence: `transcripts/v4-tools_openrouter_20261110T193123151676.transcript.json`

| Turn | User Request | Tool Calls | Version Evidence | Outcome |
|---:|---|---|---|---|
| 1 | Tìm tin tức nổi bật về AI trong tháng này. | `lookup(query="AI", topic="news", timeframe="month")` | `v4-tools+p7dc4cb261b78+t6edf66e24b4a` | Đúng source, topic và timeframe; trả danh sách tin có URL. |
| 2 | Đổi chủ đề sang chip bán dẫn nhưng vẫn giữ tháng này. | `lookup(query="chip bán dẫn", topic="news", timeframe="month")` | Cùng artifact v4-tools | Đổi query nhưng giữ đúng news/month. |
| 3 | Bỏ web, chuyển sang Twitter về chip bán dẫn. | `social_search(query="chip bán dẫn", search_type="Latest")` | Cùng artifact v4-tools | Chuyển đúng source và không gọi lại lookup. |

Transcript có 3 turns, dùng `openai/gpt-4o-mini` qua OpenRouter và không có provider error. Việc hành vi carry-over chạy đúng trong live chat nhưng từng fail ở một group run cho thấy cần kết hợp automatic eval với manual review và nhiều lần chạy để đánh giá độ tái lập.

## B5. Bonus và Engineering Evidence

| Hạng mục | Evidence File | What Worked | Risk / Guardrail |
|---|---|---|---|
| Tool mới `merge_sources` | `tools/merge_sources/`, `tests/test_tools_todo.py`, case `G01` | Chuẩn hóa URL, deduplicate, gộp metadata và ưu tiên source diversity. | Validate input chặt; không gọi mạng; kết quả deterministic. |
| Send confirmation | `tools/send/tool.py`, regression tests | Chỉ gọi Telegram API khi `confirmed is True`. | Mọi giá trị khác, kể cả chuỗi `"false"`, trả `needs_confirmation` và không gọi mạng. |
| Streamlit UI | `app.py` | Chat nhiều lượt, hiển thị tool events, lưu transcript; local và public health đều HTTP 200. | UI loại `send` khỏi declarations cho tới khi có confirmation flow an toàn; quick tunnel không có cam kết uptime. |
| Tool unit tests | `tests/test_tools_todo.py` | Toàn bộ suite: **91 passed, 0 failed, 0 skipped**. | Tests chạy offline và chặn real network. |

Unit test đã phát hiện một bug mà routing eval không đo được: `send_telegram` từng dùng `if not confirmed`, nên input sai kiểu `confirmed="false"` là chuỗi truthy và có thể gọi Telegram API. Regression test `test_send_string_false_does_not_call_network` bắt được lỗi; guardrail được sửa thành kiểm tra identity `confirmed is True`.

UI được kiểm tra theo hai lớp:

- Local: `http://127.0.0.1:8501` và `/_stcore/health` đều trả HTTP 200.
- Public: URL Cloudflare ở A1 và health endpoint đều trả HTTP 200; health body là `ok`.

## B6. Reflection

### Fix nào thuộc `system_prompt.md`?

Các quy tắc hội thoại tổng quát thuộc system prompt: không bịa thông tin còn thiếu, xác nhận trước side effect, latest correction ghi đè giá trị cũ, giữ constraints chưa bị thay đổi và loại bỏ source/tool mà user đã từ chối. V4 cho thấy nhóm quy tắc này đặc biệt hữu ích cho multi-turn: base multi-turn accuracy tăng lên 1.00.

### Fix nào thuộc `tools.yaml`?

Contract riêng của từng tool thuộc tool declaration: khi nào dùng timeline hay social search, `lookup.topic`, canonical handle, required arguments, enum và ranh giới loại trừ giữa lookup/social/fetch. V3 cải thiện mạnh từ 0.70 lên 0.90 mà không đổi system prompt, cho thấy model cần schema và description cụ thể ở đúng nơi.

### Failure nào cần manual review?

Clarification cần review thủ công vì tool có thể đúng nhưng cách hỏi hoặc `response_type` chưa đúng ý nghĩa nghiệp vụ. Carry-over nhiều lượt cũng cần review: cùng hành vi news/month đã fail ở `G08` nhưng pass trong transcript live v4. Một lần chạy không đủ để kết luận độ ổn định tuyệt đối.

### Nếu tiếp tục phát triển, nhóm sẽ cải thiện gì?

1. Thêm structured conversation state cho query/source/topic/timeframe/account/limit thay vì phụ thuộc hoàn toàn vào prompt.
2. Thiết kế confirmation state machine rõ ràng cho send/publish và tích hợp luồng xác nhận an toàn vào UI.
3. Chạy mỗi eval nhiều lần, tính pass rate/reproducibility cho từng case thay vì chỉ một kết quả nhị phân.
4. Thêm tests cho transcript/UI boundary và kiểm tra không rò rỉ secret trước khi deploy lâu dài.

## B7. Small Local Model Challenge

Nhóm không thực hiện hạng mục bonus model local; kết quả chính thức trong báo cáo dùng `openai/gpt-4o-mini` qua OpenRouter.
