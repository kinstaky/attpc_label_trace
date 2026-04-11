from __future__ import annotations

from attpc_estimator.process.progress import ProgressUpdate
from attpc_estimator.service.histogram_jobs import HistogramJobManager


def test_histogram_job_manager_emits_progress_only_when_percent_changes() -> None:
    manager = HistogramJobManager()

    def run(progress) -> dict:
        progress(ProgressUpdate(current=0, total=200, unit="trace"))
        progress(ProgressUpdate(current=1, total=200, unit="trace"))
        progress(ProgressUpdate(current=1, total=200, unit="trace"))
        progress(ProgressUpdate(current=2, total=200, unit="trace"))
        return {"ok": True}

    job_id = manager.create_job(run)
    messages = []
    message_index = 0
    while True:
        next_message = manager.next_message(job_id, message_index)
        assert next_message is not None
        message_index, payload = next_message
        messages.append(payload)
        if payload["type"] == "complete":
            break

    assert messages == [
        {
            "type": "progress",
            "current": 0,
            "total": 200,
            "percent": 0,
            "unit": "trace",
            "message": "",
        },
        {
            "type": "progress",
            "current": 2,
            "total": 200,
            "percent": 1,
            "unit": "trace",
            "message": "",
        },
        {
            "type": "complete",
            "payload": {"ok": True},
        },
    ]
