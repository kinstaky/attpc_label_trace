from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from .batch import CDF_THRESHOLDS, CDF_VALUE_BINS


def main() -> None:
    args = _parse_args()
    input_path = Path(args.input_file).expanduser().resolve()
    output_dir = Path(args.output_path).expanduser().resolve()

    if not input_path.is_file():
        raise SystemExit(f"input file not found: {input_path}")

    histogram = load_batch_histogram(input_path)
    plot_histogram_heatmap(histogram=histogram, output_dir=output_dir)
    print(f"saved 2D histogram PNG to {output_dir}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render a PNG heatmap from batch.py histogram output")
    parser.add_argument("-i", "--input-file", required=True, help="Path to the histogram .npy file produced by batch.py")
    parser.add_argument(
        "-o",
        "--output-path",
        required=True,
        help="Directory where the histogram PNG file will be written",
    )
    return parser.parse_args()


def load_batch_histogram(input_path: Path) -> np.ndarray:
    histogram = np.load(input_path)
    if histogram.ndim != 2:
        raise SystemExit(f"expected a 2D numpy array, got shape {histogram.shape}")
    expected_shape = (len(CDF_THRESHOLDS), CDF_VALUE_BINS)
    if histogram.shape != expected_shape:
        raise SystemExit(f"expected histogram shape {expected_shape}, got shape {histogram.shape}")
    return np.asarray(histogram, dtype=np.float32)


def plot_histogram_heatmap(histogram: np.ndarray, output_dir: Path) -> None:
    plt, colors = _load_pyplot()
    output_dir.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(12, 6))
    image = ax.imshow(
        histogram.T,
        origin="lower",
        aspect="auto",
        extent=[0.0, float(len(CDF_THRESHOLDS)), 0.0, 1.0],
        cmap="viridis",
        norm=colors.LogNorm(vmin=1.0, vmax=max(1.0, float(np.max(histogram)))),
    )
    ax.set_title("2D Histogram of Batch Matrix Values")
    ax.set_xlabel("F index")
    ax.set_ylabel("CDF value")
    ax.set_xlim(0.0, float(len(CDF_THRESHOLDS)))
    ax.set_ylim(0.0, 1.0)
    colorbar = fig.colorbar(image, ax=ax)
    colorbar.set_label("Count (log scale)")
    fig.tight_layout()
    fig.savefig(output_dir / "cdf_hist2d.png", dpi=200)
    plt.close(fig)


def _load_pyplot():
    import matplotlib

    matplotlib.use("Agg")

    import matplotlib.colors as colors
    import matplotlib.pyplot as plt

    return plt, colors


if __name__ == "__main__":
    main()
