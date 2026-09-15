# Tool Setup — IT Helpdesk Agent Lab

Tài liệu này tập trung vào việc cài môi trường, cấu hình model provider và kiểm
tra các tool có sẵn. Quy trình làm bài được tách riêng trong `LAB-GUIDE.md`.

## 1. Yêu cầu môi trường

- Python 3.10 trở lên.
- Một model provider hỗ trợ structured tool calling.
- API key của provider được chọn.
- Tavily key chỉ khi dùng `search_device_info` hoặc chạy extension flow cần web.

## 2. Tạo virtual environment

Windows PowerShell:

```powershell
cd starter_v0
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

macOS/Linux:

```bash
cd starter_v0
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
test -f .env || cp .env.example .env
```

Không ghi đè `.env` đang có. Không commit hoặc chia sẻ file `.env`.

## 3. Model provider

Chọn một provider và điền key tương ứng trong `starter_v0/.env`:

```text
# OpenRouter
OPENROUTER_API_KEY=...

# Hoặc OpenAI
OPENAI_API_KEY=...

# Hoặc Anthropic
ANTHROPIC_API_KEY=...

# Hoặc Gemini
GEMINI_API_KEY=...
```

Chạy preflight với đúng provider:

```powershell
python scripts/preflight_provider.py --provider openrouter
```

Có thể thay `openrouter` bằng `openai`, `anthropic` hoặc `gemini`.

Preflight PASS khi provider trả structured tool call. Nó không chấm toàn bộ
routing accuracy.

## 4. Tổng quan setup của từng tool

| Tool | Loại | Dependency/data | API key |
|---|---|---|---|
| `clarify` | Control | Không | Không |
| `search_kb` | Local knowledge | `helpdesk_data/knowledge_base/*.md` | Không |
| `check_service_status` | Local status | `helpdesk_data/service_status.json` | Không |
| `inspect_device` | Local inventory | `helpdesk_data/assets.json` | Không |
| `lookup_user` | Local directory | `helpdesk_data/users.json` | Không |
| `format_incident_report` | Local formatter | Không | Không |
| `approved_software_catalog` | Local catalog, team-built bonus | `helpdesk_data/approved_software.json` | Không |
| `policy` | Local knowledge | `company_policy/*.md` | Không |
| `create_ticket` | Local write action | Ghi vào `starter_v0/tickets/` | Không |
| `search_device_info` | External search | Tavily Search API | `TAVILY_API_KEY` |

## 5. Local tools

Các local tool sử dụng fixture trong repo và không cần network.

### `clarify`

```powershell
python -c "from tools import TOOL_FUNCTIONS as T; print(T['clarify']('Mã asset là gì?', 'text'))"
```

PASS khi output có `awaiting_user: True`.

### `search_kb`

```powershell
python -c "from tools import TOOL_FUNCTIONS as T; r=T['search_kb']('VPN macOS certificate','vpn',2); print({'error':r.get('error'),'results':len(r.get('results') or []),'boundary':r.get('trust_boundary')})"
```

PASS khi có kết quả và `trust_boundary`. Instruction-like content phải nằm
trong `untrusted_text`, không nằm trong trusted `content`.

### `check_service_status`

```powershell
python -c "from tools import TOOL_FUNCTIONS as T; print(T['check_service_status']('vpn','production'))"
```

PASS khi output có `service`, `environment`, `status` và `checked_at`.

### `inspect_device`

```powershell
python -c "from tools import TOOL_FUNCTIONS as T; print(T['inspect_device']('LT-318','vpn'))"
```

PASS khi trả đúng asset và diagnostic group được yêu cầu.

### `lookup_user`

```powershell
python -c "from tools import TOOL_FUNCTIONS as T; print(T['lookup_user']('EMP-1007'))"
```

PASS khi trả directory record giả lập và assigned assets.

### `format_incident_report`

```powershell
python -c "from tools import TOOL_FUNCTIONS as T; print(T['format_incident_report']([{'label':'VPN','detail':'degraded'}],'brief','VPN incident'))"
```

PASS khi trả markdown và đúng `finding_count`.

### `policy`

```powershell
python -c "from tools import TOOL_FUNCTIONS as T; r=T['policy']('dữ liệu nào được gửi ra external tool','external_tools',2); print({'error':r.get('error'),'results':len(r.get('results') or []),'boundary':r.get('trust_boundary')})"
```

PASS khi trả policy section có source metadata và trust boundary.

### `approved_software_catalog` (team-built bonus)

```powershell
python scripts/bonus_tool_smoke.py
```

PASS khi cả 6 check thành công. Tool chỉ đọc catalog tổng hợp, trả trạng thái
`approved`, `restricted` hoặc `prohibited`, và không cài đặt hay cấp ngoại lệ.

## 6. Action tool: `create_ticket`

Tool này ghi JSON vào `starter_v0/tickets/` khi và chỉ khi `confirmed` là Boolean
`true` thực sự.

Chỉ chạy dry-run trong smoke test:

```powershell
python -c "from tools import TOOL_FUNCTIONS as T; print(T['create_ticket']('VPN dry run','low','LT-204',False))"
```

PASS khi:

- status là `needs_confirmation`;
- không có file ticket mới;
- tool không chấp nhận password, token, MFA/OTP hoặc recovery code;
- chuỗi `"true"`, số `1` hoặc object không được coi là confirmation hợp lệ.

Chỉ test `confirmed=True` với dữ liệu giả lập và trong thư mục tạm.

## 7. External tool: `search_device_info`

Tool này gọi Tavily Search API bằng public manufacturer/model.

Tạo key tại trang Tavily và điền vào `.env`:

```text
TAVILY_API_KEY=tvly-...
```

Smoke test:

```powershell
python -c "from pathlib import Path; from env_loader import load_lab_env; load_lab_env(Path.cwd()); from tools import TOOL_FUNCTIONS as T; r=T['search_device_info']('Lenovo','ThinkPad T14 Gen 4','drivers',2); print({'error':r.get('error'),'items':len(r.get('items') or []),'domains':r.get('official_domains')})"
```

PASS khi không có error và kết quả đến từ vendor domain phù hợp.

Chỉ được truyền:

- manufacturer;
- public model name;
- query type;
- số lượng kết quả.

Không được truyền asset ID, employee ID, serial number, hostname, location,
assigned user, diagnostic log, ticket content hoặc credentials. Implementation
sẽ chặn identifier nội bộ và lọc instruction-like text từ web result.

## 8. Kiểm tra local trước khi chạy eval

```powershell
python -m compileall -q .
```

Sau đó chạy các smoke command ở phần 5–7 cho những tool nhóm sẽ demo. Trước khi
dùng model thật, chạy lại provider preflight:

```powershell
python scripts/preflight_provider.py --provider openrouter
```

Compile và local smoke checks không cần provider key. Preflight cần key của
provider nhưng không chạy toàn bộ eval. Chỉ smoke test `search_device_info` khi
có `TAVILY_API_KEY` vì lời gọi này có thể tiêu quota Tavily.

## 9. Chạy eval bằng model thật

Base:

```powershell
python run_eval.py --provider openrouter --version v0 --suite base --eval-cases data/eval_base.json
```

Group:

```powershell
python run_eval.py --provider openrouter --version v3 --suite group --eval-cases data/eval_group.json
```

Extension:

```powershell
python run_eval.py --provider openrouter --version v3 --suite extension --eval-cases data/eval_helpdesk_extension.json
```

Adversarial:

```powershell
python run_eval.py --provider openrouter --version v3 --suite adversarial --eval-cases data/eval_adversarial.json
```

Extension có thể gọi Tavily và tạo ticket local ở confirmed-action cases. Kiểm
tra `.env`, quota và `tickets/` trước/sau khi chạy.

## 10. UI dependencies

Starter không cung cấp UI implementation. Nếu chọn Streamlit:

```powershell
python -m pip install "streamlit>=1.30.0"
```

Thêm cùng version constraint vào `requirements.txt`, sau đó chạy:

```powershell
streamlit run app.py
```

UI nên tái sử dụng `run_model_tool_loop` từ `chat.py` để CLI, eval evidence và UI
không dùng các agent loop khác nhau.

## 11. Troubleshooting

### Provider không trả tool call

- Kiểm tra model có hỗ trợ structured tools.
- Kiểm tra đúng provider, key và quota.
- Chạy lại preflight trước khi chạy full eval.

### Tool báo missing API key

- Local tools không cần key.
- `search_device_info` cần `TAVILY_API_KEY` trong `starter_v0/.env`.
- Đảm bảo command được chạy từ thư mục `starter_v0/`.

### Tool name không hợp lệ

Kiểm tra tên đã đồng bộ giữa:

- `artifacts/tools.yaml`;
- `tools/__init__.py`;
- `tools/<name>/TOOL.md`;
- eval cases có liên quan.

### Ticket xuất hiện ngoài ý muốn

- Dừng demo và kiểm tra transcript/tool args.
- Xác minh `confirmed` là Boolean `true` và có explicit confirmation.
- Không đưa generated tickets vào bài nộp.

### Metric có vẻ cao nhưng output sai

Automatic grader chủ yếu chấm tool calls và argument subset. Luôn đọc
`tool_results`, final response và security evidence thủ công.

## 12. Secret hygiene

- Không commit `.env`.
- Không in API key trong log hoặc screenshot.
- Không đưa dữ liệu thật vào mock fixtures.
- Nếu key bị lộ, rotate key trước khi tiếp tục.
- Không nộp `.venv`, cache, runs chứa secret hoặc generated tickets.
