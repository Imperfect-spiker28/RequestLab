"""Assertion helpers for HTTP responses, latency budgets, and JSON dot-paths."""

from typing import Any


def resolve_dot_path(payload: Any, dot_path: str) -> tuple[bool, Any]:
    """Resolve a dot-separated path (supporting list indices) inside parsed JSON."""
    current = payload
    for segment in dot_path.split("."):
        if isinstance(current, dict) and segment in current:
            current = current[segment]
        elif isinstance(current, list) and segment.isdigit():
            idx = int(segment)
            if 0 <= idx < len(current):
                current = current[idx]
            else:
                return False, None
        else:
            return False, None
    return True, current


def evaluate_expectations(
    expect: dict[str, Any],
    status: int,
    elapsed_ms: float,
    headers: dict[str, str],
    json_body: Any,
    raw_body: str,
) -> list[str]:
    """Return a list of human-readable assertion failures (empty when all pass)."""
    failures: list[str] = []

    if "status" in expect and status != expect["status"]:
        failures.append(f"Expected status {expect['status']}, got {status}")

    if "max_ms" in expect and elapsed_ms > float(expect["max_ms"]):
        failures.append(f"Latency {elapsed_ms:.1f}ms exceeded budget {expect['max_ms']}ms")

    if "headers" in expect and isinstance(expect["headers"], dict):
        lower_headers = {k.lower(): v for k, v in headers.items()}
        for h_key, h_expected in expect["headers"].items():
            actual = lower_headers.get(h_key.lower())
            if actual is None or str(h_expected).lower() not in actual.lower():
                failures.append(f"Header '{h_key}': expected '{h_expected}', got {actual!r}")

    if "contains" in expect and str(expect["contains"]) not in raw_body:
        failures.append(f"Body did not contain {expect['contains']!r}")

    if "json" in expect and isinstance(expect["json"], dict):
        if json_body is None:
            failures.append("Expected JSON response body, but response was not valid JSON")
        else:
            for path, expected_val in expect["json"].items():
                found, actual_val = resolve_dot_path(json_body, path)
                if not found:
                    failures.append(f"JSON path '{path}' not found")
                elif actual_val != expected_val:
                    failures.append(f"JSON path '{path}': expected {expected_val!r}, got {actual_val!r}")

    return failures
