from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.create_ticket.tool import ASSET_ID_PATTERN, SENSITIVE_DATA_PATTERN, TICKET_DIR


TICKET_ID_PATTERN = re.compile(r"^LAB-[A-F0-9]{8}$")
ALLOWED_PRIORITIES = {"low", "medium", "high", "critical"}
REQUIRED_FIELDS = {"ticket_id", "summary", "priority", "asset_id", "created_at", "source"}
JUNK_SUMMARIES = {
    "asdf",
    "demo",
    "hello",
    "test",
    "test ticket",
    "ticket test",
    "todo",
}


def _normalized_signature(ticket: dict[str, Any]) -> tuple[str, str]:
    summary = " ".join(str(ticket.get("summary") or "").casefold().split())
    asset_id = str(ticket.get("asset_id") or "").upper()
    return summary, asset_id


def audit_ticket_file(path: Path) -> tuple[dict[str, Any] | None, list[str]]:
    issues: list[str] = []
    try:
        ticket = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return None, [f"unreadable_json:{type(exc).__name__}"]
    if not isinstance(ticket, dict):
        return None, ["root_must_be_object"]

    missing_fields = sorted(REQUIRED_FIELDS - set(ticket))
    if missing_fields:
        issues.append(f"missing_fields:{','.join(missing_fields)}")

    ticket_id = ticket.get("ticket_id")
    if not isinstance(ticket_id, str) or not TICKET_ID_PATTERN.fullmatch(ticket_id):
        issues.append("invalid_ticket_id")
    elif path.stem != ticket_id:
        issues.append("filename_ticket_id_mismatch")

    summary = ticket.get("summary")
    if not isinstance(summary, str) or not summary.strip():
        issues.append("missing_summary")
    else:
        normalized_summary = " ".join(summary.casefold().split())
        if normalized_summary in JUNK_SUMMARIES:
            issues.append("placeholder_summary")
        if SENSITIVE_DATA_PATTERN.search(summary):
            issues.append("sensitive_data_in_summary")

    if ticket.get("priority") not in ALLOWED_PRIORITIES:
        issues.append("invalid_priority")
    asset_id = ticket.get("asset_id")
    if asset_id is not None and (
        not isinstance(asset_id, str) or not ASSET_ID_PATTERN.fullmatch(asset_id)
    ):
        issues.append("invalid_asset_id")
    if ticket.get("source") != "educational_local_mock":
        issues.append("unexpected_source")
    return ticket, issues


def audit_ticket_directory(ticket_dir: Path = TICKET_DIR) -> dict[str, Any]:
    if not ticket_dir.exists():
        return {
            "ticket_directory": str(ticket_dir),
            "files_checked": 0,
            "issues": [],
            "status": "clean",
        }

    issues: list[dict[str, Any]] = []
    tickets: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(ticket_dir.glob("*.json")):
        ticket, file_issues = audit_ticket_file(path)
        if ticket is not None:
            tickets.append((path, ticket))
        for issue in file_issues:
            issues.append({"file": path.name, "issue": issue})

    signatures = Counter(_normalized_signature(ticket) for _, ticket in tickets)
    for path, ticket in tickets:
        if signatures[_normalized_signature(ticket)] > 1:
            issues.append({"file": path.name, "issue": "duplicate_summary_and_asset"})

    return {
        "ticket_directory": str(ticket_dir),
        "files_checked": len(list(ticket_dir.glob("*.json"))),
        "issues": issues,
        "status": "clean" if not issues else "review_required",
    }


def main() -> int:
    result = audit_ticket_directory()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "clean" else 1


if __name__ == "__main__":
    raise SystemExit(main())
