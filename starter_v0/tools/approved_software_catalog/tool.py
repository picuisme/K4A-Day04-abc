from __future__ import annotations

import json
from typing import Any

from tools._shared import ROOT, err, fold_text, terms


CATALOG_FILE = ROOT / "helpdesk_data" / "approved_software.json"
PLATFORMS = {"all", "windows", "macos", "linux", "ios", "android"}


def _match_score(query: str, query_terms: set[str], application: dict[str, Any]) -> int:
    names = [application["name"], *application.get("aliases", [])]
    folded_query = fold_text(query)
    folded_names = [fold_text(str(name)) for name in names]
    if folded_query in folded_names:
        return 100
    if any(folded_query in name or name in folded_query for name in folded_names):
        return 50
    searchable = " ".join([
        *names,
        str(application.get("software_id", "")),
        str(application.get("status", "")),
        " ".join(application.get("supported_platforms", [])),
    ])
    return len(query_terms & terms(searchable))


def approved_software_catalog(
    query: str = "",
    platform: str = "all",
    max_results: int = 5,
) -> dict[str, Any]:
    if not isinstance(query, str) or not isinstance(platform, str):
        return {"tool": "approved_software_catalog", "error": "invalid_input_type"}
    query_value = query.strip()
    platform_value = (platform or "all").strip().lower()
    if not query_value:
        return {"tool": "approved_software_catalog", "error": "missing_query"}
    if len(query_value) > 120:
        return {"tool": "approved_software_catalog", "error": "query_too_long"}
    if platform_value not in PLATFORMS:
        return {
            "tool": "approved_software_catalog",
            "error": "invalid_platform",
            "available_platforms": sorted(PLATFORMS),
        }
    if isinstance(max_results, bool) or not isinstance(max_results, int):
        return {"tool": "approved_software_catalog", "error": "invalid_max_results"}

    try:
        data = json.loads(CATALOG_FILE.read_text(encoding="utf-8"))
        query_terms = terms(query_value)
        matches: list[dict[str, Any]] = []
        for application in data["applications"]:
            supported_platforms = application.get("supported_platforms", [])
            if platform_value != "all" and platform_value not in supported_platforms:
                continue
            score = _match_score(query_value, query_terms, application)
            if score <= 0:
                continue
            matches.append({
                "software_id": application["software_id"],
                "name": application["name"],
                "status": application["status"],
                "supported_platforms": supported_platforms,
                "approved_versions": application.get("approved_versions", []),
                "license": application.get("license"),
                "install_method": application.get("install_method"),
                "owner_team": application.get("owner_team"),
                "notes": application.get("notes"),
                "score": score,
            })
        matches.sort(key=lambda item: (-item["score"], item["name"]))
        limit = min(10, max(1, max_results))
        selected = matches[:limit]
        return {
            "tool": "approved_software_catalog",
            "query": query_value,
            "platform": platform_value,
            "matches": selected,
            "match_count": len(selected),
            "catalog_version": data["catalog_version"],
            "updated_at": data["updated_at"],
            "source": data["source"],
            "trust_boundary": "Read-only synthetic catalog. A result does not install software or grant an approval exception.",
        }
    except Exception as exc:
        return err("approved_software_catalog", exc)
