# RequestLab

Zero-dependency HTTP/REST contract and latency test runner CLI for CI/CD pipelines.

## Features
- **Declarative JSON Suites:** Define `GET`/`POST`/`PUT`/`DELETE` requests with headers, JSON bodies, and expected status codes.
- **Dot-Path JSON Assertions:** Verify nested fields and array elements (e.g., `"meta.version": 1`, `"items.0.id": 42`) with zero external dependencies.
- **Latency Budgets:** Fail builds when endpoint response time exceeds `max_ms`.
- **Environment Interpolation:** Expand `${ENV_VAR}` placeholders in URLs, headers, and payloads.
- **CI/CD Ready:** Structured `--json` report and deterministic pass/fail exit codes.

## Installation

```bash
pip install -e .
```

## Usage

```bash
requestlab run examples/suite.json
requestlab run examples/suite.json --base-url http://127.0.0.1:8000 --json
```

## Tests

```bash
pip install -e ".[dev]"
pytest -v
```
