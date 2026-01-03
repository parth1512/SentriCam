import argparse
import time

import cv2

from detector import PlateDetector
from ocr_reader import OCR
from augmentations import preprocess_for_ocr


def parse_args() -> argparse.Namespace:
	import argparse
	parser = argparse.ArgumentParser()
	parser.add_argument("--device", type=str, default="mps")
	parser.add_argument("--weights", type=str, default="weights/plate_detector.pt")
	parser.add_argument("--conf", type=float, default=0.35)
	return parser.parse_args()


def main() -> None:
	args = parse_args()
	detector = PlateDetector(args.weights, device=args.device)
	ocr = OCR()
	cap = cv2.VideoCapture(0)
	if not cap.isOpened():
		raise RuntimeError("Cannot open webcam")
	while True:
		ret, frame = cap.read()
		if not ret:
			break
		start = time.time()
		dets = detector.predict(frame, conf=args.conf)
		for d in dets:
			x1, y1, x2, y2 = d.bbox
			cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
			crop = detector.crop(frame, d.bbox)
			crop = preprocess_for_ocr(crop)
			text, conf = ocr.recognize_plate(crop)
			label = f"{text} ({conf:.2f})"
			cv2.putText(frame, label, (x1, max(0, y1 - 10)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
		fps = 1.0 / max(1e-6, (time.time() - start))
		cv2.putText(frame, f"FPS: {fps:.1f}", (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
		cv2.imshow("ANPR Webcam", frame)
		if cv2.waitKey(1) & 0xFF == ord('q'):
			break
	cap.release()
	cv2.destroyAllWindows()


if __name__ == "__main__":
	main()







