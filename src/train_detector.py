import argparse
from pathlib import Path
from typing import Dict, Any

import pandas as pd
from ultralytics import YOLO

from utils import ensure_dir, save_line_plot


DEFAULT_MODEL = "yolo11s.pt"  # latest Ultralytics YOLO family


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser()
	parser.add_argument("--data", type=str, default=str(Path(__file__).resolve().parents[1] / "data" / "data.yaml"))
	parser.add_argument("--model", type=str, default=DEFAULT_MODEL)
	parser.add_argument("--epochs", type=int, default=100)
	parser.add_argument("--imgsz", type=int, default=640)
	parser.add_argument("--batch", type=int, default=16)
	parser.add_argument("--device", type=str, default="mps")
	parser.add_argument("--project", type=str, default=str(Path(__file__).resolve().parents[1] / "results"))
	parser.add_argument("--name", type=str, default="detector_train")
	parser.add_argument("--resume", action="store_true", help="Resume training from last checkpoint in the run directory")
	return parser.parse_args()


def main() -> None:
	args = parse_args()

	results_dir = Path(args.project)
	ensure_dir(results_dir / "plots")

	model = YOLO(args.model)

	train_results = model.train(
		data=args.data,
		epochs=args.epochs,
		imgsz=args.imgsz,
		batch=args.batch,
		device=args.device,
		project=str(results_dir),
		name=args.name,
		save=True,
		verbose=True,
		resume=args.resume,
		exist_ok=True,
	)

	# Copy best weights to weights/plate_detector.pt
	run_dir = Path(train_results.save_dir)
	best_pt = run_dir / "weights" / "best.pt"
	out_weights = Path(__file__).resolve().parents[1] / "weights" / "plate_detector.pt"
	ensure_dir(out_weights.parent)
	if best_pt.exists():
		import shutil
		shutil.copy2(best_pt, out_weights)
		print(f"Saved best weights to {out_weights}")
	else:
		print("Warning: best.pt not found in run directory.")

	# Plot training curves if results.csv exists
	results_csv = run_dir / "results.csv"
	if results_csv.exists():
		df = pd.read_csv(results_csv)
		epoch = list(range(1, len(df) + 1))
		# Losses
		losses: Dict[str, Any] = {}
		for col in [c for c in df.columns if "loss" in c.lower()]:
			losses[col] = df[col].tolist()
		if losses:
			save_line_plot(epoch, losses, "Training/Validation Loss", "Epoch", "Loss", str(results_dir / "plots" / "loss_curves.png"))
		# Metrics
		metrics = {}
		for key in ["metrics/precision(B)", "metrics/recall(B)", "metrics/mAP50(B)", "metrics/mAP50-95(B)"]:
			if key in df.columns:
				metrics[key] = df[key].tolist()
		if metrics:
			save_line_plot(epoch, metrics, "Validation Metrics", "Epoch", "Score", str(results_dir / "plots" / "val_metrics.png"))

	print("Training complete.")


if __name__ == "__main__":
	main()
