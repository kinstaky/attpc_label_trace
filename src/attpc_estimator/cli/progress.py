from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

from tqdm import tqdm

from ..process.progress import ProgressReporter, ProgressUpdate


@contextmanager
def tqdm_reporter(description: str) -> Iterator[ProgressReporter]:
    progress_bar: tqdm | None = None
    last_current = 0

    def report(update: ProgressUpdate) -> None:
        nonlocal progress_bar, last_current
        if progress_bar is None:
            progress_bar = tqdm(
                total=max(update.total, 0),
                desc=description,
                unit=update.unit,
            )
        if progress_bar.total != update.total:
            progress_bar.total = max(update.total, 0)
        progress_bar.unit = update.unit
        delta = max(0, update.current - last_current)
        if delta:
            progress_bar.update(delta)
        last_current = max(last_current, update.current)
        if update.message:
            progress_bar.set_postfix_str(update.message)

    try:
        yield report
    finally:
        if progress_bar is not None:
            progress_bar.close()
