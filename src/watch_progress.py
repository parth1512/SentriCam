import argparse
import os
import sys
import time
from pathlib import Path


def render_bar(progress: float, width: int = 40) -> str:
	progress = max(0.0, min(1.0, progress))
	filled = int(progress * width)
	bar = "#" * filled + "-" * (width - filled)
	return f"[{bar}] {progress*100:5.1f}%"


def main() -> None:
	parser = argparse.ArgumentParser()
	parser.add_argument("--run-dir", type=str, required=True)
	parser.add_argument("--total-epochs", type=int, default=100)
	parser.add_argument("--interval", type=float, default=2.0)
	args = parser.parse_args()

	run_dir = Path(args.run_dir)
	csv_path = run_dir / "results.csv"
	start_time = time.time()
	last_seen_epoch = 0
	avg_epoch_time = None

	print("Watching:", csv_path)
	while True:
		if not csv_path.exists():
			print("Waiting for results.csv...", end="\r")
			time.sleep(args.interval)
			continue
		try:
			with open(csv_path, "r", encoding="utf-8", errors="ignore") as f:
				lines = f.read().strip().splitlines()
			epochs_done = max(0, len(lines) - 1)
		except Exception:
			epochs_done = last_seen_epoch

		if epochs_done > last_seen_epoch:
			elapsed = time.time() - start_time
			avg_epoch_time = elapsed / max(1, epochs_done)
			last_seen_epoch = epochs_done

		remaining = max(0, args.total_epochs - epochs_done)
		eta = remaining * (avg_epoch_time or 0.0)
		bar = render_bar(epochs_done / max(1, args.total_epochs))
		msg = f"Epoch {epochs_done}/{args.total_epochs}  {bar}  ETA: {eta/60:4.1f} min"
		print(msg, end="\r", flush=True)
		if epochs_done >= args.total_epochs:
			print()  # newline
			break
		time.sleep(args.interval)


if __name__ == "__main__":
	main()







