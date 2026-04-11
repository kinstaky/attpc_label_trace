from __future__ import annotations

import sys

from attpc_estimator.cli import webui


def test_webui_main_uses_cli_workspace_and_trace_path(tmp_path, monkeypatch) -> None:
    trace_root = tmp_path / "traces"
    trace_root.mkdir()
    (trace_root / "run_0042.h5").touch()
    (trace_root / "run_0043.h5").touch()
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    captured: dict[str, object] = {}

    class DummyService:
        def __init__(self, trace_path, workspace, default_run=None, verbose=False) -> None:
            captured["trace_path"] = trace_path
            captured["workspace"] = workspace
            captured["default_run"] = default_run
            captured["verbose"] = verbose

    monkeypatch.setattr(
        sys,
        "argv",
        ["webui", "-t", str(trace_root), "-w", str(workspace)],
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(webui, "EstimatorService", DummyService)
    monkeypatch.setattr(webui, "create_app", lambda service, frontend_dist: object())
    monkeypatch.setattr(webui, "_pick_port", lambda preferred_port: 8765)
    monkeypatch.setattr(webui.uvicorn, "run", lambda *args, **kwargs: None)

    webui.main()

    assert captured["trace_path"] == trace_root.resolve()
    assert captured["workspace"] == workspace.resolve()
    assert captured["default_run"] is None
    assert captured["verbose"] is False


def test_webui_main_reads_options_from_config_file(tmp_path, monkeypatch) -> None:
    trace_root = tmp_path / "traces"
    trace_root.mkdir()
    (trace_root / "run_0042.h5").touch()
    (trace_root / "run_0043.h5").touch()
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        "\n".join(
            [
                f'trace_path = "{trace_root}"',
                f'workspace = "{workspace}"',
                "run = 43",
                "port = 9001",
            ]
        ),
        encoding="utf-8",
    )
    captured: dict[str, object] = {}

    class DummyService:
        def __init__(self, trace_path, workspace, default_run=None, verbose=False) -> None:
            captured["trace_path"] = trace_path
            captured["workspace"] = workspace
            captured["default_run"] = default_run
            captured["verbose"] = verbose

    monkeypatch.setattr(sys, "argv", ["webui", "-c", str(config_path)])
    monkeypatch.setattr(webui, "EstimatorService", DummyService)
    monkeypatch.setattr(webui, "create_app", lambda service, frontend_dist: object())
    monkeypatch.setattr(webui, "_pick_port", lambda preferred_port: preferred_port)
    monkeypatch.setattr(webui.uvicorn, "run", lambda *args, **kwargs: None)

    webui.main()

    assert captured["trace_path"] == trace_root.resolve()
    assert captured["workspace"] == workspace.resolve()
    assert captured["default_run"] == 43
    assert captured["verbose"] is False


def test_webui_main_passes_verbose_to_service(tmp_path, monkeypatch) -> None:
    trace_root = tmp_path / "traces"
    trace_root.mkdir()
    (trace_root / "run_0042.h5").touch()
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    captured: dict[str, object] = {}

    class DummyService:
        def __init__(self, trace_path, workspace, default_run=None, verbose=False) -> None:
            captured["trace_path"] = trace_path
            captured["workspace"] = workspace
            captured["default_run"] = default_run
            captured["verbose"] = verbose

    monkeypatch.setattr(
        sys,
        "argv",
        ["webui", "-t", str(trace_root), "-w", str(workspace), "--verbose"],
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(webui, "EstimatorService", DummyService)
    monkeypatch.setattr(webui, "create_app", lambda service, frontend_dist: object())
    monkeypatch.setattr(webui, "_pick_port", lambda preferred_port: 8765)
    monkeypatch.setattr(webui.uvicorn, "run", lambda *args, **kwargs: None)

    webui.main()

    assert captured["verbose"] is True
