"""
=========================================================================================
ocr.py — RapidOCR Offline Text & Handwritten Document Extraction Engine
=========================================================================================

Tech Stack:
 - RapidOCR / ONNX Runtime (High-speed CPU-optimized text detection & recognition)
 - Pillow (PIL) & NumPy (Image preprocessing and array manipulation)
 - PyMuPDF (`fitz` for rasterizing scanned multi-page PDF documents)
 - Regular Expressions (Colloquial abbreviation and noise normalization)

Key Architectural Responsibilities:
 1. 100% Offline Local Document Recognition:
    - Extracts text from scanned PDFs and images without sending image bytes to external cloud APIs.
    - Operates entirely within the on-premise security boundary.

 2. Spatial Bounding-Box Line Reconstruction:
    - Merges detected text fragments into coherent lines using vertical centroid clustering
      and horizontal coordinate sorting.

 3. Handwritten & Indian Slang Normalization:
    - Corrects handwritten informal abbreviations (e.g. "Adhaar No", "Aadhar", "ph no", "mob no")
      into standardized labels, guaranteeing high-confidence downstream PII detection.
    - Filters out non-Latin noise glyphs and cleans boundary artifacts.
=========================================================================================
"""

from __future__ import annotations

import io
import re
import threading
import time
from dataclasses import dataclass
from statistics import median
from typing import Any

import numpy as np

from app.core.logging import get_logger

logger = get_logger(__name__)

IMAGE_EXTENSIONS: frozenset[str] = frozenset(
    {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
)
MAX_OCR_PDF_PAGES: int = 10

_CJK_NOISE_RE = re.compile(r"^[\u3000-\u303f\u4e00-\u9fff\u25a0-\u25ff\s]+$")


class OcrExtractionError(ValueError):
    """Raised when local image/PDF OCR cannot parse or extract text."""


@dataclass(frozen=True)
class OcrLine:
    text: str
    confidence: float
    x_min: float
    y_center: float
    height: float


@dataclass(frozen=True)
class OcrExtractionResult:
    text: str
    line_count: int
    avg_confidence: float
    width: int
    height: int
    ocr_ms: float
    engine_name: str
    lines: list[OcrLine]


_OCR_LOCK = threading.Lock()
_OCR_ENGINE: Any | None = None
_OCR_ENGINE_MODE: str = "rapidocr"


def get_ocr_engine() -> Any:
    """Lazy-load and cache the local RapidOCR ONNX inference engine (100% offline at inference)."""
    global _OCR_ENGINE, _OCR_ENGINE_MODE
    if _OCR_ENGINE is not None:
        return _OCR_ENGINE
    with _OCR_LOCK:
        if _OCR_ENGINE is None:
            try:
                from rapidocr import RapidOCR

                _OCR_ENGINE = RapidOCR(params={"Global.use_cls": False})
                _OCR_ENGINE_MODE = "rapidocr-v3"
                logger.info("local_ocr_engine_initialized", engine="rapidocr")
            except ImportError:
                try:
                    from rapidocr_onnxruntime import RapidOCR as RapidOCROnnx

                    _OCR_ENGINE = RapidOCROnnx(use_cls=False)
                    _OCR_ENGINE_MODE = "rapidocr-onnxruntime"
                    logger.info("local_ocr_engine_initialized", engine="rapidocr_onnxruntime")
                except ImportError as exc:
                    raise OcrExtractionError(
                        "Local OCR engine (rapidocr) is not installed on the server."
                    ) from exc
    return _OCR_ENGINE


def _run_ocr_array(engine: Any, rgb_array: np.ndarray) -> list[tuple[Any, str, float]]:
    """Normalize output tuples across both `rapidocr` (v3+) and `rapidocr_onnxruntime` (v1)."""
    if _OCR_ENGINE_MODE == "rapidocr-v3":
        out = engine(rgb_array)
        boxes = getattr(out, "boxes", None)
        txts = getattr(out, "txts", None)
        scores = getattr(out, "scores", None)
        if not txts:
            return []
        normalized: list[tuple[Any, str, float]] = []
        for idx, txt in enumerate(txts):
            quad = boxes[idx] if boxes is not None and idx < len(boxes) else [[0, 0], [10, 0], [10, 10], [0, 10]]
            conf = float(scores[idx]) if scores is not None and idx < len(scores) else 0.0
            normalized.append((quad, str(txt), conf))
        return normalized

    raw_res, _ = engine(rgb_array)
    return list(raw_res or [])


def _to_rgb_with_white_bg(img: Any) -> Any:
    from PIL import Image, ImageOps

    transposed = ImageOps.exif_transpose(img)
    if transposed.mode in ("RGBA", "LA") or (
        transposed.mode == "P" and "transparency" in transposed.info
    ):
        rgba = transposed.convert("RGBA")
        canvas = Image.new("RGB", rgba.size, "white")
        canvas.paste(rgba, mask=rgba.split()[-1])
        return canvas
    if transposed.mode != "RGB":
        return transposed.convert("RGB")
    return transposed


def _prepare_image_for_ocr(img: Any) -> tuple[Any, int, int]:
    """Normalize orientation, color channels, edge padding, and scale for crisp PII OCR."""
    from PIL import Image, ImageOps

    rgb = _to_rgb_with_white_bg(img)
    orig_w, orig_h = rgb.size
    if orig_w <= 0 or orig_h <= 0:
        raise OcrExtractionError("Uploaded image has invalid zero dimensions.")

    max_side = max(orig_w, orig_h)
    if max_side < 1800:
        scale = min(2.2, 2000.0 / float(max_side))
        if scale > 1.05:
            rgb = rgb.resize(
                (max(1, int(round(orig_w * scale))), max(1, int(round(orig_h * scale)))),
                Image.Resampling.LANCZOS,
            )
    elif max_side > 2800:
        scale = 2800.0 / float(max_side)
        rgb = rgb.resize(
            (max(1, int(round(orig_w * scale))), max(1, int(round(orig_h * scale)))),
            Image.Resampling.LANCZOS,
        )

    padded = ImageOps.expand(rgb, border=24, fill="white")
    return padded, orig_w, orig_h


def _flatten_illumination_and_shadows(rgb_img: Any) -> np.ndarray:
    """Divide out uneven lighting/shadows on phone camera shots of paper/handwriting."""
    import cv2

    arr = np.array(rgb_img)
    gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)
    h, w = gray.shape
    k = max(31, (min(h, w) // 12) | 1)
    k = min(k, 121)
    bg = cv2.GaussianBlur(gray, (k, k), 0)
    flattened = np.clip(
        (gray.astype(np.float32) / np.maximum(bg.astype(np.float32), 1.0)) * 255.0,
        0,
        255,
    ).astype(np.uint8)
    return cv2.cvtColor(flattened, cv2.COLOR_GRAY2RGB)


def _has_uneven_lighting(rgb_img: Any) -> bool:
    """Detect non-uniform shadows / paper tint so digital screenshots skip extra blur work."""
    import cv2

    small = np.array(rgb_img.resize((160, 160)))
    gray = cv2.cvtColor(small, cv2.COLOR_RGB2GRAY)
    bg = cv2.GaussianBlur(gray, (31, 31), 0)
    p10, p95 = np.percentile(bg, [10, 95])
    # Natural camera photos of paper/notebooks show noticeable shading gradient (>18 intensity spread)
    return float(p95 - p10) > 18.0


def _enhance_contrast_for_retry(rgb_img: Any) -> np.ndarray:
    from PIL import ImageEnhance, ImageOps

    gray = ImageOps.grayscale(rgb_img)
    auto = ImageOps.autocontrast(gray, cutoff=1)
    boosted = ImageEnhance.Contrast(auto).enhance(1.5)
    sharpened = ImageEnhance.Sharpness(boosted).enhance(1.4)
    return np.array(sharpened.convert("RGB"))


def _clean_ocr_line(line: str) -> str:
    # Normalize full-width punctuation occasionally emitted by multilingual OCR checkpoints
    cleaned = (
        line.replace("：", ":")
        .replace("，", ",")
        .replace("；", ";")
        .replace("（", "(")
        .replace("）", ")")
        .replace("。", " ")
    )
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    # Recover missing space after field labels like 'Aadhaar:3456' or 'Phone No:+91'
    # without altering URLs ('https://') or numeric timestamps ('10:30').
    cleaned = re.sub(r"(?<=[A-Za-z]):(?!//)(?=[A-Za-z0-9+])", ": ", cleaned)
    return cleaned


def _reconstruct_reading_order(raw_results: list[tuple[Any, str, float]] | None) -> tuple[str, list[OcrLine], float]:
    if not raw_results:
        return "", [], 0.0

    parsed_boxes: list[tuple[float, float, float, float, str, float]] = []
    heights: list[float] = []

    for item in raw_results:
        if not item or len(item) < 3:
            continue
        quad, text, conf = item[0], str(item[1] or "").strip(), float(item[2] or 0.0)
        if not text:
            continue
        # Drop isolated non-Latin QR/texture false symbols (e.g., CJK glyph artifacts on barcodes)
        if _CJK_NOISE_RE.match(text):
            continue
        xs = [float(pt[0]) for pt in quad]
        ys = [float(pt[1]) for pt in quad]
        x_min = min(xs)
        x_max = max(xs)
        y_center = (min(ys) + max(ys)) / 2.0
        box_h = max(8.0, max(ys) - min(ys))
        heights.append(box_h)
        parsed_boxes.append((x_min, x_max, y_center, box_h, text, conf))

    if not parsed_boxes:
        return "", [], 0.0

    row_tolerance = max(10.0, median(heights) * 0.55)
    parsed_boxes.sort(key=lambda b: (b[2], b[0]))

    rows: list[list[tuple[float, float, float, float, str, float]]] = []
    for box in parsed_boxes:
        if not rows:
            rows.append([box])
            continue
        current_row = rows[-1]
        anchor_y = sum(b[2] for b in current_row) / len(current_row)
        if abs(box[2] - anchor_y) <= row_tolerance:
            current_row.append(box)
        else:
            rows.append([box])

    lines_out: list[OcrLine] = []
    confs: list[float] = []

    for row in rows:
        row.sort(key=lambda b: b[0])
        joined = _clean_ocr_line(" ".join(b[4] for b in row))
        if not joined:
            continue
        row_conf = sum(b[5] for b in row) / len(row)
        confs.append(row_conf)
        lines_out.append(
            OcrLine(
                text=joined,
                confidence=round(row_conf, 4),
                x_min=row[0][0],
                y_center=sum(b[2] for b in row) / len(row),
                height=max(b[3] for b in row),
            )
        )

    full_text = "\n".join(line.text for line in lines_out).strip()
    avg_conf = round(sum(confs) / len(confs), 4) if confs else 0.0
    return full_text, lines_out, avg_conf


def extract_text_from_pil_image(img: Any) -> OcrExtractionResult:
    started = time.perf_counter()
    prepared, orig_w, orig_h = _prepare_image_for_ocr(img)
    engine = get_ocr_engine()

    # For shadowy camera photos / handwritten pages, illumination flattening dramatically improves recall.
    if _has_uneven_lighting(prepared):
        primary_arr = _flatten_illumination_and_shadows(prepared)
        raw_res = _run_ocr_array(engine, primary_arr)
        text, lines, avg_conf = _reconstruct_reading_order(raw_res)
        # Compare against unflattened RGB if primary looks weak
        if avg_conf < 0.82 or sum(ch.isalnum() for ch in text) < 12:
            raw_plain = _run_ocr_array(engine, np.array(prepared))
            plain_text, plain_lines, plain_conf = _reconstruct_reading_order(raw_plain)
            if (len(plain_text) > len(text) and plain_conf >= avg_conf - 0.05) or plain_conf > avg_conf + 0.08:
                text, lines, avg_conf = plain_text, plain_lines, plain_conf
    else:
        raw_res = _run_ocr_array(engine, np.array(prepared))
        text, lines, avg_conf = _reconstruct_reading_order(raw_res)

    alnum_count = sum(ch.isalnum() for ch in text)
    if alnum_count < 8 or avg_conf < 0.72:
        retry_res = _run_ocr_array(engine, _enhance_contrast_for_retry(prepared))
        retry_text, retry_lines, retry_conf = _reconstruct_reading_order(retry_res)
        if sum(ch.isalnum() for ch in retry_text) > alnum_count or (
            retry_conf > avg_conf + 0.05 and len(retry_text) >= len(text) * 0.85
        ):
            text, lines, avg_conf = retry_text, retry_lines, retry_conf

    elapsed_ms = round((time.perf_counter() - started) * 1000.0, 2)
    return OcrExtractionResult(
        text=text,
        line_count=len(lines),
        avg_confidence=avg_conf,
        width=orig_w,
        height=orig_h,
        ocr_ms=elapsed_ms,
        engine_name="rapidocr-onnxruntime",
        lines=lines,
    )


def extract_text_from_image_bytes(raw_bytes: bytes) -> OcrExtractionResult:
    try:
        from PIL import Image, UnidentifiedImageError
    except ImportError as exc:
        raise OcrExtractionError(
            "Image processing library (Pillow) is not installed on the server."
        ) from exc

    try:
        with Image.open(io.BytesIO(raw_bytes)) as img:
            n_frames = getattr(img, "n_frames", 1)
            if n_frames > 1:
                frame_texts: list[str] = []
                total_lines = 0
                confs: list[float] = []
                total_ms = 0.0
                orig_w, orig_h = img.size
                all_lines: list[OcrLine] = []
                for idx in range(min(n_frames, MAX_OCR_PDF_PAGES)):
                    img.seek(idx)
                    res = extract_text_from_pil_image(img.copy())
                    total_ms += res.ocr_ms
                    if res.text:
                        frame_texts.append(f"--- Page {idx + 1} (OCR) ---\n{res.text}")
                        total_lines += res.line_count
                        confs.append(res.avg_confidence)
                        all_lines.extend(res.lines)
                joined = "\n\n".join(frame_texts).strip()
                if not joined:
                    raise OcrExtractionError(
                        "Local OCR could not detect readable text or PII characters in this image."
                    )
                return OcrExtractionResult(
                    text=joined,
                    line_count=total_lines,
                    avg_confidence=round(sum(confs) / len(confs), 4) if confs else 0.0,
                    width=orig_w,
                    height=orig_h,
                    ocr_ms=round(total_ms, 2),
                    engine_name="rapidocr-onnxruntime",
                    lines=all_lines,
                )

            result = extract_text_from_pil_image(img)
            if not result.text:
                raise OcrExtractionError(
                    "Local OCR could not detect readable text or PII characters in this image."
                )
            return result
    except OcrExtractionError:
        raise
    except UnidentifiedImageError as exc:
        raise OcrExtractionError("Uploaded image file could not be decoded or is corrupted.") from exc
    except Exception as exc:
        raise OcrExtractionError(f"Failed to run local OCR on image: {exc}") from exc


def extract_text_from_scanned_pdf(
    raw_bytes: bytes,
    max_pages: int = MAX_OCR_PDF_PAGES,
) -> tuple[str, int, float, int, float]:
    """Render image-only PDF pages locally via pypdfium2 and run RapidOCR page-by-page."""
    try:
        import pypdfium2 as pdfium
    except ImportError as exc:
        raise OcrExtractionError(
            "Scanned PDF rendering library (pypdfium2) is not installed on the server."
        ) from exc

    started = time.perf_counter()
    pdf = pdfium.PdfDocument(raw_bytes)
    total_pages = len(pdf)
    if total_pages == 0:
        raise OcrExtractionError("Uploaded PDF has zero pages.")

    page_texts: list[str] = []
    confs: list[float] = []
    total_lines = 0
    pages_to_scan = min(total_pages, max_pages)

    try:
        for idx in range(pages_to_scan):
            page = pdf[idx]
            try:
                bitmap = page.render(scale=200.0 / 72.0)
                pil_img = bitmap.to_pil()
                ocr_res = extract_text_from_pil_image(pil_img)
                if ocr_res.text:
                    page_texts.append(f"--- Page {idx + 1} (OCR) ---\n{ocr_res.text}")
                    confs.append(ocr_res.avg_confidence)
                    total_lines += ocr_res.line_count
            finally:
                page.close()
    finally:
        pdf.close()

    joined = "\n\n".join(page_texts).strip()
    if not joined:
        raise OcrExtractionError(
            "No readable text found in scanned PDF pages even after local OCR."
        )
    elapsed_ms = round((time.perf_counter() - started) * 1000.0, 2)
    avg_conf = round(sum(confs) / len(confs), 4) if confs else 0.0
    return joined, total_pages, avg_conf, total_lines, elapsed_ms
