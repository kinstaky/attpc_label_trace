from __future__ import annotations

from collections.abc import Mapping
import threading
import time

from ...model.label import StoredLabel
from ...model.trace import TraceRecord, TraceRef
from .loader import TraceLoader


class TracePrefetcher:
    def __init__(self, loader: TraceLoader) -> None:
        self._loader = loader
        self._cache: dict[TraceRef, TraceRecord] = {}
        self._desired_refs: tuple[TraceRef, ...] = ()
        self._scheduled_refs: tuple[TraceRef, ...] = ()
        self._generation = 0
        self._completed_generation = 0
        self._active_generation: int | None = None
        self._cache_lock = threading.Lock()
        self._condition = threading.Condition()
        self._closed = False
        self._thread = threading.Thread(
            target=self._worker_loop,
            name="trace-source-prefetch",
            daemon=True,
        )
        self._thread.start()

    def cache_snapshot(self) -> dict[TraceRef, TraceRecord]:
        with self._cache_lock:
            return dict(self._cache)

    def get_cached(self, ref: TraceRef) -> TraceRecord | None:
        with self._cache_lock:
            return self._cache.get(ref)

    def schedule(self, window_refs: list[TraceRef]) -> None:
        refs = tuple(window_refs)
        desired = set(refs)
        with self._cache_lock:
            self._desired_refs = refs
            self._cache = {
                ref: record
                for ref, record in self._cache.items()
                if ref in desired
            }
        with self._condition:
            self._generation += 1
            self._scheduled_refs = refs
            self._condition.notify_all()

    def store_current(self, ref: TraceRef, record: TraceRecord) -> None:
        with self._cache_lock:
            self._cache[ref] = record

    def update_cached_label(self, ref: TraceRef, family: str, label: str) -> None:
        with self._cache_lock:
            cached = self._cache.get(ref)
            if cached is None:
                return
            cached.family = family
            cached.label = label

    def replace_labels(self, labels: Mapping[TraceRef, StoredLabel]) -> None:
        with self._cache_lock:
            for ref, record in self._cache.items():
                stored_label = labels.get(ref)
                if stored_label is None:
                    record.family = None
                    record.label = None
                else:
                    record.family = stored_label.family
                    record.label = stored_label.label

    def wait(self, timeout: float = 1.0) -> bool:
        deadline = time.monotonic() + timeout
        with self._condition:
            while time.monotonic() < deadline:
                if (
                    self._active_generation is None
                    and self._completed_generation >= self._generation
                ):
                    return True
                self._condition.wait(timeout=max(0.0, deadline - time.monotonic()))
            return (
                self._active_generation is None
                and self._completed_generation >= self._generation
            )

    def close(self) -> None:
        with self._condition:
            self._closed = True
            self._condition.notify_all()
        self._thread.join(timeout=1.0)
        with self._cache_lock:
            self._cache.clear()
            self._desired_refs = ()

    def _is_stale(self, generation: int) -> bool:
        with self._condition:
            return self._closed or generation != self._generation

    def _worker_loop(self) -> None:
        while True:
            with self._condition:
                while (
                    not self._closed
                    and self._generation == self._completed_generation
                    and self._active_generation is None
                ):
                    self._condition.wait()
                if self._closed:
                    return
                generation = self._generation
                refs = self._scheduled_refs
                self._active_generation = generation

            self._prefetch_window(generation, refs)

            with self._condition:
                if self._active_generation == generation:
                    self._active_generation = None
                if generation == self._generation:
                    self._completed_generation = generation
                if (
                    self._active_generation is None
                    and self._completed_generation >= self._generation
                ):
                    self._condition.notify_all()

    def _prefetch_window(
        self,
        generation: int,
        refs: tuple[TraceRef, ...],
    ) -> None:
        if not refs:
            return

        for ref in refs:
            if self._is_stale(generation):
                return
            with self._cache_lock:
                if ref in self._cache or ref not in self._desired_refs:
                    continue
            record = self._loader.try_load(ref)
            if record is None:
                continue
            if self._is_stale(generation):
                return
            with self._cache_lock:
                if ref not in self._desired_refs:
                    continue
                self._cache[ref] = record
                desired = set(self._desired_refs)
                self._cache = {
                    cached_ref: cached_record
                    for cached_ref, cached_record in self._cache.items()
                    if cached_ref in desired
                }
