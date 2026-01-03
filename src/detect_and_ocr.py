import argparse
import json
from pathlib import Path

import cv2

from detector import PlateDetector
from ocr_reader import OCR
from augmentations import preprocess_for_ocr
from utils import timestamp


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser()
	parser.add_argument("--image", type=str, required=True)
	parser.add_argument("--weights", type=str, default=str(Path(__file__).resolve().parents[1] / "weights" / "plate_detector.pt"))
	parser.add_argument("--device", type=str, default="mps")
	parser.add_argument("--conf", type=float, default=0.25)
	return parser.parse_args()


def main() -> None:
	args = parse_args()
	image_path = Path(args.image)
	img = cv2.imread(str(image_path))
	if img is None:
		raise FileNotFoundError(f"Could not read image: {image_path}")

	detector = PlateDetector(weights_path=args.weights, device=args.device)
	dets = detector.predict(img, conf=args.conf)

	ocr = OCR()
	plate_text = ""
	plate_conf = 0.0
	ocr_conf = 0.0
	bbox = None
	if dets:
		# choose highest-confidence detection
		best = max(dets, key=lambda d: d.confidence)
		bbox = best.bbox
		crop = PlateDetector.crop(img, bbox)
		crop = preprocess_for_ocr(crop)
		plate_text, ocr_conf = ocr.recognize_plate(crop)
		plate_conf = best.confidence

	result = {
		"plate_number": plate_text,
		"plate_confidence": round(float(plate_conf), 4),
		"ocr_confidence": round(float(ocr_conf), 4),
		"bbox": list(bbox) if bbox else None,
		"timestamp": timestamp(),
	}
	print(json.dumps(result, indent=2))


if __name__ == "__main__":
	main()







