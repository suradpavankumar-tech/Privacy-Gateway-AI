"""
=========================================================================================
engine.py — Hybrid Indic NER & Presidio PII Detection Engine
=========================================================================================

Tech Stack:
 - Microsoft Presidio Analyzer (Enterprise entity analysis framework)
 - Spacy NLP (`en_core_web_sm` contextual statistical tokenization)
 - Custom Indian Recognizers (Aadhaar, PAN, GSTIN, Voter ID, Indian Address, IFSC)
 - Python Standard Library (dataclasses, re, time)

Key Architectural Responsibilities:
 1. High-Accuracy Multi-Layered PII Detection:
    - Identifies Mandatory Indian PII (Aadhaar, PAN, GSTIN, Voter ID, Passport, Address, Person)
      and Extended PII (Phone, Email, Bank Account, IFSC, UPI ID, Credit Card).

 2. Hybrid Detection Pipeline:
    - Combines contextual linguistic NER (Spacy) with deterministic pattern matching
      and mathematical checksum validators (Verhoeff, Modulo-11, Luhn).

 3. Overlapping Span Conflict Resolution:
    - Resolves competing entity detections by favoring higher confidence, longer character
      spans, and mandatory category tiers.
=========================================================================================
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass
from typing import Iterable

from presidio_analyzer import AnalyzerEngine, RecognizerRegistry, RecognizerResult
from presidio_analyzer.nlp_engine import NlpEngineProvider
from presidio_analyzer.predefined_recognizers import (
    CreditCardRecognizer,
    EmailRecognizer,
    SpacyRecognizer,
)

from app.core.config import get_settings
from app.core.logging import get_logger
from app.schemas.gateway import CategoryTier
from app.services.detection.indian_recognizers import (
    IndiaAadhaarRecognizer,
    IndiaAddressRecognizer,
    IndiaGstinRecognizer,
    IndiaPanRecognizer,
    IndiaPassportRecognizer,
    IndiaPersonContextRecognizer,
    IndiaVoterIdRecognizer,
    build_extended_indian_recognizers,
)
from app.services.detection.indian_validators import normalize_digits, validate_luhn

logger = get_logger(__name__)

MANDATORY_ENTITIES: frozenset[str] = frozenset(
    {
        "PERSON",
        "AADHAAR",
        "PAN",
        "GSTIN",
        "VOTER_ID",
        "PASSPORT",
        "ADDRESS",
    }
)

EXTENDED_ENTITIES: frozenset[str] = frozenset(
    {
        "PHONE_NUMBER",
        "EMAIL_ADDRESS",
        "BANK_ACCOUNT",
        "IFSC",
        "DATE_OF_BIRTH",
        "CREDIT_CARD",
        "CUSTOMER_ID",
        "UPI_ID",
        "PROPERTY_LEGAL_ID",
    }
)

ALL_SUPPORTED_ENTITIES: list[str] = sorted(MANDATORY_ENTITIES | EXTENDED_ENTITIES)

_ENTITY_PRIORITY: dict[str, int] = {
    "GSTIN": 100,
    "BANK_ACCOUNT": 96,
    "AADHAAR": 95,
    "PAN": 90,
    "PASSPORT": 85,
    "VOTER_ID": 85,
    "CREDIT_CARD": 82,
    "IFSC": 78,
    "UPI_ID": 78,
    "EMAIL_ADDRESS": 75,
    "PHONE_NUMBER": 72,
    "ADDRESS": 70,
    "PERSON": 68,
    "DATE_OF_BIRTH": 65,
    "PROPERTY_LEGAL_ID": 62,
    "CUSTOMER_ID": 60,
}

_PERSON_FALSE_POSITIVES = frozenset(
    {
        "aadhaar", "aadhar", "pan", "gstin", "gst", "ifsc", "upi", "kyc", "ekyc",
        "voter", "passport", "loan", "claim", "claimant", "policy", "branch", "account",
        "holder", "applicant", "customer", "amount", "name", "number", "address",
        "savings", "current", "neft", "rtgs", "imps", "dob", "pin", "pincode",
        "india", "bengaluru", "bangalore", "mumbai", "delhi", "chennai",
        "hyderabad", "kolkata", "pune", "ahmedabad", "jaipur", "lucknow", "davangere",
        "karnataka", "maharashtra", "tamil nadu", "telangana", "gujarat",
        "hdfc", "icici", "sbi", "axis", "kotak", "bajaj", "lic", "uidai", "nsdl",
        "rupees", "inr", "rs", "emi", "approved", "rejected", "pending",
        "enclave", "apartments", "residency", "gardens", "colony", "niketan", "vihar",
        "sector", "road", "main", "cross", "stage", "extension", "mera", "ignore", "karein",
        "deed", "sale", "lease", "agreement", "contract", "notice", "legal",
        "property", "schedule", "district", "state", "court", "tribunal",
        "registrar", "authority", "authorities", "corporation", "clause", "section",
        "stamp", "duty", "witness", "party", "parties", "execution", "registration",
        "maidan", "chowk", "taluka", "tal", "haveli", "balance", "land", "said",
        "project", "building", "buildings", "loft", "carpet", "area", "parks", "park",
        "car", "it", "government", "semi", "local", "msdc", "ginger", "royale",
        "developers", "developer", "promoter", "promoters", "owner", "owners",
        "purchaser", "purchasers", "vendor", "vendee", "unit", "units", "dummy",
        "document", "page", "note", "table", "annexure", "appendix", "first", "second",
        "part", "partner", "authorized", "partnership", "act", "office", "camp",
        "shop", "flat", "floor", "wing", "guntha", "gunthas", "sq", "mts", "fts", "mt",
        "enterprise", "privacy", "gateway", "problem", "statement", "summary", "overview",
        "architecture", "pipeline", "security", "gate", "vault", "token", "placeholder",
        "indian", "dpdp", "compliance", "evaluation", "benchmark", "matrix", "llm", "slm",
        "api", "json", "pdf", "docx", "synthetic", "dataset", "restoration", "audit",
        "ner", "model", "models", "small", "language", "large", "genai", "domain", "title",
        "duration", "event", "dates", "overview", "hackathon", "system", "prompt", "provider",
        "adapter", "engine", "module", "schema", "framework", "latency", "accuracy",
        "precision", "recall", "presidio", "spacy", "gliner",
        "plaintiff", "defendant", "defendants", "petitioner", "respondent", "applicant",
        "appellant", "accused", "advocate", "counsel", "coolie", "agriculturist",
        "farmer", "aged", "years", "year", "sio", "dio", "wio", "cio", "sri", "shri",
        "smt", "mr", "mrs", "miss", "apmc",
    }
)

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

_PINCODE_RE = re.compile(r"\b[1-9][0-9]{2}\s?[0-9]{3}\b")
_STREET_HINT_RE = re.compile(
    r"\b(?:flat|house|plot|door|no\.?|road|rd|street|st|lane|cross|main|sector|phase|block|nagar|nagara|colony|vihar|layout|enclave|puram|marg|chowk|village|gram|grama|post|hobli|taluk|taluka|tq|tehsil|mandal|district|dist|extension|extn?\.?|badavane|temple|front|behind|beside|circle|city|town)\b",
    re.IGNORECASE,
)


class DetectionEngineError(RuntimeError):
    """Raised when local PII detection cannot execute safely (fail-closed)."""


@dataclass(frozen=True)
class DetectionItem:
    entity_type: str
    category_tier: CategoryTier
    start: int
    end: int
    confidence: float
    recognizer: str
    matched_text: str
    normalized_value: str


def normalize_entity_value(entity_type: str, value: str) -> str:
    cleaned = value.strip()
    if entity_type in {"AADHAAR", "PHONE_NUMBER", "CREDIT_CARD", "BANK_ACCOUNT"}:
        digits = normalize_digits(cleaned)
        if entity_type == "PHONE_NUMBER" and len(digits) > 10 and digits.startswith("91"):
            return digits[-10:]
        if entity_type == "PHONE_NUMBER" and len(digits) == 11 and digits.startswith("0"):
            return digits[1:]
        return digits
    if entity_type in {"PAN", "GSTIN", "VOTER_ID", "PASSPORT", "IFSC", "CUSTOMER_ID"}:
        return cleaned.upper()
    if entity_type in {"EMAIL_ADDRESS", "UPI_ID"}:
        return cleaned.lower()
    if entity_type == "PERSON":
        return re.sub(r"\s+", " ", cleaned).lower()
    if entity_type == "ADDRESS":
        return re.sub(r"[\s,]+", " ", cleaned).strip().lower()
    return cleaned


class DetectionIntelligenceEngine:
    """Engine 1: Local Presidio + Indian Validators + Local NER (spaCy / optional GLiNER)."""

    VERSION = "2.0.0"

    def __init__(self) -> None:
        settings = get_settings()
        self._initialized = False
        self._analyzer: AnalyzerEngine | None = None
        self._gliner_enabled = settings.ENABLE_GLINER
        self._spacy_model = settings.SPACY_MODEL

    def initialize(self) -> None:
        if self._initialized:
            return
        try:
            nlp_config = {
                "nlp_engine_name": "spacy",
                "models": [{"lang_code": "en", "model_name": self._spacy_model}],
            }
            nlp_engine = NlpEngineProvider(nlp_configuration=nlp_config).create_engine()

            registry = RecognizerRegistry()
            registry.add_recognizer(SpacyRecognizer(supported_language="en", supported_entities=["PERSON"]))
            registry.add_recognizer(EmailRecognizer())
            registry.add_recognizer(CreditCardRecognizer())

            registry.add_recognizer(IndiaAadhaarRecognizer())
            registry.add_recognizer(IndiaPanRecognizer())
            registry.add_recognizer(IndiaGstinRecognizer())
            registry.add_recognizer(IndiaVoterIdRecognizer())
            registry.add_recognizer(IndiaPassportRecognizer())
            registry.add_recognizer(IndiaAddressRecognizer())
            registry.add_recognizer(IndiaPersonContextRecognizer())

            for rec in build_extended_indian_recognizers():
                registry.add_recognizer(rec)

            if self._gliner_enabled:
                try:
                    from presidio_analyzer.predefined_recognizers.ner.gliner_recognizer import (
                        GLiNERRecognizer,
                    )

                    gliner_rec = GLiNERRecognizer(
                        model_name="urchade/gliner_multi_pii-v1",
                        supported_entities=["PERSON", "ADDRESS"],
                        flat_ner=True,
                        multi_label=False,
                    )
                    registry.add_recognizer(gliner_rec)
                    logger.info("gliner_recognizer_enabled")
                except Exception as exc:
                    logger.warning("gliner_unavailable_falling_back_to_spacy", error=str(exc))

            analyzer = AnalyzerEngine(
                registry=registry,
                nlp_engine=nlp_engine,
                supported_languages=["en"],
            )
            self._analyzer = analyzer
            self._initialized = True
            logger.info("detection_engine_initialized", spacy_model=self._spacy_model)
        except Exception as exc:
            logger.error("detection_engine_init_failed", error=str(exc))
            raise DetectionEngineError(f"Local PII detector initialization failed: {exc}") from exc

    def _filter_result(self, text: str, res: RecognizerResult) -> bool:
        span_text = text[res.start : res.end].strip()
        if not span_text:
            return False
        if res.entity_type == "PERSON":
            if "/" in span_text:
                return False
            words = span_text.split()
            lower_words = [w.lower().strip(".,") for w in words]
            if span_text.lower() in _PERSON_FALSE_POSITIVES or len(span_text) < 3:
                return False
            recognizer_name = (res.recognition_metadata or {}).get("recognizer_name", "")
            if any(lw in _PERSON_FALSE_POSITIVES for lw in lower_words):
                if recognizer_name != "india_person_context_recognizer" or len(words) < 2:
                    return False
            if span_text.islower() or any(ch.isdigit() for ch in span_text):
                return False
            if not all(w[0].isupper() for w in words if w):
                return False
            if re.fullmatch(r"[A-Z]{5}[0-9]{4}[A-Z]", span_text):
                return False
            # All-caps PERSON names are accepted only from explicit labeled/honorific recognizer with 2+ words
            if span_text.isupper() and (recognizer_name != "india_person_context_recognizer" or len(words) < 2):
                return False
            if recognizer_name == "SpacyRecognizer" and len(words) >= 2 and any(len(w.strip(".,")) == 1 for w in words):
                return False
            if len(words) == 1 and recognizer_name == "SpacyRecognizer" and res.score < 0.86:
                return False
        if res.entity_type == "PROPERTY_LEGAL_ID":
            if len(span_text) < 3 or not any(ch.isdigit() for ch in span_text):
                return False
        if res.entity_type == "CREDIT_CARD":
            if not validate_luhn(span_text):
                return False
        if res.entity_type == "PHONE_NUMBER":
            digits = normalize_digits(span_text)
            if len(digits) < 10 or len(digits) > 13:
                return False
            if len(digits) == 12 and not span_text.lstrip().startswith("+") and digits[0] in "23456789":
                return False
        if res.entity_type == "ADDRESS":
            if len(span_text) < 8:
                return False
            if not (_PINCODE_RE.search(span_text) or _STREET_HINT_RE.search(span_text)):
                return False
        return True

    @staticmethod
    def _resolve_overlaps(items: Iterable[DetectionItem]) -> list[DetectionItem]:
        sorted_items = sorted(
            items,
            key=lambda d: (
                -_ENTITY_PRIORITY.get(d.entity_type, 50),
                -d.confidence,
                -(d.end - d.start),
                d.start,
            ),
        )
        accepted: list[DetectionItem] = []
        for candidate in sorted_items:
            overlaps = False
            for existing in accepted:
                if not (candidate.end <= existing.start or candidate.start >= existing.end):
                    overlaps = True
                    break
            if not overlaps:
                accepted.append(candidate)
        return sorted(accepted, key=lambda d: d.start)

    @staticmethod
    def _propagate_known_entities(text: str, items: list[DetectionItem]) -> list[DetectionItem]:
        extra: list[DetectionItem] = list(items)

        # 1. Propagate verified multi-word PERSON names across spaces/line-wraps (case-insensitive)
        known_persons: set[tuple[str, ...]] = set()
        for item in items:
            if item.entity_type == "PERSON" and item.confidence >= 0.75:
                words = [w for w in item.matched_text.split() if len(w) >= 2]
                if len(words) >= 2:
                    known_persons.add(tuple(words))

        for words in sorted(known_persons, key=lambda w: len(" ".join(w)), reverse=True):
            pat = re.compile(r"\b" + r"\s+".join(re.escape(w) for w in words) + r"\b", re.IGNORECASE)
            for match in pat.finditer(text):
                s, e = match.start(), match.end()
                if any(not (e <= ex.start or s >= ex.end) for ex in extra):
                    continue
                extra.append(
                    DetectionItem(
                        entity_type="PERSON",
                        category_tier=CategoryTier.MANDATORY,
                        start=s,
                        end=e,
                        confidence=0.90,
                        recognizer="document_person_propagation",
                        matched_text=match.group(0),
                        normalized_value=normalize_entity_value("PERSON", match.group(0)),
                    )
                )

        # 2. Propagate exact standalone structured IDs repeated in tables without repeating their labels
        _PROPAGATABLE_IDS = {
            "PROPERTY_LEGAL_ID": CategoryTier.EXTENDED,
            "PAN": CategoryTier.MANDATORY,
            "GSTIN": CategoryTier.MANDATORY,
            "VOTER_ID": CategoryTier.MANDATORY,
            "PASSPORT": CategoryTier.MANDATORY,
            "IFSC": CategoryTier.EXTENDED,
            "CUSTOMER_ID": CategoryTier.EXTENDED,
        }
        seen_id_pairs: set[tuple[str, str]] = set()
        for item in items:
            if item.entity_type in _PROPAGATABLE_IDS and len(item.matched_text.strip()) >= 4:
                seen_id_pairs.add((item.entity_type, item.matched_text.strip()))

        for ent_type, raw_val in sorted(seen_id_pairs, key=lambda x: len(x[1]), reverse=True):
            pat = re.compile(rf"(?<![A-Za-z0-9/\-_]){re.escape(raw_val)}(?![A-Za-z0-9/\-_])")
            for match in pat.finditer(text):
                s, e = match.start(), match.end()
                if any(not (e <= ex.start or s >= ex.end) for ex in extra):
                    continue
                extra.append(
                    DetectionItem(
                        entity_type=ent_type,
                        category_tier=_PROPAGATABLE_IDS[ent_type],
                        start=s,
                        end=e,
                        confidence=0.90,
                        recognizer="document_id_propagation",
                        matched_text=match.group(0),
                        normalized_value=normalize_entity_value(ent_type, match.group(0)),
                    )
                )

        return sorted(extra, key=lambda d: d.start)

    def detect(
        self,
        text: str,
        entities: list[str] | None = None,
        min_confidence: float = 0.60,
    ) -> tuple[list[DetectionItem], float]:
        t0 = time.perf_counter()
        if not self._initialized or self._analyzer is None:
            self.initialize()
        assert self._analyzer is not None

        clean_text = text.translate(_OCR_CHAR_CLEANUP)
        target_entities = entities if entities else ALL_SUPPORTED_ENTITIES
        try:
            raw_results = self._analyzer.analyze(
                text=clean_text,
                language="en",
                entities=target_entities,
                score_threshold=min_confidence,
            )
        except Exception as exc:
            logger.error("detection_analyze_failed", error=str(exc))
            raise DetectionEngineError(f"PII detection failed: {exc}") from exc

        candidates: list[DetectionItem] = []
        for res in raw_results:
            if res.entity_type not in ALL_SUPPORTED_ENTITIES:
                continue
            if not self._filter_result(clean_text, res):
                continue
            start, end = res.start, res.end
            while end > start and text[end - 1] in " \t\r\n.,;":
                end -= 1
            while start < end and text[start] in " \t\r\n":
                start += 1
            if end <= start:
                continue
            matched = text[start:end]
            rec_name = (res.recognition_metadata or {}).get("recognizer_name", "presidio")
            tier = (
                CategoryTier.MANDATORY
                if res.entity_type in MANDATORY_ENTITIES
                else CategoryTier.EXTENDED
            )
            candidates.append(
                DetectionItem(
                    entity_type=res.entity_type,
                    category_tier=tier,
                    start=start,
                    end=end,
                    confidence=round(float(res.score), 4),
                    recognizer=rec_name,
                    matched_text=matched,
                    normalized_value=normalize_entity_value(res.entity_type, clean_text[start:end]),
                )
            )

        resolved = self._resolve_overlaps(candidates)
        resolved = self._propagate_known_entities(clean_text, resolved)
        if entities is not None:
            allowed_set = set(entities)
            resolved = [d for d in resolved if d.entity_type in allowed_set]
        elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        return resolved, elapsed_ms


_detection_engine: DetectionIntelligenceEngine | None = None


def get_detection_engine() -> DetectionIntelligenceEngine:
    global _detection_engine
    if _detection_engine is None:
        _detection_engine = DetectionIntelligenceEngine()
    return _detection_engine
