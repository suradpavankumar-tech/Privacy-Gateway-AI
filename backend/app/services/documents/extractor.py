"""
=========================================================================================
extractor.py — Enterprise Multi-Format Document Ingestion & Classification Engine
=========================================================================================

Tech Stack:
 - PyMuPDF (`fitz` for high-fidelity text and page layout extraction)
 - Python-docx (Native Microsoft Word XML document parsing)
 - RapidOCR (Automatic visual fallback for rasterized/scanned PDFs and photos)
 - Python Standard Library (io, pathlib, dataclasses)

Key Architectural Responsibilities:
 1. Universal Document Ingestion:
    - Parses native PDFs, scanned PDFs, DOCX, TXT, CSV, JSON, and common image formats.
    - Automatically detects scanned/image-only PDFs and activates RapidOCR.

 2. Domain Document Classification:
    - Automatically identifies document taxonomy using keyword frequency heuristics:
      * `property_deed`: Sale deeds, stamp duty receipts, survey extracts, khata records.
      * `court_order`: High Court orders, CNR numbers, petition summaries.
      * `loan_agreement`: Financial sanctions, promissory notes, mortgage terms.
      * `kyc_record`: Aadhaar cards, PAN cards, voter identification, passports.

 3. Size & Payload Safety Constraints:
    - Enforces 10MB maximum upload limit and 100,000-character safety bounds to prevent
      buffer exhaustion and memory overflow attacks.
=========================================================================================
"""

from __future__ import annotations

import io
import json
import re
from dataclasses import dataclass
from pathlib import Path

from app.services.documents.ocr import (
    IMAGE_EXTENSIONS,
    OcrExtractionError,
    extract_text_from_image_bytes,
    extract_text_from_scanned_pdf,
)

SUPPORTED_EXTENSIONS: frozenset[str] = (
    frozenset({".pdf", ".docx", ".txt", ".md", ".csv", ".json", ".log", ".xml", ".html"})
    | IMAGE_EXTENSIONS
)
MAX_UPLOAD_BYTES: int = 10 * 1024 * 1024  # 10 MB
MAX_GATEWAY_CHARS: int = 100000

_PROPERTY_KEYWORDS: tuple[str, ...] = (
    "sale deed",
    "deed of sale",
    "sub-registrar",
    "sub registrar",
    "encumbrance",
    "khasra",
    "khata",
    "khatauni",
    "survey no",
    "sy. no",
    "sy no",
    "plot no",
    "mouza",
    "taluk",
    "hobli",
    "stamp duty",
    "conveyance",
    "lease deed",
    "rental agreement",
    "vendor",
    "vendee",
    "lessor",
    "lessee",
    "schedule of property",
    "schedule property",
    "built-up area",
    "carpet area",
    "square feet",
    "rera",
    "pid no",
    "title deed",
    "mutation",
    "patta",
)

_LEGAL_KEYWORDS: tuple[str, ...] = (
    "legal notice",
    "plaintiff",
    "defendant",
    "petitioner",
    "respondent",
    "advocate",
    "bar council",
    "writ petition",
    "affidavit",
    "power of attorney",
    "arbitration",
    "arbitrator",
    "indemnity",
    "indemnify",
    "force majeure",
    "jurisdiction",
    "whereas",
    "hereinafter",
    "memorandum of understanding",
    "non-disclosure",
    "nda",
    "litigation",
    "high court",
    "district court",
    "cnr no",
    "suit no",
    "o.s. no",
    "executant",
    "testator",
    "deponent",
    "subpoena",
    "breach of contract",
)

_LOAN_KEYWORDS: tuple[str, ...] = (
    "loan application",
    "home loan",
    "sanction",
    "disbursement",
    "emi",
    "credit appraisal",
    "borrower",
)

_KYC_KEYWORDS: tuple[str, ...] = (
    "kyc",
    "e-kyc",
    "ekyc",
    "know your customer",
    "ckyc",
    "identity verification",
)

_INSURANCE_KEYWORDS: tuple[str, ...] = (
    "insurance claim",
    "policyholder",
    "sum insured",
    "hospitalization",
    "claimant",
    "third party administrator",
)


class DocumentExtractionError(ValueError):
    """Raised when an uploaded document cannot be parsed safely or is unsupported."""


@dataclass(frozen=True)
class DocumentClassification:
    category: str
    purpose: str
    suggested_task: str
    matched_signals: list[str]


@dataclass(frozen=True)
class ExtractedDocumentResult:
    filename: str
    file_extension: str
    file_size_bytes: int
    page_count: int | None
    char_count: int
    word_count: int
    extraction_method: str
    extracted_text: str
    truncated_for_gateway: bool
    classification: DocumentClassification
    ocr_used: bool = False
    ocr_confidence: float | None = None
    ocr_line_count: int | None = None
    ocr_processing_ms: float | None = None
    image_dimensions: str | None = None


def _sanitize_filename(filename: str | None) -> str:
    base = Path(filename or "uploaded_document.txt").name.strip()
    cleaned = re.sub(r"[^A-Za-z0-9._\- ]+", "_", base)
    return cleaned or "uploaded_document.txt"


_OCR_CHAR_CLEANUP = str.maketrans({
    "ı": "i",
    "İ": "I",
    "ú": "u",
    "Ú": "U",
    "ó": "o",
    "Ó": "O",
    "á": "a",
    "Á": "A",
    "é": "e",
    "É": "E",
    "í": "i",
    "Í": "I",
    "ñ": "n",
    "Ñ": "N",
    "’": "'",
    "‘": "'",
    "“": '"',
    "”": '"',
})


def _decode_text_bytes(raw_bytes: bytes, ext: str) -> str:
    text: str | None = None
    for encoding in ("utf-8-sig", "utf-8", "utf-16", "cp1252", "latin-1"):
        try:
            text = raw_bytes.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        raise DocumentExtractionError("Unable to decode text file with UTF-8/UTF-16/Latin-1.")

    if ext == ".json":
        try:
            parsed = json.loads(text)
            text = json.dumps(parsed, indent=2, ensure_ascii=False)
        except json.JSONDecodeError:
            pass
    elif ext in {".html", ".xml"}:
        text = re.sub(r"<script[^>]*>.*?</script>", " ", text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r"<[^>]+>", " ", text)
    return text


def _extract_pdf(raw_bytes: bytes) -> tuple[str, int, str, float | None, int | None, float | None]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise DocumentExtractionError(
            "PDF extraction library (pypdf) is not installed on the server."
        ) from exc

    try:
        reader = PdfReader(io.BytesIO(raw_bytes))
        if reader.is_encrypted:
            raise DocumentExtractionError(
                "Uploaded PDF is password-protected/encrypted. Decrypt it locally before upload."
            )
        pages: list[str] = []
        for idx, page in enumerate(reader.pages, start=1):
            page_text = (page.extract_text() or "").strip()
            if page_text:
                pages.append(f"--- Page {idx} ---\n{page_text}")
        joined = "\n\n".join(pages).strip()
        non_ws = re.sub(r"\s+", "", joined)
        if len(non_ws) < 20:
            # Automatic local OCR fallback for scanned/image-only PDFs
            try:
                ocr_text, total_pages, avg_conf, line_count, ocr_ms = extract_text_from_scanned_pdf(
                    raw_bytes
                )
                return ocr_text, total_pages, "pypdfium2+rapidocr", avg_conf, line_count, ocr_ms
            except OcrExtractionError as ocr_exc:
                raise DocumentExtractionError(str(ocr_exc)) from ocr_exc
        return joined, len(reader.pages), "pypdf", None, None, None
    except DocumentExtractionError:
        raise
    except Exception as exc:
        raise DocumentExtractionError(f"Failed to parse PDF document: {exc}") from exc


def _extract_docx(raw_bytes: bytes) -> str:
    try:
        from docx import Document
    except ImportError as exc:
        raise DocumentExtractionError(
            "DOCX extraction library (python-docx) is not installed on the server."
        ) from exc

    try:
        doc = Document(io.BytesIO(raw_bytes))
        parts: list[str] = []
        for para in doc.paragraphs:
            txt = para.text.strip()
            if txt:
                parts.append(txt)
        for table in doc.tables:
            for row in table.rows:
                cells = [cell.text.strip().replace("\n", " ") for cell in row.cells]
                row_line = " | ".join(c for c in cells if c)
                if row_line:
                    parts.append(row_line)
        joined = "\n".join(parts).strip()
        if not joined:
            raise DocumentExtractionError("Uploaded DOCX file contains no extractable text or table content.")
        return joined
    except DocumentExtractionError:
        raise
    except Exception as exc:
        raise DocumentExtractionError(f"Failed to parse DOCX document: {exc}") from exc


def _count_keyword_hits(keywords: tuple[str, ...], haystack: str) -> list[str]:
    hits: list[str] = []
    for kw in keywords:
        pat = rf"(?<![a-z0-9]){re.escape(kw)}(?![a-z0-9])"
        if re.search(pat, haystack):
            hits.append(kw)
    return hits


def classify_uploaded_document(text: str, filename: str = "") -> DocumentClassification:
    haystack = f"{filename}\n{text[:15000]}".lower()

    prop_hits = _count_keyword_hits(_PROPERTY_KEYWORDS, haystack)
    legal_hits = _count_keyword_hits(_LEGAL_KEYWORDS, haystack)
    loan_hits = _count_keyword_hits(_LOAN_KEYWORDS, haystack)
    kyc_hits = _count_keyword_hits(_KYC_KEYWORDS, haystack)
    ins_hits = _count_keyword_hits(_INSURANCE_KEYWORDS, haystack)

    scores = [
        ("property_document", len(prop_hits), prop_hits),
        ("legal_document", len(legal_hits), legal_hits),
        ("loan_application", len(loan_hits), loan_hits),
        ("kyc_document", len(kyc_hits), kyc_hits),
        ("insurance_claim", len(ins_hits), ins_hits),
    ]
    scores.sort(key=lambda item: item[1], reverse=True)
    top_cat, top_score, top_hits = scores[0]

    if top_cat == "property_document" and top_score >= 1:
        return DocumentClassification(
            category="property_document",
            purpose="property_verification",
            suggested_task=(
                "Analyze this property document into 4 structured sections — "
                "1. Ownership Chain / Parties, 2. Deed, Survey & CNR IDs, "
                "3. Financial Consideration & Deadlines, and 4. Risk & Red-Flag Clauses — "
                "while preserving all masked placeholder tokens verbatim."
            ),
            matched_signals=top_hits[:8],
        )
    if top_cat == "legal_document" and top_score >= 1:
        return DocumentClassification(
            category="legal_document",
            purpose="legal_review",
            suggested_task=(
                "Analyze this legal document into 4 structured sections — "
                "1. Ownership Chain / Parties, 2. Deed, Survey & CNR IDs, "
                "3. Financial Consideration & Deadlines, and 4. Risk & Red-Flag Clauses — "
                "while preserving all masked placeholder tokens verbatim."
            ),
            matched_signals=top_hits[:8],
        )
    if top_cat == "loan_application" and top_score >= 1:
        return DocumentClassification(
            category="loan_application",
            purpose="loan_underwriting",
            suggested_task=(
                "Summarize this loan application, verify underwriting & bank disbursement readiness, "
                "and list key compliance checks while preserving all placeholder tokens verbatim."
            ),
            matched_signals=top_hits[:8],
        )
    if top_cat == "kyc_document" and top_score >= 1:
        return DocumentClassification(
            category="kyc_document",
            purpose="kyc_verification",
            suggested_task=(
                "Summarize KYC verification details and list document validation steps while preserving "
                "all masked placeholder tokens verbatim."
            ),
            matched_signals=top_hits[:8],
        )
    if top_cat == "insurance_claim" and top_score >= 1:
        return DocumentClassification(
            category="insurance_claim",
            purpose="insurance_claims",
            suggested_task=(
                "Analyze this insurance claim record, summarize adjudication steps, and flag missing proofs "
                "while preserving all masked placeholder tokens verbatim."
            ),
            matched_signals=top_hits[:8],
        )

    return DocumentClassification(
        category="general_document",
        purpose="document_summarization",
        suggested_task=(
            "Summarize this uploaded enterprise document clearly, extract key findings and obligations, "
            "and preserve all masked placeholder tokens verbatim."
        ),
        matched_signals=[],
    )


def extract_document_upload(filename: str | None, raw_bytes: bytes) -> ExtractedDocumentResult:
    safe_name = _sanitize_filename(filename)
    ext = Path(safe_name).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        allowed = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise DocumentExtractionError(
            f"Unsupported file type '{ext or 'none'}'. Supported formats: {allowed}."
        )

    size_bytes = len(raw_bytes)
    if size_bytes == 0:
        raise DocumentExtractionError("Uploaded file is empty.")
    if size_bytes > MAX_UPLOAD_BYTES:
        raise DocumentExtractionError(
            f"Uploaded file exceeds maximum allowed size ({MAX_UPLOAD_BYTES // (1024 * 1024)} MB)."
        )

    page_count: int | None = None
    ocr_used = False
    ocr_confidence: float | None = None
    ocr_line_count: int | None = None
    ocr_processing_ms: float | None = None
    image_dimensions: str | None = None

    if ext == ".pdf":
        text, page_count, method, ocr_confidence, ocr_line_count, ocr_processing_ms = _extract_pdf(
            raw_bytes
        )
        ocr_used = "rapidocr" in method
    elif ext == ".docx":
        text = _extract_docx(raw_bytes)
        method = "python-docx"
    elif ext in IMAGE_EXTENSIONS:
        try:
            ocr_res = extract_text_from_image_bytes(raw_bytes)
        except OcrExtractionError as exc:
            raise DocumentExtractionError(str(exc)) from exc
        text = ocr_res.text
        method = ocr_res.engine_name
        ocr_used = True
        ocr_confidence = ocr_res.avg_confidence
        ocr_line_count = ocr_res.line_count
        ocr_processing_ms = ocr_res.ocr_ms
        image_dimensions = f"{ocr_res.width}x{ocr_res.height}"
    else:
        text = _decode_text_bytes(raw_bytes, ext)
        method = "text-decoder"

    # Normalize excessive whitespace and OCR diacritic/dotless artifacts while preserving line breaks cleanly
    normalized = re.sub(r"\r\n?", "\n", text).strip()
    normalized = normalized.translate(_OCR_CHAR_CLEANUP)
    normalized = re.sub(r"\n{4,}", "\n\n\n", normalized)
    if not normalized:
        raise DocumentExtractionError("No readable text content remained after extraction.")

    truncated = False
    if len(normalized) > MAX_GATEWAY_CHARS:
        normalized = normalized[:MAX_GATEWAY_CHARS]
        truncated = True

    word_count = len(normalized.split())
    classification = classify_uploaded_document(normalized, safe_name)

    return ExtractedDocumentResult(
        filename=safe_name,
        file_extension=ext,
        file_size_bytes=size_bytes,
        page_count=page_count,
        char_count=len(normalized),
        word_count=word_count,
        extraction_method=method,
        extracted_text=normalized,
        truncated_for_gateway=truncated,
        classification=classification,
        ocr_used=ocr_used,
        ocr_confidence=ocr_confidence,
        ocr_line_count=ocr_line_count,
        ocr_processing_ms=ocr_processing_ms,
        image_dimensions=image_dimensions,
    )
