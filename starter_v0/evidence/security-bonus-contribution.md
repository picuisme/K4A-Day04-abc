# Security and Bonus Tool Evidence

Contributor: Nguyen Tuan Thanh (`Chika1357`)
Role: E - Security and Bonus Tool

## Tavily privacy boundary

`search_device_info` sends only public manufacturer, model, query type, and a
bounded result limit. It rejects asset/employee identifiers plus serial,
hostname, IP, location, diagnostics, and ticket-related labels before any HTTP
request. Official domains are preferred for known vendors, and instruction-like
web lines are separated into `untrusted_text`.

Deterministic evidence:

```powershell
python scripts/security_smoke.py
```

Observed result on 2026-09-15: 12/12 checks passed. The mocked HTTP client also
proved that blocked payloads caused zero network calls.

OpenAI evidence progressed from 10/12 adversarial cases in V6 to 12/12 in V9.
After integration, V12 exposed an A10 regression because the evaluator flattened
multi-turn context into one message. V13 added runtime detection for both native
chat history and flattened context. Its final adversarial and base runs measured
every case with zero provider errors: adversarial passed 12/12 and base passed
30/30.

## Generated-ticket hygiene

The ticket writer accepts only literal Boolean `confirmed=True` and rejects
common credential fields before writing. `scripts/audit_tickets.py` performs a
read-only checkout for malformed, placeholder, sensitive, mismatched, or
duplicate generated tickets.

```powershell
python scripts/audit_tickets.py
```

Observed result after the final V13 run: clean, 0 generated ticket files present.
Generated tickets remain ignored and must not be committed as evidence.

## Bonus tool: approved software catalog

`approved_software_catalog` is a new read-only capability backed by synthetic
JSON. It supports name/alias search and platform filtering, and preserves the
distinction among `approved`, `restricted`, and `prohibited`. A catalog result
does not install software or approve an exception.

Included artifacts:

- `tools/approved_software_catalog/TOOL.md`
- `tools/approved_software_catalog/tool.py`
- `helpdesk_data/approved_software.json`
- registry entry in `tools/__init__.py`
- model-facing schema in `artifacts/tools.yaml`
- `scripts/bonus_tool_smoke.py`

```powershell
python scripts/bonus_tool_smoke.py
```

Observed result on 2026-09-14: 6/6 checks passed; declaration/registry parity
also passed with 10 tools.

The preliminary OpenAI group run passed `G-SW01` (1/1 measured, zero provider
errors). It is not the final group metric because the team dataset still needs
exactly 10 original cases.

## Final measured runs

- `evidence/runs/v12_B_adversarial_openai_20260915T002630395996.json`: 11/12; retained as the A10 failure trace.
- `evidence/runs/v13_B_adversarial_openai_20260915T002850206811.json`: 12/12 PASS.
- `evidence/runs/v13_B_base_openai_20260915T002944855130.json`: 30/30 PASS.
- `evidence/runs/v9-preliminary_B_group_openai_20260914T202247834389.json`: bonus case 1/1 PASS; preliminary only.
- V6-V9 adversarial runs are retained to show the earlier evidence-driven iteration.

## Evidence still requiring the final team branch

- Keep `G-SW01_approved_software_lookup` in the final set of exactly 10 original
  cases, then rerun the complete group suite with the final artifact version.
- Capture a UI/transcript trace and copy the measured result into REPORT B5.
