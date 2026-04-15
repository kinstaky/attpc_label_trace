import polars as pl
from pathlib import Path

def main():
	BASE = Path(__file__).resolve().parent
	source_path = BASE / "config"
	detector_path = BASE.parents[1] / "src" / "attpc_estimator" / "detector"
	pad_updown_path = source_path / "padupdown.csv"

	pad_xy = pl.read_csv(source_path / "padxy.csv")
	pad_scale = pl.read_csv(source_path / "padscale.csv")
	rcnp_map = pl.read_csv(source_path / "rcnp_map.csv")
	pad_map = (
		rcnp_map
		.filter(pl.col("det keyword") == "pad")
		.select(["cobo", "asad", "aget", "aget channel", "det channel"])
	)

	pad_xy = pad_xy.with_row_index("pad")
	pad_scale = pad_scale.with_row_index("pad")
	pad_map = pad_map.rename({
		"aget channel": "channel",
		"det channel": "pad"
	})

	joined = pad_xy.join(pad_scale, on="pad", how="left")
	if pad_updown_path.exists():
		pad_updown = pl.read_csv(pad_updown_path).with_row_index("pad")
		joined = joined.join(pad_updown, on="pad", how="left")
	else:
		joined = joined.with_columns(pl.lit(None).alias("direction"))

	joined = joined.join(pad_map, on="pad", how="left")

	if pad_updown_path.exists():
		edge = 4.908235
		offset = edge * (3**0.5) / 6
		joined = joined.with_columns(
			(
				(-pl.col("x")).alias("cy")
			),
			(
				pl.when(pl.col("direction") == 0)
				.then(-pl.col("y") + offset*pl.col("scale"))
				.otherwise(-pl.col("y") - offset*pl.col("scale"))
				.alias("cx")
			)
		)

	joined.write_json(detector_path / "pads.json")
	joined.write_csv(detector_path / "pads.csv")

if __name__ == "__main__":
	main()
