"""Command-line interface for RequestLab."""

import argparse
import json
from pathlib import Path
import sys

from . import __version__
from .runner import run_suite


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="requestlab",
        description="Zero-dependency HTTP/REST contract & latency test runner.",
    )
    parser.add_argument("--version", action="version", version=f"requestlab {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    run_cmd = sub.add_parser("run", help="Execute an API test suite JSON file")
    run_cmd.add_argument("suite", type=Path, help="Path to suite JSON file")
    run_cmd.add_argument("--base-url", default=None, help="Override suite base_url")
    run_cmd.add_argument("--timeout", type=float, default=10.0, help="Request timeout in seconds")
    run_cmd.add_argument("--json", action="store_true", help="Emit JSON report")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "run":
        try:
            suite = json.loads(args.suite.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"Error loading suite {args.suite}: {exc}", file=sys.stderr)
            return 1

        results = run_suite(suite, base_url_override=args.base_url, timeout=args.timeout)
        passed_count = sum(1 for r in results if r.passed)
        total_count = len(results)

        if args.json:
            payload = {
                "passed": passed_count,
                "failed": total_count - passed_count,
                "total": total_count,
                "ok": passed_count == total_count,
                "results": [r.to_dict() for r in results],
            }
            print(json.dumps(payload, indent=2))
        else:
            print(f"RequestLab v{__version__} — {passed_count}/{total_count} passed")
            for r in results:
                tag = "PASS" if r.passed else "FAIL"
                print(f"  [{tag}] {r.method} {r.url} ({r.status}, {r.elapsed_ms:.1f}ms) — {r.name}")
                for fail in r.failures:
                    print(f"         -> {fail}")

        return 0 if passed_count == total_count else 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
