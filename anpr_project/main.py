import cv2
from ultralytics import YOLO
import easyocr
import numpy as np

# -----------------------------
# ✅ Load YOLOv10 model
# -----------------------------
model = YOLO("best.pt")      # make sure best.pt is in same folder

# -----------------------------
# ✅ Initialize EasyOCR
# -----------------------------
reader = easyocr.Reader(['en'], gpu=False)

# -----------------------------
# ✅ Plate Correction Function
# -----------------------------
def correct_plate(text):
    """
    Fixes common OCR mistakes for Indian number plates.
    """
    replacements = {
        'I': '1',
        'O': '0',
        'S': '5',
        'Z': '2',
        'B': '8',
    }

    # Special case: M ↔ H confusion
    if text.startswith("H"):
        text = "M" + text[1:]

    new_text = ""
    for ch in text:
        new_text += replacements.get(ch, ch)

    return new_text


# -----------------------------
# ✅ Read Test Image
# -----------------------------
image_path = "test.jpg"
img = cv2.imread(image_path)

if img is None:
    print("❌ ERROR: test.jpg not found in folder.")
    exit()

# -----------------------------
# ✅ YOLO Number Plate Detection
# -----------------------------
results = model(img)

for r in results:
    for box in r.boxes:
        cls = int(box.cls[0])
        if model.names[cls] == "number_plate":

            # get box coords
            x1, y1, x2, y2 = map(int, box.xyxy[0])

            # crop plate
            crop = img[y1:y2, x1:x2]

            # ------------------------------------------------
            # ✅ Preprocessing for better OCR
            # ------------------------------------------------
            gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)

            # sharpen + upscale
            gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

            # threshold clean
            gray = cv2.GaussianBlur(gray, (3, 3), 0)
            _, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            # -----------------------------
            # ✅ OCR Extraction
            # -----------------------------
            result = reader.readtext(thresh, detail=0)

            if len(result) > 0:
                raw_text = result[0]
                fixed_text = correct_plate(raw_text)

                print("Raw OCR:", raw_text)
                print("✅ Corrected Plate:", fixed_text)
            else:
                print("❌ No text detected on number plate.")

            # Show plate for debugging
            cv2.imshow("Detected Plate", crop)
            cv2.imshow("Processed", thresh)
            cv2.waitKey(0)
            cv2.destroyAllWindows()
