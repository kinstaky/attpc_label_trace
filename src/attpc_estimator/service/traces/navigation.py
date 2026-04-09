from __future__ import annotations

from ...model.trace import TraceRef


class Navigator:
    def __init__(self, *, review_mode: bool) -> None:
        self.review_mode = review_mode
        self.stack: list[TraceRef] = []
        self.index = -1

    def replace_stack(
        self,
        refs: list[TraceRef],
        *,
        keep_current_ref: TraceRef | None = None,
    ) -> None:
        previous_index = self.index
        self.stack = list(refs)
        if not self.stack:
            self.index = -1
            return
        if keep_current_ref is not None and keep_current_ref in self.stack:
            self.index = self.stack.index(keep_current_ref)
            return
        if previous_index < 0:
            self.index = -1
            return
        self.index = min(previous_index, len(self.stack) - 1)

    def extend_stack(self, refs: list[TraceRef]) -> None:
        if refs:
            self.stack.extend(refs)

    def current_ref(self) -> TraceRef | None:
        if self.index < 0 or self.index >= len(self.stack):
            return None
        return self.stack[self.index]

    def next_ref(self, *, clamp_at_end: bool) -> TraceRef:
        if not self.stack:
            raise LookupError("no traces are available")
        if self.index + 1 < len(self.stack):
            self.index += 1
            return self.stack[self.index]
        if clamp_at_end and self.index >= 0:
            return self.stack[self.index]
        raise LookupError("no additional traces are available")

    def previous_ref(self) -> TraceRef:
        if not self.stack or self.index < 0:
            raise LookupError("no trace history is available")
        if self.index > 0:
            self.index -= 1
        return self.stack[self.index]

    def window(self, radius: int) -> list[TraceRef]:
        current = self.current_ref()
        if current is None:
            return []
        start = max(0, self.index - radius)
        stop = min(len(self.stack), self.index + radius + 1)
        forward = self.stack[self.index + 1 : stop]
        backward = list(reversed(self.stack[start : self.index]))
        return [current, *forward, *backward]

    def progress(self) -> dict[str, int] | None:
        if not self.review_mode or not self.stack or self.index < 0:
            return None
        return {"current": self.index + 1, "total": len(self.stack)}
