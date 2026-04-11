from __future__ import annotations

import pytest

from attpc_estimator.storage.run_paths import (
    collect_run_files,
    format_run_id,
    resolve_run_file,
)


def test_resolve_run_file_uses_requested_run_from_directory(tmp_path) -> None:
    trace_root = tmp_path / "traces"
    trace_root.mkdir()
    run_file = trace_root / "run_0008.h5"
    run_file.touch()

    resolved = resolve_run_file(trace_root, 8)

    assert resolved == run_file.resolve()


def test_resolve_run_file_rejects_mismatched_direct_file(tmp_path) -> None:
    run_file = tmp_path / "run_0008.h5"
    run_file.touch()

    with pytest.raises(ValueError, match="not requested run 9"):
        resolve_run_file(run_file, 9)


def test_collect_run_files_still_supports_multi_run_directory(tmp_path) -> None:
    trace_root = tmp_path / "traces"
    trace_root.mkdir()
    run_8 = trace_root / "run_0008.h5"
    run_9 = trace_root / "run_0009.h5"
    run_8.touch()
    run_9.touch()

    run_files = collect_run_files(trace_root)

    assert run_files == {
        8: run_8.resolve(),
        9: run_9.resolve(),
    }


def test_format_run_id_zero_pads_to_four_digits() -> None:
    assert format_run_id(106) == "0106"
    assert format_run_id("1056") == "1056"
