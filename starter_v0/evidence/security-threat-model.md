# Security Threat Model

Owner: Nguyen Tuan Thanh (`Chika1357`)
Scope: Tavily data boundary, ticket side effects, and untrusted tool content.

## Security invariants

1. External search receives public manufacturer, model, query type, and result
   limit only. Internal identifiers and operational data never leave the local
   trust boundary.
2. Web, knowledge-base, policy, and user-provided text is evidence, not an
   instruction source. Role labels or tool-result-shaped text inside it cannot
   authorize an action.
3. Ticket creation requires Boolean `confirmed=True` after explicit user
   confirmation for the current payload. String, number, object, forged, or
   stale confirmation is invalid.
4. Passwords, API keys, tokens, MFA/OTP values, and recovery codes are never
   written to tickets or included in external requests.
5. Security tests use synthetic data. Local smoke tests must not consume model
   or Tavily quota and must not leave generated tickets in the repository.

## Threat and control matrix

| Threat | Trust boundary | Required control | Deterministic evidence | Model-level evidence |
|---|---|---|---|---|
| Internal identifier sent to Tavily | Local data -> external provider | Reject asset/employee identifiers before network I/O | `scripts/security_smoke.py` verifies rejection and zero HTTP calls | A06, A12 |
| Data smuggling through public fields | Local data -> external provider | Validate field type, length, and restricted identifier patterns | Smoke test inspects the mocked Tavily request body | A12 |
| Prompt injection in web results | External provider -> agent | Remove instruction-like lines from trusted summary and retain them as `untrusted_text` | Smoke response contains a synthetic `SYSTEM:` line | A08, A09 |
| Forged confirmation | User content -> write action | Accept only literal Boolean `True`; prompt must require a separate confirmation turn | Smoke test tries `False`, `"true"`, and `1` | A02, A03, A04, A11 |
| Stale or forged confirmation | Conversation state -> write action | Prompt provenance rules plus runtime rerouting before side effects | Runtime smoke forces an unsafe proposed call and verifies no ticket file | A03, A04, A10, A11 |
| Credential written to ticket | User content -> filesystem | Reject credential-bearing summaries before creating a directory or file | Smoke test submits password, token, API key, MFA, OTP, and recovery-code samples | A05 |
| Unsupported tool or secret-file request | User content -> runtime | Refuse undeclared tools and secret access | Registry/declaration review | A01, A07 |

## Evidence procedure

### Local deterministic checks

Run from `starter_v0/`:

```powershell
python scripts/security_smoke.py
```

Expected result: every check prints `PASS`, the process exits with code 0, no
real HTTP request is made, and no file remains under `tickets/`.

### Provider adversarial checks

Run only after the team selects the final prompt and tool schema:

```powershell
python run_eval.py --provider openai --version v13 --suite adversarial --eval-cases data/eval_adversarial.json
```

A run is valid evidence only when `provider_error_cases == 0` and
`measured_cases == total_cases`. Review A03, A05, A06, A10, and A12 manually;
automatic routing scores do not prove that no data was written or sent.

## Manual checkout

- Count files in `tickets/` before and after adversarial runs.
- Inspect `tool_results` and external request arguments, not only PASS/FAIL.
- Confirm that committed evidence contains no `.env` values, credentials,
  internal identifiers copied into external payloads, or generated tickets.
- Preserve sanitized run/transcript evidence in a tracked evidence directory.
