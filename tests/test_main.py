from __future__ import annotations

import sys

from attpc_estimator.cli import webui


def test_webui_main_uses_cli_workspace_and_trace_path(tmp_path, monkeypatch) -> None:
    trace_root = tmp_path / "traces"
    trace_root.mkdir()
    (trace_root / "run_0042.h5").touch()
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    captured: dict[str, object] = {}

    class DummyService:
        def __init__(self, trace_path, workspace) -> None:
            captured["trace_path"] = trace_path
            captured["workspace"] = workspace

    monkeypatch.setattr(
        sys,
        "argv",
        ["webui", "-t", str(trace_root), "-w", str(workspace)],
    )
    monkeypatch.setattr(webui, "EstimatorService", DummyService)
    monkeypatch.setattr(webui, "create_app", lambda service, frontend_dist: object())
    monkeypatch.setattr(webui, "_pick_port", lambda preferred_port: 8765)
    monkeypatch.setattr(webui.uvicorn, "run", lambda *args, **kwargs: None)

    webui.main()

    assert captured["trace_path"] == trace_root.resolve()
    assert captured["workspace"] == workspace.resolve()


def test_webui_main_reads_options_from_config_file(tmp_path, monkeypatch) -> None:
    trace_root = tmp_path / "traces"
    trace_root.mkdir()
    (trace_root / "run_0042.h5").touch()
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        "\n".join(
            [
                f'trace_path = "{trace_root}"',
                f'workspace = "{workspace}"',
                "port = 9001",
            ]
        ),
        encoding="utf-8",
    )
    captured: dict[str, object] = {}

    class DummyService:
        def __init__(self, trace_path, workspace) -> None:
            captured["trace_path"] = trace_path
            captured["workspace"] = workspace

    monkeypatch.setattr(sys, "argv", ["webui", "-c", str(config_path)])
    monkeypatch.setattr(webui, "EstimatorService", DummyService)
    monkeypatch.setattr(webui, "create_app", lambda service, frontend_dist: object())
    monkeypatch.setattr(webui, "_pick_port", lambda preferred_port: preferred_port)
    monkeypatch.setattr(webui.uvicorn, "run", lambda *args, **kwargs: None)

    webui.main()

    assert captured["trace_path"] == trace_root.resolve()
    assert captured["workspace"] == workspace.resolve()
