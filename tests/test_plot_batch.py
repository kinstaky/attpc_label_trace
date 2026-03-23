from __future__ import annotations

import sys
import types
from pathlib import Path

import numpy as np

from trace_label.plot_batch import load_batch_histogram, main


class FakeAxes:
    def imshow(self, data, origin, aspect, extent, cmap, norm):
        return object()

    def set_title(self, title) -> None:
        return None

    def set_xlabel(self, label) -> None:
        return None

    def set_ylabel(self, label) -> None:
        return None

    def set_xlim(self, left, right) -> None:
        return None

    def set_ylim(self, bottom, top) -> None:
        return None


class FakeColorbar:
    def set_label(self, label) -> None:
        return None


class FakeLogNorm:
    def __init__(self, vmin, vmax) -> None:
        self.vmin = vmin
        self.vmax = vmax


class FakeFigure:
    def tight_layout(self) -> None:
        return None

    def savefig(self, path: Path, dpi: int) -> None:
        Path(path).write_bytes(b"fake-png")

    def colorbar(self, image, ax):
        return FakeColorbar()


def install_fake_matplotlib(monkeypatch) -> None:
    fake_matplotlib = types.ModuleType("matplotlib")
    fake_matplotlib.use = lambda backend: None

    fake_colors = types.ModuleType("matplotlib.colors")
    fake_colors.LogNorm = FakeLogNorm

    fake_pyplot = types.ModuleType("matplotlib.pyplot")
    fake_pyplot.subplots = lambda figsize: (FakeFigure(), FakeAxes())
    fake_pyplot.close = lambda fig: None

    monkeypatch.setitem(sys.modules, "matplotlib", fake_matplotlib)
    monkeypatch.setitem(sys.modules, "matplotlib.colors", fake_colors)
    monkeypatch.setitem(sys.modules, "matplotlib.pyplot", fake_pyplot)


def test_load_batch_histogram_rejects_wrong_shape(tmp_path) -> None:
    input_path = tmp_path / "bad.npy"
    np.save(input_path, np.ones((149, 100), dtype=np.float32))

    try:
        load_batch_histogram(input_path)
    except SystemExit as exc:
        assert "expected histogram shape" in str(exc)
    else:
        raise AssertionError("expected load_batch_histogram to reject the input shape")


def test_plot_batch_main_writes_heatmap_png(tmp_path, monkeypatch) -> None:
    install_fake_matplotlib(monkeypatch)

    input_path = tmp_path / "cdf_hist2d.npy"
    output_dir = tmp_path / "plots"
    np.save(input_path, np.full((150, 100), 3, dtype=np.int64))

    monkeypatch.setattr(sys, "argv", ["plot-batch", "-i", str(input_path), "-o", str(output_dir)])
    main()

    assert (output_dir / "cdf_hist2d.png").is_file()
