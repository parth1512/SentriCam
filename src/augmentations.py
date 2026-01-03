from typing import Tuple, Dict, Any

import cv2
import numpy as np
import albumentations as A


DEFAULT_IMG_SIZE: Tuple[int, int] = (640, 640)


def build_train_transforms(img_size: Tuple[int, int] = DEFAULT_IMG_SIZE) -> A.Compose:
	return A.Compose(
		[
			A.Resize(height=img_size[1], width=img_size[0]),
			A.MedianBlur(blur_limit=3, p=0.3),
			A.GaussianBlur(blur_limit=(3, 5), p=0.3),
			A.RandomBrightnessContrast(brightness_limit=0.2, contrast_limit=0.2, p=0.5),
			A.HorizontalFlip(p=0.5),
			A.Rotate(limit=5, border_mode=cv2.BORDER_CONSTANT, p=0.5),
			A.RandomResizedCrop(height=img_size[1], width=img_size[0], scale=(0.9, 1.1), ratio=(0.95, 1.05), p=0.3),
			A.Perspective(scale=(0.02, 0.05), p=0.3),
			A.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
		],
		bbox_params=A.BboxParams(format='yolo', label_fields=['class_labels'], min_visibility=0.2),
	)


def build_val_transforms(img_size: Tuple[int, int] = DEFAULT_IMG_SIZE) -> A.Compose:
	return A.Compose(
		[
			A.Resize(height=img_size[1], width=img_size[0]),
			A.MedianBlur(blur_limit=3, p=0.1),
			A.GaussianBlur(blur_limit=(3, 3), p=0.1),
			A.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
		],
		bbox_params=A.BboxParams(format='yolo', label_fields=['class_labels'], min_visibility=0.2),
	)


def preprocess_for_ocr(img: np.ndarray, to_gray: bool = False) -> np.ndarray:
	"""Minimal preprocessing - OCR module handles detailed preprocessing internally"""
	# Just ensure minimum size for OCR (OCR will do its own preprocessing)
	if img is None or img.size == 0:
		return img
	h, w = img.shape[:2]
	if h < 32 or w < 64:
		# Resize to minimum viable size for Indian plates (wider aspect)
		img = cv2.resize(img, (max(64, w), max(32, h)), interpolation=cv2.INTER_CUBIC)
	return img



