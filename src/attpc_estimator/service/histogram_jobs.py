from __future__ import annotations

from collections.abc import Callable
from threading import Condition, Thread
from uuid import uuid4

from ..process.progress import ProgressReporter, ProgressUpdate


class HistogramJob:
    def __init__(self) -> None:
        self._condition = Condition()
        self._messages: list[dict] = []
        self._done = False
        self._last_percent: int | None = None

    def progress_reporter(self) -> ProgressReporter:
        def report(update: ProgressUpdate) -> None:
            percent = update.percent
            with self._condition:
                if self._last_percent == percent:
                    return
                self._last_percent = percent
                self._messages.append(
                    {
                        "type": "progress",
                        "current": int(update.current),
                        "total": int(update.total),
                        "percent": percent,
                        "unit": update.unit,
                        "message": update.message,
                    }
                )
                self._condition.notify_all()

        return report

    def complete(self, payload: dict) -> None:
        with self._condition:
            self._messages.append({"type": "complete", "payload": payload})
            self._done = True
            self._condition.notify_all()

    def error(self, detail: str) -> None:
        with self._condition:
            self._messages.append({"type": "error", "detail": detail})
            self._done = True
            self._condition.notify_all()

    def next_message(self, after_index: int) -> tuple[int, dict] | None:
        with self._condition:
            while len(self._messages) <= after_index and not self._done:
                self._condition.wait()
            if len(self._messages) <= after_index:
                return None
            return after_index + 1, self._messages[after_index]


class HistogramJobManager:
    def __init__(self) -> None:
        self._jobs: dict[str, HistogramJob] = {}

    def create_job(
        self,
        runner: Callable[[ProgressReporter], dict],
    ) -> str:
        job_id = uuid4().hex
        job = HistogramJob()
        self._jobs[job_id] = job

        def run() -> None:
            try:
                payload = runner(job.progress_reporter())
            except Exception as exc:  # pragma: no cover - exercised via callers
                job.error(str(exc))
                return
            job.complete(payload)

        Thread(target=run, daemon=True).start()
        return job_id

    def next_message(self, job_id: str, after_index: int) -> tuple[int, dict] | None:
        job = self._jobs.get(job_id)
        if job is None:
            raise LookupError(f"histogram job not found: {job_id}")
        return job.next_message(after_index)
