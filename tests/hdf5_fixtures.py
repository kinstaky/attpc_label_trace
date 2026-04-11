from __future__ import annotations

from pathlib import Path

import h5py
import numpy as np


def write_events_hdf5(
    path: Path,
    events: dict[int, np.ndarray],
    *,
    bad_events: np.ndarray | None = None,
    version: str | None = "libattpc_merger:2.0",
) -> None:
    with h5py.File(path, "w") as handle:
        event_ids = sorted(events)
        group = handle.create_group("events")
        group.attrs["min_event"] = min(event_ids)
        group.attrs["max_event"] = max(event_ids)
        group.attrs["bad_events"] = (
            np.asarray([], dtype=np.int64)
            if bad_events is None
            else np.asarray(bad_events, dtype=np.int64)
        )
        if version is not None:
            group.attrs["version"] = version

        for event_id in event_ids:
            event_group = group.create_group(f"event_{event_id}")
            get_group = event_group.create_group("get")
            get_group.create_dataset("pads", data=np.asarray(events[event_id], dtype=np.float32))


def write_legacy_hdf5(path: Path, events: dict[int, np.ndarray]) -> None:
    with h5py.File(path, "w") as handle:
        event_ids = sorted(events)
        meta_group = handle.create_group("meta")
        meta_group.create_dataset(
            "meta",
            data=np.asarray(
                [float(min(event_ids)), 0.0, float(max(event_ids)), 0.0],
                dtype=np.float64,
            ),
        )

        get_group = handle.create_group("get")
        for event_id in event_ids:
            get_group.create_dataset(
                f"evt{event_id}_data",
                data=np.asarray(events[event_id], dtype=np.float32),
            )

        frib_group = handle.create_group("frib")
        frib_group.create_group("evt")
