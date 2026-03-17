from __future__ import annotations

import random

import h5py
import numpy as np

from trace_label.services import TraceLabelService


def write_hdf5_input(path) -> None:
    with h5py.File(path, "w") as handle:
        events = handle.create_group("events")
        events.attrs["min_event"] = 1
        events.attrs["max_event"] = 2
        events.attrs["bad_events"] = np.array([], dtype=np.int64)

        event_1 = events.create_group("event_1")
        get_1 = event_1.create_group("get")
        get_1.create_dataset(
            "pads",
            data=np.array(
                [
                    [10, 11, 12, 13, 14, 1, 2, 3],
                    [20, 21, 22, 23, 24, 4, 5, 6],
                ],
                dtype=np.float32,
            ),
        )

        event_2 = events.create_group("event_2")
        get_2 = event_2.create_group("get")
        get_2.create_dataset(
            "pads",
            data=np.array(
                [
                    [30, 31, 32, 33, 34, 7, 8, 9],
                ],
                dtype=np.float32,
            ),
        )


def test_bootstrap_and_normal_label_flow(tmp_path) -> None:
    random.seed(1)
    input_path = tmp_path / "run_0001.h5"
    db_dir = tmp_path / "db"
    write_hdf5_input(input_path)

    service = TraceLabelService(input_path=input_path, db_dir=db_dir)

    bootstrap = service.bootstrap_state()
    assert bootstrap["totalTraces"] == 3
    assert bootstrap["labeledCount"] == 0

    trace = service.next_trace()
    assert trace["traceKey"]["run"] == "0001"
    assert len(trace["hardwareId"]) == 5
    assert trace["currentLabel"] is None

    result = service.save_label(
        run=trace["traceKey"]["run"],
        event_id=trace["traceKey"]["eventId"],
        trace_id=trace["traceKey"]["traceId"],
        family="normal",
        label="3",
    )
    assert result["labeledCount"] == 1
    assert result["currentLabel"]["family"] == "normal"
    assert result["currentLabel"]["label"] == "3"

    previous = service.previous_trace()
    assert previous["traceKey"] == trace["traceKey"]
    assert previous["currentLabel"]["label"] == "3"


def test_strange_label_flow_and_no_duplicate_random_trace(tmp_path) -> None:
    random.seed(3)
    input_path = tmp_path / "run_0002.h5"
    db_dir = tmp_path / "db"
    write_hdf5_input(input_path)

    service = TraceLabelService(input_path=input_path, db_dir=db_dir)

    first_trace = service.next_trace()
    first_key = first_trace["traceKey"]
    service.save_label(
        run=first_key["run"],
        event_id=first_key["eventId"],
        trace_id=first_key["traceId"],
        family="normal",
        label="1",
    )

    second_trace = service.next_trace()
    assert second_trace["traceKey"] != first_key

    create_result = service.create_strange_label("Noise", "n")
    label_id = create_result["createdLabel"]["id"]
    save_result = service.save_label(
        run=second_trace["traceKey"]["run"],
        event_id=second_trace["traceKey"]["eventId"],
        trace_id=second_trace["traceKey"]["traceId"],
        family="strange",
        label=str(label_id),
    )
    assert save_result["currentLabel"]["label"] == "Noise"

    previous = service.previous_trace()
    assert previous["traceKey"] == first_key


def test_reserved_shortcuts_and_duplicate_labels_are_rejected(tmp_path) -> None:
    random.seed(9)
    input_path = tmp_path / "run_0003.h5"
    db_dir = tmp_path / "db"
    write_hdf5_input(input_path)
    service = TraceLabelService(input_path=input_path, db_dir=db_dir)

    try:
        service.create_strange_label("Broken", "q")
    except ValueError as exc:
        assert "reserved" in str(exc)
    else:
        raise AssertionError("expected reserved shortcut to fail")

    trace = service.next_trace()
    trace_key = trace["traceKey"]
    service.save_label(
        run=trace_key["run"],
        event_id=trace_key["eventId"],
        trace_id=trace_key["traceId"],
        family="normal",
        label="2",
    )

    try:
        service.save_label(
            run=trace_key["run"],
            event_id=trace_key["eventId"],
            trace_id=trace_key["traceId"],
            family="normal",
            label="4",
        )
    except ValueError as exc:
        assert "already labeled" in str(exc)
    else:
        raise AssertionError("expected duplicate label to fail")
