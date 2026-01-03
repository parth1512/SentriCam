from __future__ import annotations

from dataclasses import dataclass
from typing import List, Tuple, Optional

import cv2
import numpy as np
from ultralytics import YOLO


@dataclass
class Detection:
	bbox: Tuple[int, int, int, int]
	confidence: float
	class_id: int
	class_name: str


class PlateDetector:
	def __init__(self, weights_path: str, device: str = "mps") -> None:
		self.model = YOLO(weights_path)
		self.device = device

	def predict(self, image_bgr: np.ndarray, conf: float = 0.25) -> List[Detection]:
		results = self.model.predict(source=image_bgr, device=self.device, conf=conf, verbose=False)
		detections: List[Detection] = []
		if not results:
			return detections
		res = results[0]
		names = res.names
		for b in res.boxes:
			x1, y1, x2, y2 = b.xyxy[0].cpu().numpy().astype(int).tolist()
			score = float(b.conf[0].cpu().numpy())
			cls_id = int(b.cls[0].cpu().numpy())
			cls_name = names.get(cls_id, str(cls_id)) if isinstance(names, dict) else str(cls_id)
			detections.append(Detection(bbox=(x1, y1, x2, y2), confidence=score, class_id=cls_id, class_name=cls_name))
		return detections

	@staticmethod
	def crop(image_bgr: np.ndarray, bbox: Tuple[int, int, int, int]) -> np.ndarray:
		x1, y1, x2, y2 = bbox
		h, w = image_bgr.shape[:2]
		x1 = max(0, min(w - 1, x1))
		y1 = max(0, min(h - 1, y1))
		x2 = max(0, min(w, x2))
		y2 = max(0, min(h, y2))
		return image_bgr[y1:y2, x1:x2].copy()







