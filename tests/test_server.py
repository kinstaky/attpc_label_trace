from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("httpx")

from fastapi.testclient import TestClient

from attpc_estimator.server import create_app


class DummyMergedService:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True

    def bootstrap_state(self) -> dict:
        return {"appType": "merged", "session": {"mode": "label", "run": 8}}

    def set_session(
        self,
        *,
        mode: str,
        run: int | None = None,
        source: str | None = None,
        family: str | None = None,
        label: str | None = None,
        filter_file: str | None = None,
    ) -> dict:
        return {
            "session": {
                "mode": mode,
                "run": run,
                "source": source,
                "family": family,
                "label": label,
                "filterFile": filter_file,
            }
        }

    def next_trace(self) -> dict:
        return {"run": 8, "eventId": 1, "traceId": 2}

    def previous_trace(self) -> dict:
        raise LookupError("no previous trace")

    def assign_label(self, *, event_id: int, trace_id: int, family: str, label: str) -> dict:
        return {
            "eventId": event_id,
            "traceId": trace_id,
            "family": family,
            "label": label,
        }

    def get_strange_labels(self) -> dict:
        return {"strangeLabels": []}

    def create_strange_label(self, name: str, shortcut_key: str) -> dict:
        return {"name": name, "shortcutKey": shortcut_key}

    def delete_strange_label(self, label: str) -> dict:
        return {"deleted": label}

    def get_histogram(
        self, *, metric: str, mode: str, run: int, filter_file: str | None = None
    ) -> dict:
        return {
            "metric": metric,
            "mode": mode,
            "run": run,
            "filterFile": filter_file,
        }


def test_create_app_routes_and_fallback(tmp_path: Path) -> None:
    app = create_app(DummyMergedService(), tmp_path / "missing-dist")

    with TestClient(app) as client:
        assert client.get("/api/health").json() == {"status": "ok"}
        assert client.get("/api/bootstrap").json() == {
            "appType": "merged",
            "session": {"mode": "label", "run": 8},
        }

        session = client.post(
            "/api/session",
            json={"mode": "review", "run": 8, "source": "label_set", "family": "normal"},
        )
        assert session.status_code == 200
        assert session.json() == {
            "session": {
                "mode": "review",
                "run": 8,
                "source": "label_set",
                "family": "normal",
                "label": None,
                "filterFile": None,
            }
        }

        assert client.post("/api/traces/next").json() == {"run": 8, "eventId": 1, "traceId": 2}
        previous = client.post("/api/traces/previous")
        assert previous.status_code == 404
        assert previous.json() == {"detail": "no previous trace"}

        assign = client.post(
            "/api/labels/assign",
            json={"eventId": 1, "traceId": 2, "family": "normal", "label": "0"},
        )
        assert assign.status_code == 200
        assert assign.json() == {"eventId": 1, "traceId": 2, "family": "normal", "label": "0"}

        histogram = client.get(
            "/api/histograms",
            params={"metric": "cdf", "mode": "all", "run": 8},
        )
        assert histogram.status_code == 200
        assert histogram.json() == {
            "metric": "cdf",
            "mode": "all",
            "run": 8,
            "filterFile": None,
        }

        fallback = client.get("/some/client/route")
        assert fallback.status_code == 200
        assert "Frontend build missing" in fallback.text
        missing_api = client.get("/api/missing")
        assert missing_api.status_code == 404
        assert missing_api.text == "Not Found"
