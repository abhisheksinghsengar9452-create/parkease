"""OpenCV/EasyOCR adapter with safe, review-first recognition behavior and Indian RTO heuristics."""
from __future__ import annotations
from dataclasses import dataclass
import re
from time import monotonic
from services.plates import normalize_plate
from services.rto_decoder import decode_indian_plate, STATE_NAMES


STICKER_WORDS = {
    "CNG", "LPG", "PETROL", "DIESEL", "ELECTRIC", "EV", "HYBRID", "HSRP",
    "INDIA", "IND", "POLICE", "ARMY", "NAVY", "GOVT", "PRESS", "ADVOCATE",
    "MARUTI", "SUZUKI", "HYUNDAI", "TATA", "HONDA", "MAHINDRA", "TOYOTA",
    "FORD", "CHEVROLET", "RENAULT", "NISSAN", "VOLKSWAGEN", "SKODA", "KIA",
    "MG", "BMW", "MERCEDES", "AUDI", "HERO", "BAJAJ", "TVS", "ROYAL", "ENFIELD"
}

DIGIT_LOOKALIKES = str.maketrans({"O": "0", "I": "1", "Q": "0", "B": "8", "S": "5", "Z": "2"})
VALID_STATES = set(STATE_NAMES.keys()) - {"BH"}

INDIAN_PLATE_PATTERN = re.compile(
    r"(?:^|[^A-Z0-9])"
    r"([A-Z]{2})"                 # State code
    r"[\s\-_.]*"
    r"([0-9OIBSZ]{1,2})"          # District code
    r"[\s\-_.]*"
    r"([A-Z]{1,3})"               # Series letters
    r"[\s\-_.]*"
    r"([0-9OIBSZ]{1,4})"          # Registration number
    r"(?:$|[^A-Z0-9])"
)

BH_PATTERN = re.compile(
    r"(?:^|[^A-Z0-9])"
    r"([0-9OIBSZ]{2})"            # Year
    r"[\s\-_.]*BH[\s\-_.]*"       # BH series
    r"([0-9OIBSZ]{4})"            # 4 digit number
    r"[\s\-_.]*"
    r"([A-Z]{1,2})"               # Series
    r"(?:$|[^A-Z0-9])"
)


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


def _clean_ocr_text(text: str) -> str:
    """Strip leading HSRP IND and special characters."""
    clean = text.upper().strip()
    if clean.startswith("INDIA"):
        clean = clean[5:].strip()
    elif clean.startswith("IND") and len(clean) >= 9:
        clean = clean[3:].strip()
    return clean


def _extract_indian_plate_from_text(text: str) -> str | None:
    """Robust extraction of Indian standard or BH series plate from arbitrary OCR text."""
    clean = _clean_ocr_text(text)

    # 1. Check Bharat Series (e.g. 22BH1234AA)
    m_bh = BH_PATTERN.search(clean)
    if m_bh:
        yr, num, ser = m_bh.groups()
        yr_clean = yr.translate(DIGIT_LOOKALIKES)
        num_clean = num.translate(DIGIT_LOOKALIKES)
        if yr_clean.isdigit() and num_clean.isdigit():
            return f"{yr_clean}BH{num_clean}{ser}"

    # 2. Check Standard State series
    for match in INDIAN_PLATE_PATTERN.finditer(clean):
        st, dist, ser, num = match.groups()
        if st in VALID_STATES:
            d_clean = dist.translate(DIGIT_LOOKALIKES)
            n_clean = num.translate(DIGIT_LOOKALIKES)
            if d_clean.isdigit() and n_clean.isdigit():
                return f"{st}{d_clean}{ser}{n_clean}"

    # 3. Fallback position-aware lookalike on compact string
    compact = re.sub(r"[^A-Za-z0-9]", "", clean).upper()
    if len(compact) >= 7 and compact[:2] in VALID_STATES:
        st = compact[:2]
        rest = compact[2:]
        m_rest = re.match(r"^([0-9OIBSZ]{1,2})([A-Z]{1,3})([0-9OIBSZ]{1,4})$", rest)
        if m_rest:
            d, s, n = m_rest.groups()
            d_clean = d.translate(DIGIT_LOOKALIKES)
            n_clean = n.translate(DIGIT_LOOKALIKES)
            if d_clean.isdigit() and n_clean.isdigit():
                return f"{st}{d_clean}{s}{n_clean}"

    return None


def select_plate_candidate(candidates: list[tuple[object, str, float]], review_threshold: float = 85.0) -> RecognitionResult:
    """Join OCR fragments, reject sticker noise, and prefer valid Indian plates."""
    if not candidates:
        return RecognitionResult("", None, 0.0, True)

    sources: list[tuple[str, float, list[object]]] = []
    for box, text, confidence in candidates:
        sources.append((text.strip(), confidence * 100, [box]))

    # 1. Group horizontally adjacent fragments (same text line)
    lines: list[list[tuple[object, str, float]]] = []
    for candidate in candidates:
        box = candidate[0]
        try:
            center_y = sum(float(point[1]) for point in box) / len(box)
            height = max(float(point[1]) for point in box) - min(float(point[1]) for point in box)
        except Exception:
            center_y, height = 0.0, 20.0
        for line in lines:
            first_box = line[0][0]
            try:
                line_y = sum(float(point[1]) for point in first_box) / len(first_box)
            except Exception:
                line_y = 0.0
            if abs(center_y - line_y) <= max(height, 22):
                line.append(candidate)
                break
        else:
            lines.append([candidate])

    for line in lines:
        if len(line) < 2:
            continue
        try:
            ordered = sorted(line, key=lambda item: min(float(point[0]) for point in item[0]))
        except Exception:
            ordered = line
        line_text = " ".join(item[1] for item in ordered)
        line_conf = sum(item[2] for item in ordered) * 100 / len(ordered)
        line_boxes = [item[0] for item in ordered]
        sources.append((line_text, line_conf, line_boxes))

    # 2. Check 2-line plates (vertically adjacent boxes)
    if len(lines) >= 2:
        for i in range(len(lines)):
            for j in range(i + 1, len(lines)):
                l1_text = " ".join(item[1] for item in lines[i])
                l2_text = " ".join(item[1] for item in lines[j])
                combined_text = f"{l1_text} {l2_text}"
                combined_conf = (
                    sum(item[2] for item in lines[i]) + sum(item[2] for item in lines[j])
                ) * 100 / (len(lines[i]) + len(lines[j]))
                combined_boxes = [item[0] for item in lines[i]] + [item[0] for item in lines[j]]
                sources.append((combined_text, combined_conf, combined_boxes))

    # 3. Also check global concatenated non-sticker text
    non_sticker_items = [c for c in candidates if c[1].strip().upper() not in STICKER_WORDS]
    if len(non_sticker_items) >= 2:
        all_text = " ".join(item[1] for item in non_sticker_items)
        all_conf = sum(item[2] for item in non_sticker_items) * 100 / len(non_sticker_items)
        all_boxes = [item[0] for item in non_sticker_items]
        sources.append((all_text, all_conf, all_boxes))

    # Evaluate each source for Indian plate patterns
    indian_matches: list[tuple[str, float, str, list[object]]] = []
    for raw, confidence, boxes in sources:
        plate = _extract_indian_plate_from_text(raw)
        if plate:
            indian_matches.append((raw, confidence, plate, boxes))

    if indian_matches:
        # Pick the valid Indian plate with the highest confidence
        raw, confidence, plate, matched_boxes = max(indian_matches, key=lambda item: item[1])
        b_box = None
        if matched_boxes:
            try:
                all_pts = [pt for b in matched_boxes if hasattr(b, '__iter__') for pt in b]
                if all_pts:
                    min_x = min(float(pt[0]) for pt in all_pts)
                    min_y = min(float(pt[1]) for pt in all_pts)
                    max_x = max(float(pt[0]) for pt in all_pts)
                    max_y = max(float(pt[1]) for pt in all_pts)
                    b_box = [round(min_x, 1), round(min_y, 1), round(max_x - min_x, 1), round(max_y - min_y, 1)]
            except Exception:
                b_box = None
        rto = decode_indian_plate(plate)
        return RecognitionResult(
            raw_text=raw,
            normalized_plate=plate,
            confidence=round(confidence, 2),
            requires_review=(confidence < review_threshold),
            bounding_box=b_box,
            rto_info=rto
        )

    # If no valid Indian plate matched, filter out pure sticker words from being chosen
    non_stickers = [s for s in sources if s[0].upper() not in STICKER_WORDS and len(re.sub(r'[^A-Za-z0-9]', '', s[0])) >= 4]
    if non_stickers:
        raw, confidence, boxes = max(non_stickers, key=lambda item: item[1])
        return parse_ocr_candidate(raw, round(confidence, 2), review_threshold)

    # If only stickers were found (e.g. CNG), report clearly that only sticker was detected
    raw, confidence, _ = max(sources, key=lambda item: item[1])
    return RecognitionResult(
        raw_text=f"{raw} (Vehicle Sticker detected - Plate not visible)",
        normalized_plate=None,
        confidence=round(confidence, 2),
        requires_review=True,
        bounding_box=None,
        rto_info=None
    )


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

        self._reader = self._reader or easyocr.Reader(["en"], gpu=False, verbose=False)

        # Pass 1: Original Image
        raw_candidates = self._reader.readtext(image)
        result = select_plate_candidate(raw_candidates, self.review_threshold)

        # Pass 2: If no valid plate detected in Pass 1, apply CLAHE contrast enhancement
        if not result.normalized_plate:
            try:
                gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
                clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
                enhanced = clahe.apply(gray)
                enhanced_candidates = self._reader.readtext(enhanced)
                all_candidates = raw_candidates + enhanced_candidates
                enhanced_result = select_plate_candidate(all_candidates, self.review_threshold)
                if enhanced_result.normalized_plate:
                    return enhanced_result
            except Exception:
                pass

        return result
