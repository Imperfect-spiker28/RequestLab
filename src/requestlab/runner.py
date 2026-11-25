"""HTTP execution engine for declarative RequestLab test suites."""

from dataclasses import dataclass, field
import json
import os
import re
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .assertions import evaluate_expectations

_ENV_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


def interpolate_env(value: Any, env: dict[str, str] | None = None) -> Any:
    """Recursively expand ${VAR} placeholders in strings, lists, and dicts."""
    source = env if env is not None else os.environ
    if isinstance(value, str):
        return _ENV_PATTERN.sub(lambda m: source.get(m.group(1), m.group(0)), value)
    if isinstance(value, list):
        return [interpolate_env(item, source) for item in value]
    if isinstance(value, dict):
        return {k: interpolate_env(v, source) for k, v in value.items()}
    return value


@dataclass
class CaseResult:
    name: str
    method: str
    url: str
    status: int | None
    elapsed_ms: float
    passed: bool
    failures: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "method": self.method,
            "url": self.url,
            "status": self.status,
            "elapsed_ms": round(self.elapsed_ms, 2),
            "passed": self.passed,
            "failures": self.failures,
        }


def run_case(
    case: dict[str, Any],
    base_url: str = "",
    default_timeout: float = 10.0,
    env: dict[str, str] | None = None,
) -> CaseResult:
    """Execute a single HTTP request test case and evaluate expectations."""
    resolved = interpolate_env(case, env)
    name = resolved.get("name", "unnamed-case")
    method = str(resolved.get("method", "GET")).upper()
    path_or_url = str(resolved.get("url") or resolved.get("path") or "/")
    if path_or_url.startswith(("http://", "https://")):
        url = path_or_url
    else:
        url = base_url.rstrip("/") + "/" + path_or_url.lstrip("/")

    headers: dict[str, str] = {str(k): str(v) for k, v in resolved.get("headers", {}).items()}
    body_data = resolved.get("body")
    payload_bytes: bytes | None = None
    if body_data is not None:
        if isinstance(body_data, (dict, list)):
            payload_bytes = json.dumps(body_data).encode("utf-8")
            headers.setdefault("Content-Type", "application/json")
        else:
            payload_bytes = str(body_data).encode("utf-8")

    req = Request(url=url, data=payload_bytes, headers=headers, method=method)
    timeout = float(resolved.get("timeout", default_timeout))
    expect = resolved.get("expect", {"status": 200})

    start = time.perf_counter()
    status_code: int | None = None
    resp_headers: dict[str, str] = {}
    raw_body = ""
    try:
        with urlopen(req, timeout=timeout) as resp:
            status_code = resp.status
            resp_headers = dict(resp.headers.items())
            raw_body = resp.read().decode("utf-8", errors="replace")
    except HTTPError as err:
        status_code = err.code
        resp_headers = dict(err.headers.items()) if err.headers else {}
        raw_body = err.read().decode("utf-8", errors="replace")
    except URLError as err:
        elapsed_ms = (time.perf_counter() - start) * 1000.0
        return CaseResult(
            name=name,
            method=method,
            url=url,
            status=None,
            elapsed_ms=elapsed_ms,
            passed=False,
            failures=[f"Network error: {err.reason}"],
        )

    elapsed_ms = (time.perf_counter() - start) * 1000.0
    try:
        json_body = json.loads(raw_body) if raw_body.strip() else None
    except json.JSONDecodeError:
        json_body = None

    failures = evaluate_expectations(expect, status_code, elapsed_ms, resp_headers, json_body, raw_body)
    return CaseResult(
        name=name,
        method=method,
        url=url,
        status=status_code,
        elapsed_ms=elapsed_ms,
        passed=not failures,
        failures=failures,
    )


def run_suite(
    suite: dict[str, Any],
    base_url_override: str | None = None,
    timeout: float = 10.0,
    env: dict[str, str] | None = None,
) -> list[CaseResult]:
    """Run all cases defined in a suite dictionary."""
    base_url = base_url_override if base_url_override is not None else str(interpolate_env(suite.get("base_url", ""), env))
    cases = suite.get("cases", [])
    return [run_case(c, base_url=base_url, default_timeout=timeout, env=env) for c in cases]
