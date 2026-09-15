from __future__ import annotations

import sys
from pathlib import Path
from typing import Callable


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools import TOOL_FUNCTIONS
from tools.approved_software_catalog.tool import approved_software_catalog


def run_check(name: str, check: Callable[[], None]) -> None:
    check()
    print(f"PASS  {name}")


def check_registered() -> None:
    assert TOOL_FUNCTIONS["approved_software_catalog"] is approved_software_catalog


def check_exact_alias() -> None:
    result = approved_software_catalog("VSCode", "windows", 3)
    assert result["match_count"] == 1
    assert result["matches"][0]["name"] == "Visual Studio Code"
    assert result["matches"][0]["status"] == "approved"


def check_platform_filter() -> None:
    result = approved_software_catalog("7zip", "macos", 3)
    assert result["match_count"] == 0


def check_restricted_and_prohibited() -> None:
    restricted = approved_software_catalog("Docker", "windows", 3)
    prohibited = approved_software_catalog("AnyDesk", "all", 3)
    assert restricted["matches"][0]["status"] == "restricted"
    assert prohibited["matches"][0]["status"] == "prohibited"
    assert prohibited["matches"][0]["install_method"] == "Not available"


def check_invalid_arguments() -> None:
    assert approved_software_catalog("", "all", 3)["error"] == "missing_query"
    assert approved_software_catalog("Zoom", "solaris", 3)["error"] == "invalid_platform"
    assert approved_software_catalog("Zoom", "all", "3")["error"] == "invalid_max_results"


def check_limit_clamped() -> None:
    result = approved_software_catalog("software approved", "all", 99)
    assert result["match_count"] <= 10


def main() -> None:
    checks = (
        ("Bonus tool is registered", check_registered),
        ("Exact alias lookup returns an approved package", check_exact_alias),
        ("Platform filtering excludes unsupported packages", check_platform_filter),
        ("Restricted and prohibited states are preserved", check_restricted_and_prohibited),
        ("Invalid arguments are rejected", check_invalid_arguments),
        ("Result limit is bounded", check_limit_clamped),
    )
    for name, check in checks:
        run_check(name, check)
    print(f"\n{len(checks)} bonus-tool smoke checks passed.")


if __name__ == "__main__":
    main()
