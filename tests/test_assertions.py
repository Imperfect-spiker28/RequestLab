from requestlab.assertions import evaluate_expectations, resolve_dot_path


def test_resolve_dot_path_nested_and_list() -> None:
    payload = {"data": {"items": [{"id": 42, "ok": True}]}}
    found, val = resolve_dot_path(payload, "data.items.0.id")
    assert found is True
    assert val == 42

    missing, _ = resolve_dot_path(payload, "data.items.5.id")
    assert missing is False


def test_evaluate_expectations_reports_multiple_failures() -> None:
    failures = evaluate_expectations(
        expect={"status": 200, "max_ms": 50, "json": {"ok": True}},
        status=500,
        elapsed_ms=120.5,
        headers={},
        json_body={"ok": False},
        raw_body='{"ok": false}',
    )
    assert len(failures) == 3
