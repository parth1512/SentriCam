import argparse
import json
from pathlib import Path
from typing import Dict, Any, List, Optional

import numpy as np
import pandas as pd
from ultralytics import YOLO
import matplotlib.pyplot as plt

from detector import PlateDetector
from ocr_reader import OCR
from augmentations import preprocess_for_ocr
from utils import ensure_dir, write_json


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser()
	parser.add_argument("--data", type=str, default=str(Path(__file__).resolve().parents[1] / "data" / "data.yaml"))
	parser.add_argument("--weights", type=str, default=str(Path(__file__).resolve().parents[1] / "weights" / "plate_detector.pt"))
	parser.add_argument("--device", type=str, default="mps")
	parser.add_argument("--results-dir", type=str, default=str(Path(__file__).resolve().parents[1] / "results"))
	return parser.parse_args()


def load_gt_texts(csv_path: Path) -> Dict[str, str]:
	if not csv_path.exists():
		return {}
	df = pd.read_csv(csv_path)
	mapping: Dict[str, str] = {}
	for _, row in df.iterrows():
		mapping[str(row["filename"])]= str(row["text"]).strip()
	return mapping


def evaluate_detector(model_path: str, data_yaml: str, device: str, results_dir: Path) -> Dict[str, Any]:
	model = YOLO(model_path)
	metrics = model.val(data=data_yaml, device=device, split="test")
	# Extract main metrics
	out = {
		"precision": float(metrics.box.map_per_class.mean() if hasattr(metrics.box, 'map_per_class') and metrics.box.map_per_class is not None else metrics.box.mp if hasattr(metrics.box, 'mp') else float('nan')),
		"recall": float(metrics.box.mr if hasattr(metrics.box, 'mr') else float('nan')),
		"mAP50": float(metrics.box.map50 if hasattr(metrics.box, 'map50') else float('nan')),
		"mAP50_95": float(metrics.box.map if hasattr(metrics.box, 'map') else float('nan')),
	}
	# Save PR curve and F1 curve if available
	try:
		pr_path = results_dir / "plots" / "precision_recall_curve.png"
		f1_path = results_dir / "plots" / "f1_curve.png"
		metrics.plot_pr_curve(save_dir=str(pr_path.parent))
		# metrics object in latest Ultralytics doesn't always expose F1 plot; fallback to results.csv based
		# We won't error if unavailable.
	except Exception:
		pass
	return out


def evaluate_ocr_on_detections(weights: str, device: str, data_root: Path, gt_texts: Dict[str, str]) -> Dict[str, Any]:
	# Iterate over test images and run detection + OCR
	images_dir = data_root / "images" / "test"
	detector = PlateDetector(weights, device=device)
	ocr = OCR()
	n = 0
	char_hits = 0
	char_total = 0
	plate_hits = 0
	times: List[float] = []
	for img_path in images_dir.rglob("*.jpg"):
		import time
		start = time.time()
		import cv2
		img = cv2.imread(str(img_path))
		if img is None:
			continue
		dets = detector.predict(img)
		pred_text = ""
		if dets:
			best = max(dets, key=lambda d: d.confidence)
			crop = detector.crop(img, best.bbox)
			crop = preprocess_for_ocr(crop)
			pred_text, _ = ocr.recognize_plate(crop)
		elapsed = time.time() - start
		times.append(elapsed)
		fname = img_path.name
		gt = gt_texts.get(fname)
		if gt is not None and pred_text:
			gt_s = gt.strip().replace(" ", "")
			pr_s = pred_text.strip().replace(" ", "")
			char_total += max(len(gt_s), len(pr_s))
			char_hits += sum(1 for a, b in zip(gt_s, pr_s) if a == b)
			plate_hits += 1 if gt_s == pr_s else 0
			n += 1
	
	char_acc = (char_hits / char_total) if char_total > 0 else None
	plate_acc = (plate_hits / n) if n > 0 else None
	avg_time = float(np.mean(times)) if times else None
	return {
		"ocr_char_accuracy": char_acc,
		"ocr_plate_accuracy": plate_acc,
		"avg_processing_time": avg_time,
	}


def main() -> None:
	args = parse_args()
	results_dir = Path(args.results_dir)
	ensure_dir(results_dir / "plots")

	# Detection metrics
	det_metrics = evaluate_detector(args.weights, args.data, args.device, results_dir)

	# OCR metrics (optional if gt_plates.csv present)
	data_root = Path(args.data).parent
	gt_csv = data_root / "gt_plates.csv"
	gt_texts = load_gt_texts(gt_csv)
	ocr_metrics: Dict[str, Any] = {"ocr_char_accuracy": None, "ocr_plate_accuracy": None, "avg_processing_time": None}
	if gt_texts:
		ocr_metrics = evaluate_ocr_on_detections(args.weights, args.device, data_root, gt_texts)

	# F1-score from precision/recall
	p = det_metrics.get("precision")
	r = det_metrics.get("recall")
	f1 = (2 * p * r / (p + r)) if p is not None and r is not None and (p + r) > 0 else None

	summary = {
		"precision": det_metrics.get("precision"),
		"recall": det_metrics.get("recall"),
		"f1_score": f1,
		"mAP50": det_metrics.get("mAP50"),
		"mAP50_95": det_metrics.get("mAP50_95"),
		"ocr_char_accuracy": ocr_metrics.get("ocr_char_accuracy"),
		"ocr_plate_accuracy": ocr_metrics.get("ocr_plate_accuracy"),
		"avg_processing_time": ocr_metrics.get("avg_processing_time"),
	}

	write_json(summary, results_dir / "metrics.json")
	print(json.dumps(summary, indent=2))


if __name__ == "__main__":
	main()







