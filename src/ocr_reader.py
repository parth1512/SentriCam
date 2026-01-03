from __future__ import annotations

import re
from typing import Tuple, List

import cv2
import numpy as np


def preprocess_for_indian_plates(img: np.ndarray) -> List[np.ndarray]:
	"""Generate multiple preprocessed versions optimized for Indian number plates"""
	processed = []
	
	# Convert to grayscale if needed
	if len(img.shape) == 3:
		gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
	else:
		gray = img.copy()
	
	# Original grayscale
	processed.append(gray)
	
	# 1. High contrast with CLAHE
	clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
	clahe_img = clahe.apply(gray)
	processed.append(clahe_img)
	
	# 2. Adaptive thresholding
	adaptive = cv2.adaptiveThreshold(
		gray, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
	)
	processed.append(adaptive)
	
	# 3. Morphological operations to clean up
	kernel = np.ones((2, 2), np.uint8)
	morph = cv2.morphologyEx(gray, cv2.MORPH_CLOSE, kernel)
	morph = cv2.morphologyEx(morph, cv2.MORPH_OPEN, kernel)
	processed.append(morph)
	
	# 4. Denoised + sharpened
	denoised = cv2.fastNlMeansDenoising(gray, None, 10, 7, 21)
	kernel_sharpen = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
	sharpened = cv2.filter2D(denoised, -1, kernel_sharpen)
	processed.append(sharpened)
	
	# 5. Resize to optimal size for OCR (wider aspect ratio for Indian plates)
	resized = cv2.resize(gray, (320, 80), interpolation=cv2.INTER_CUBIC)
	processed.append(resized)
	
	# Convert all back to 3-channel BGR for OCR compatibility
	result = []
	for p in processed:
		if len(p.shape) == 2:
			p = cv2.cvtColor(p, cv2.COLOR_GRAY2BGR)
		result.append(p)
	
	return result


# Valid Indian state codes
VALID_STATE_CODES = {
	'AP', 'AR', 'AS', 'BR', 'CG', 'GA', 'GJ', 'HR', 'HP', 'JH', 'JK', 'KA', 'KL',
	'MP', 'MH', 'MN', 'ML', 'MZ', 'NL', 'OD', 'OR', 'PB', 'RJ', 'SK', 'TN', 'TS',
	'TR', 'UP', 'UK', 'UA', 'WB', 'AN', 'CH', 'DN', 'DD', 'DL', 'LA', 'LD', 'PY'
}

# Common OCR character corrections (only apply in appropriate positions)
OCR_CORRECTIONS = {
	'O': '0',  # O -> 0 (in number positions)
	'I': '1',  # I -> 1 (in number positions)
	'S': '5',  # S -> 5 (in number positions)
	'Z': '2',  # Z -> 2 (in number positions)
	'B': '8',  # B -> 8 (in number positions)
	'0': 'O',  # 0 -> O (in letter positions, but be careful)
	'1': 'I',  # 1 -> I (in letter positions, but be careful)
	'5': 'S',  # 5 -> S (in letter positions, but be careful)
	'8': 'B',  # 8 -> B (in letter positions, but be careful)
}


def validate_and_fix_indian_plate(text: str) -> str:
	"""
	Validate and fix Indian number plate format: XX##XX####
	Format: 2 letters (state code) + 2 digits + 2 letters + 4 digits
	Example: MH15GA6565
	"""
	if not text:
		return ""
	
	# Remove all non-alphanumeric characters
	cleaned = re.sub(r'[^A-Z0-9]', '', text.upper().strip())
	
	# Must be exactly 10 characters
	if len(cleaned) != 10:
		return ""
	
	# Extract parts: [0:2] = state code, [2:4] = district, [4:6] = series, [6:10] = number
	state_part = cleaned[0:2]
	district_part = cleaned[2:4]
	series_part = cleaned[4:6]
	number_part = cleaned[6:10]
	
	# Validate state code
	if state_part not in VALID_STATE_CODES:
		# Try to fix common OCR errors in state code
		for code in VALID_STATE_CODES:
			# Check if it's a one-character difference
			if sum(a != b for a, b in zip(state_part, code)) == 1:
				state_part = code
				break
		else:
			# If no valid state code found, return empty
			return ""
	
	# Validate district (must be 2 digits)
	if not district_part.isdigit():
		# Try to fix OCR errors in digits
		fixed_district = ""
		for char in district_part:
			if char.isdigit():
				fixed_district += char
			elif char in OCR_CORRECTIONS and OCR_CORRECTIONS[char].isdigit():
				fixed_district += OCR_CORRECTIONS[char]
			else:
				return ""  # Can't fix
		district_part = fixed_district
		if len(district_part) != 2:
			return ""
	
	# Validate series (must be 2 letters)
	if not series_part.isalpha():
		# Try to fix OCR errors in letters
		fixed_series = ""
		for char in series_part:
			if char.isalpha():
				fixed_series += char
			elif char in OCR_CORRECTIONS and OCR_CORRECTIONS[char].isalpha():
				fixed_series += OCR_CORRECTIONS[char]
			else:
				return ""  # Can't fix
		series_part = fixed_series.upper()
		if len(series_part) != 2:
			return ""
	
	# Validate number (must be 4 digits)
	if not number_part.isdigit():
		# Try to fix OCR errors in digits
		fixed_number = ""
		for char in number_part:
			if char.isdigit():
				fixed_number += char
			elif char in OCR_CORRECTIONS and OCR_CORRECTIONS[char].isdigit():
				fixed_number += OCR_CORRECTIONS[char]
			else:
				return ""  # Can't fix
		number_part = fixed_number
		if len(number_part) != 4:
			return ""
	
	# Reconstruct valid plate
	return f"{state_part}{district_part}{series_part}{number_part}"


def clean_indian_plate_text(text: str) -> str:
	"""Clean and validate Indian number plate text with strict format validation"""
	if not text:
		return ""
	
	# Remove all non-alphanumeric characters and convert to uppercase
	cleaned = re.sub(r'[^A-Z0-9]', '', text.upper().strip())
	
	# First, try to extract exact pattern: 2 letters + 2 digits + 2 letters + 4 digits
	pattern = r'([A-Z]{2})(\d{2})([A-Z]{2})(\d{4})'
	match = re.search(pattern, cleaned)
	
	if match:
		state, district, series, number = match.groups()
		candidate = f"{state}{district}{series}{number}"
		# Validate the candidate (especially state code)
		validated = validate_and_fix_indian_plate(candidate)
		if validated:
			return validated
	
	# If no exact pattern match, try the entire cleaned string if it's exactly 10 chars
	if len(cleaned) == 10:
		validated = validate_and_fix_indian_plate(cleaned)
		if validated:
			return validated
	
	# If still no match, try to extract and fix from longer strings
	# Look for any 10-character sequence that might be a plate
	if len(cleaned) >= 10:
		for i in range(len(cleaned) - 9):
			candidate = cleaned[i:i+10]
			validated = validate_and_fix_indian_plate(candidate)
			if validated:
				return validated
	
	# Last resort: try to build from parts if we can find them separately
	# Look for state code first
	for state_code in VALID_STATE_CODES:
		if state_code in cleaned:
			idx = cleaned.find(state_code)
			if idx + 10 <= len(cleaned):
				candidate = cleaned[idx:idx+10]
				validated = validate_and_fix_indian_plate(candidate)
				if validated:
					return validated
	
	return ""


class PaddleOCRReader:
	def __init__(self) -> None:
		from paddleocr import PaddleOCR  # type: ignore
		# Use English + better config for Indian plates
		# PaddleOCR 3.x uses different parameters:
		# - use_angle_cls is deprecated, use use_textline_orientation instead
		# - use_gpu and show_log are no longer supported
		try:
			# Try with PaddleOCR 3.x parameter format
			self.ocr = PaddleOCR(
				lang='en',
				use_textline_orientation=True  # Replaces deprecated use_angle_cls
			)
		except (TypeError, ValueError) as e:
			# Fallback for older versions or if parameters are not supported
			try:
				# Try with deprecated parameter name for older versions
				self.ocr = PaddleOCR(
					lang='en',
					use_angle_cls=True
				)
			except Exception:
				# If still fails, try minimal initialization
				self.ocr = PaddleOCR(lang='en')

	def read(self, image_bgr: np.ndarray) -> Tuple[str, float]:
		"""
		Read text from image using PaddleOCR
		Returns: (cleaned_text, average_confidence)
		"""
		try:
			img = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
			res = self.ocr.ocr(img, cls=True)
			
			texts = []
			confs = []
			
			# Handle PaddleOCR response format
			if res is None:
				return ("", 0.0)
			
			# PaddleOCR returns list of pages, each page is a list of detections
			for page in res:
				if page is None:
					continue
				for line in page:
					if line is None or len(line) < 2:
						continue
					
					# PaddleOCR format: [[[x1,y1], [x2,y2], [x3,y3], [x4,y4]], (text, confidence)]
					bbox = line[0]  # Bounding box coordinates
					text_info = line[1]  # (text, confidence) tuple
					
					if isinstance(text_info, (list, tuple)) and len(text_info) >= 2:
						text = str(text_info[0]) if text_info[0] else ""
						conf = float(text_info[1]) if text_info[1] is not None else 0.0
					else:
						text = str(text_info) if text_info else ""
						conf = 0.0
					
					if text:
						texts.append(text)
						confs.append(conf)
			
			if texts:
				combined = "".join(texts)
				cleaned = clean_indian_plate_text(combined)
				avg_conf = float(np.mean(confs) if confs else 0.0)
				return (cleaned, avg_conf)
			
			return ("", 0.0)
		except Exception as e:
			# Return empty on any error (don't print to avoid spam)
			return ("", 0.0)


class EasyOCRReader:
	def __init__(self) -> None:
		import easyocr  # type: ignore
		# EasyOCR with English - works well for Indian plates
		self.reader = easyocr.Reader(['en'], gpu=False, verbose=False)

	def read(self, image_bgr: np.ndarray) -> Tuple[str, float]:
		img = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
		# Use better parameters for Indian plates
		res = self.reader.readtext(
			img,
			detail=1,
			paragraph=False,
			width_ths=0.7,
			height_ths=0.7,
			slope_ths=0.1,
			ycenter_ths=0.5,
			mag_ratio=1.5
		)
		texts = []
		confs = []
		for (bbox, _text, conf) in res:
			texts.append(_text)
			try:
				confs.append(float(conf))
			except Exception:
				pass
		if texts:
			combined = "".join(texts)
			cleaned = clean_indian_plate_text(combined)
			avg_conf = float(np.mean(confs) if confs else 0.0)
			return (cleaned, avg_conf)
		return ("", 0.0)


class OCR:
	def __init__(self) -> None:
		self.primary = None  # PaddleOCR
		self.fallback = None  # EasyOCR
		
		# Load PaddleOCR
		try:
			self.primary = PaddleOCRReader()
			print("✅ PaddleOCR loaded")
		except Exception as e:
			print(f"⚠️ PaddleOCR failed: {e}")
			self.primary = None
		
		# Load EasyOCR
		try:
			self.fallback = EasyOCRReader()
			print("✅ EasyOCR loaded")
		except Exception as e:
			print(f"⚠️ EasyOCR failed: {e}")
			self.fallback = None
		
		# Check configuration
		if self.primary is not None and self.fallback is not None:
			print("✅ Using PaddleOCR + EasyOCR together for enhanced accuracy")
		elif self.primary is not None:
			print("⚠️ Using PaddleOCR only (EasyOCR not available)")
		elif self.fallback is not None:
			print("⚠️ Using EasyOCR only (PaddleOCR not available)")
		else:
			print("❌ ERROR: No OCR engine available! Please install PaddleOCR or EasyOCR")

	def recognize_plate(self, cropped_plate_img: np.ndarray) -> Tuple[str, float]:
		"""
		Recognize Indian number plate using BOTH PaddleOCR and EasyOCR together
		Combines results from both engines for better accuracy
		"""
		if cropped_plate_img is None or cropped_plate_img.size == 0:
			return ("", 0.0)
		
		# Generate multiple preprocessed versions
		preprocessed_versions = preprocess_for_indian_plates(cropped_plate_img)
		
		# Store results from both OCR engines
		paddle_results = []  # List of (text, confidence) from PaddleOCR
		easyocr_results = []  # List of (text, confidence) from EasyOCR
		
		# Try each preprocessed version with BOTH OCR engines
		for preprocessed_img in preprocessed_versions:
			# Run PaddleOCR
			if self.primary is not None:
				try:
					text, conf = self.primary.read(preprocessed_img)
					if text and len(text) == 10:  # Valid Indian plate format
						paddle_results.append((text, conf))
				except Exception:
					pass
			
			# Run EasyOCR
			if self.fallback is not None:
				try:
					text, conf = self.fallback.read(preprocessed_img)
					if text and len(text) == 10:  # Valid Indian plate format
						easyocr_results.append((text, conf))
				except Exception:
					pass
		
		# Combine and analyze results from both engines
		all_results = paddle_results + easyocr_results
		
		if not all_results:
			return ("", 0.0)
		
		# Strategy 1: If both engines agree on the same text, use it with higher confidence
		text_counts = {}
		text_confidences = {}
		
		for text, conf in all_results:
			if text not in text_counts:
				text_counts[text] = 0
				text_confidences[text] = []
			text_counts[text] += 1
			text_confidences[text].append(conf)
		
		# Find text that appears most frequently (agreement between engines)
		best_text = ""
		best_conf = 0.0
		max_count = 0
		
		for text, count in text_counts.items():
			avg_conf = sum(text_confidences[text]) / len(text_confidences[text])
			
			# Prefer text that appears multiple times (both engines agree)
			# Or has highest confidence if no agreement
			if count > max_count or (count == max_count and avg_conf > best_conf):
				best_text = text
				best_conf = avg_conf
				max_count = count
		
		# Strategy 2: If no agreement, use the result with highest confidence
		if max_count == 1:
			# No agreement - use highest confidence result
			for text, conf in all_results:
				if conf > best_conf:
					best_text = text
					best_conf = conf
		
		# Final validation for Indian plate format
		if best_text:
			validated_text = clean_indian_plate_text(best_text)
			# Only return if validation passed (non-empty result)
			if validated_text and len(validated_text) == 10:
				# Boost confidence if both engines agreed
				if max_count > 1:
					best_conf = min(1.0, best_conf * 1.1)  # Slight boost for agreement
				return (validated_text, best_conf)
			# If validation failed, return empty (invalid format)
			return ("", 0.0)
		
		return ("", 0.0)



