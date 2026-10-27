"""OpenCV/EasyOCR adapter with safe, review-first recognition behavior."""
from __future__ import annotations
from dataclasses import dataclass
import re
from time import monotonic
from services.plates import normalize_plate
from services.rto_decoder import decode_indian_plate


@dataclass(frozen=True)
class RecognitionResult:
    raw_text: str
    normalized_plate: str | None
    confidence: float
    requires_review: bool
    bounding_box: list[float] | None = None
    rto_info: dict | None = None


class DuplicateSuppressor:
    def __init__(self, cooldown_seconds: float = 10.0) -> None:
        self.cooldown_seconds, self._seen = cooldown_seconds, {}

    def is_duplicate(self, plate: str) -> bool:
        now, previous = monotonic(), self._seen.get(plate)
        if previous is not None and now - previous < self.cooldown_seconds:
            return True
        self._seen[plate] = now
        return False


def parse_ocr_candidate(text: str, confidence: float, review_threshold: float = 85.0, bounding_box: list[float] | None = None) -> RecognitionResult:
    try:
        plate = normalize_plate(text)
    except ValueError:
        plate = None
    rto = decode_indian_plate(plate or text)
    return RecognitionResult(text, plate, confidence, plate is None or confidence < review_threshold, bounding_box, rto)


_INDIAN_PLATE = re.compile(r"^([A-Z]{2})([0-9OI]{1,2})([A-Z]{1,3})([0-9OI]{1,4})$")
_BH_SERIES = re.compile(r"^([0-9OI]{2})BH([0-9OI]{4})([A-Z]{1,2})$")
_DIGIT_LOOKALIKES = str.maketrans({"O": "0", "I": "1"})


def _indian_plate_from_ocr(text: str) -> str | None:
    """Apply position-aware OCR correction to a likely Indian registration."""
    compact = re.sub(r"[^A-Za-z0-9]", "", text).upper()
    match = _INDIAN_PLATE.fullmatch(compact)
    if match:
        state, district, series, number = match.groups()
        return f"{state}{district.translate(_DIGIT_LOOKALIKES)}{series}{number.translate(_DIGIT_LOOKALIKES)}"
    bh_match = _BH_SERIES.fullmatch(compact)
    if bh_match:
        year, number, series = bh_match.groups()
        return f"{year.translate(_DIGIT_LOOKALIKES)}BH{number.translate(_DIGIT_LOOKALIKES)}{series}"
    return None


def select_plate_candidate(candidates: list[tuple[object, str, float]], review_threshold: float = 85.0) -> RecognitionResult:
    """Join OCR fragments on one line and prefer a valid Indian plate candidate.

    EasyOCR commonly reports the state/district and the remaining plate text as
    separate boxes. The joined result is deliberately review-first because its
    confidence includes every fragment, including low-confidence characters.
    """
    if not candidates:
        return RecognitionResult("", None, 0.0, True)
    sources: list[tuple[str, float]] = [(text, confidence * 100) for _, text, confidence in candidates]
    lines: list[list[tuple[object, str, float]]] = []
    for candidate in candidates:
        box = candidate[0]
        center_y = sum(float(point[1]) for point in box) / len(box)
        height = max(float(point[1]) for point in box) - min(float(point[1]) for point in box)
        for line in lines:
            first_box = line[0][0]
            line_y = sum(float(point[1]) for point in first_box) / len(first_box)
            if abs(center_y - line_y) <= max(height, 18):
                line.append(candidate)
                break
        else:
            lines.append([candidate])
    for line in lines:
        if len(line) < 2:
            continue
        ordered = sorted(line, key=lambda item: min(float(point[0]) for point in item[0]))
        sources.append((" ".join(item[1] for item in ordered), sum(item[2] for item in ordered) * 100 / len(ordered)))
    all_boxes = [c[0] for c in candidates if hasattr(c[0], '__iter__')]
    b_box = None
    if all_boxes:
        try:
            min_x = min(float(pt[0]) for b in all_boxes for pt in b)
            min_y = min(float(pt[1]) for b in all_boxes for pt in b)
            max_x = max(float(pt[0]) for b in all_boxes for pt in b)
            max_y = max(float(pt[1]) for b in all_boxes for pt in b)
            b_box = [round(min_x, 1), round(min_y, 1), round(max_x - min_x, 1), round(max_y - min_y, 1)]
        except Exception:
            b_box = None

    indian = [(raw, confidence, _indian_plate_from_ocr(raw)) for raw, confidence in sources]
    indian = [candidate for candidate in indian if candidate[2]]
    if indian:
        raw, confidence, plate = max(indian, key=lambda candidate: candidate[1])
        rto = decode_indian_plate(plate or raw)
        return RecognitionResult(raw, plate, round(confidence, 2), confidence < review_threshold, b_box, rto)
    raw, confidence = max(sources, key=lambda candidate: candidate[1])
    return parse_ocr_candidate(raw, round(confidence, 2), review_threshold, b_box)


class EasyOcrRecognizer:
    """Loads heavy OCR libraries only when recognition is actually requested."""
    def __init__(self, review_threshold: float = 85.0) -> None:
        self.review_threshold = review_threshold
        self._reader = None

    def recognize_bytes(self, image_bytes: bytes) -> RecognitionResult:
        try:
            import cv2
            import easyocr
            import numpy as np
        except ImportError as error:
            raise RuntimeError("ANPR dependencies are unavailable. Install opencv-python, easyocr and numpy.") from error
        image = cv2.imdecode(np.frombuffer(image_bytes, np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("Uploaded image cannot be decoded.")
        # Disable EasyOCR's Unicode block-character progress bar. Windows
        # consoles using a legacy code page can otherwise raise a charmap error.
        self._reader = self._reader or easyocr.Reader(["en"], gpu=False, verbose=False)
        return select_plate_candidate(self._reader.readtext(image), self.review_threshold)
