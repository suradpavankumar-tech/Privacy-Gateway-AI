from __future__ import annotations

import re
from presidio_analyzer import EntityRecognizer, Pattern, PatternRecognizer, RecognizerResult

from app.services.detection.indian_validators import (
    validate_aadhaar_verhoeff,
    validate_gstin,
    validate_ifsc,
    validate_indian_passport,
    validate_pan,
    validate_voter_id,
)


class IndiaAadhaarRecognizer(EntityRecognizer):
    """Detects 12-digit Indian Aadhaar numbers with Verhoeff checksum + context scoring.

    Unlabeled 12-digit numbers must start with [2-9] and pass the Verhoeff checksum.
    Numbers explicitly preceded by an Aadhaar/UIDAI label (and not marked 'invalid') are
    also flagged even if a digit typo breaks Verhoeff or starts with '1'.
    """

    STRICT_PATTERN = re.compile(r"(?<!\d)([2-9][0-9]{3}[\s\-]?[0-9]{4}[\s\-]?[0-9]{4})(?!\d)")
    CONTEXT_FALLBACK_PATTERN = re.compile(r"(?<!\d)([1-9][0-9]{3}[\s\-]?[0-9]{4}[\s\-]?[0-9]{4})(?!\d)")
    CONTEXT_WORDS = ("aadhaar", "aadhar", "adhaar", "adhar", "aadhaaar", "uidai", "uid", "e-kyc", "ekyc", "आधार")
    BANK_CONTEXT_WORDS = ("a/c", "acct", "account", "ifsc", "bank", "disbursement", "settlement")

    def __init__(self) -> None:
        super().__init__(
            supported_entities=["AADHAAR"],
            name="india_aadhaar_validator",
            supported_language="en",
        )

    def load(self) -> None:
        pass

    def analyze(self, text: str, entities: list[str], nlp_artifacts=None) -> list[RecognizerResult]:
        if "AADHAAR" not in entities:
            return []
        results: list[RecognizerResult] = []
        seen_spans: set[tuple[int, int]] = set()
        lower_text = text.lower()

        for match in self.STRICT_PATTERN.finditer(text):
            raw = match.group(1)
            start, end = match.start(1), match.end(1)
            left_window = lower_text[max(0, start - 50) : start]
            full_window = lower_text[max(0, start - 50) : min(len(text), end + 30)]
            has_aadhaar_ctx = any(kw in full_window for kw in self.CONTEXT_WORDS)
            has_bank_ctx = any(kw in left_window for kw in self.BANK_CONTEXT_WORDS)

            if has_bank_ctx and not has_aadhaar_ctx:
                continue

            if validate_aadhaar_verhoeff(raw):
                score = 0.99 if has_aadhaar_ctx else 0.92
                results.append(RecognizerResult("AADHAAR", start, end, score))
                seen_spans.add((start, end))
            elif has_aadhaar_ctx:
                results.append(RecognizerResult("AADHAAR", start, end, 0.86))
                seen_spans.add((start, end))

        for match in self.CONTEXT_FALLBACK_PATTERN.finditer(text):
            start, end = match.start(1), match.end(1)
            if (start, end) in seen_spans:
                continue
            immediate_left = lower_text[max(0, start - 40) : start]
            if any(kw in immediate_left for kw in self.CONTEXT_WORDS) and "invalid" not in immediate_left:
                results.append(RecognizerResult("AADHAAR", start, end, 0.85))
                seen_spans.add((start, end))

        return results


class IndiaPanRecognizer(EntityRecognizer):
    """Detects Indian PAN numbers with 4th-character entity classification check."""

    PATTERN = re.compile(r"\b([A-Z]{5}[0-9]{4}[A-Z])\b")
    CONTEXT_WORDS = ("pan", "permanent account", "income tax", "nsdl", "tax id", "पैन")

    def __init__(self) -> None:
        super().__init__(
            supported_entities=["PAN"],
            name="india_pan_validator",
            supported_language="en",
        )

    def load(self) -> None:
        pass

    def analyze(self, text: str, entities: list[str], nlp_artifacts=None) -> list[RecognizerResult]:
        if "PAN" not in entities:
            return []
        results: list[RecognizerResult] = []
        lower_text = text.lower()
        for match in self.PATTERN.finditer(text):
            raw = match.group(1)
            start, end = match.start(1), match.end(1)
            window = lower_text[max(0, start - 50) : min(len(text), end + 30)]
            has_context = any(kw in window for kw in self.CONTEXT_WORDS)
            if validate_pan(raw):
                score = 0.99 if has_context else 0.93
                results.append(RecognizerResult("PAN", start, end, score))
            elif has_context:
                results.append(RecognizerResult("PAN", start, end, 0.82))
        return results


class IndiaGstinRecognizer(EntityRecognizer):
    """Detects 15-character Indian GSTIN with Mod-36 checksum & embedded PAN verification."""

    PATTERN = re.compile(r"\b([0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z])\b")
    CONTEXT_WORDS = ("gstin", "gst", "goods and services", "taxpayer", "invoice")

    def __init__(self) -> None:
        super().__init__(
            supported_entities=["GSTIN"],
            name="india_gstin_validator",
            supported_language="en",
        )

    def load(self) -> None:
        pass

    def analyze(self, text: str, entities: list[str], nlp_artifacts=None) -> list[RecognizerResult]:
        if "GSTIN" not in entities:
            return []
        results: list[RecognizerResult] = []
        lower_text = text.lower()
        for match in self.PATTERN.finditer(text):
            raw = match.group(1)
            start, end = match.start(1), match.end(1)
            window = lower_text[max(0, start - 50) : min(len(text), end + 30)]
            has_context = any(kw in window for kw in self.CONTEXT_WORDS)
            if validate_gstin(raw):
                results.append(RecognizerResult("GSTIN", start, end, 0.995))
            elif has_context:
                results.append(RecognizerResult("GSTIN", start, end, 0.88))
        return results


class IndiaVoterIdRecognizer(EntityRecognizer):
    """Detects Indian Voter ID (EPIC) numbers."""

    PATTERN = re.compile(r"\b([A-Z]{3}[0-9]{7})\b")
    CONTEXT_WORDS = ("voter", "epic", "elector", "election", "voter id", "matdata")

    def __init__(self) -> None:
        super().__init__(
            supported_entities=["VOTER_ID"],
            name="india_voter_id_validator",
            supported_language="en",
        )

    def load(self) -> None:
        pass

    def analyze(self, text: str, entities: list[str], nlp_artifacts=None) -> list[RecognizerResult]:
        if "VOTER_ID" not in entities:
            return []
        results: list[RecognizerResult] = []
        lower_text = text.lower()
        for match in self.PATTERN.finditer(text):
            raw = match.group(1)
            start, end = match.start(1), match.end(1)
            window = lower_text[max(0, start - 60) : min(len(text), end + 30)]
            has_context = any(kw in window for kw in self.CONTEXT_WORDS)
            if validate_voter_id(raw):
                score = 0.96 if has_context else 0.72
                results.append(RecognizerResult("VOTER_ID", start, end, score))
        return results


class IndiaPassportRecognizer(EntityRecognizer):
    """Detects Indian Passport numbers with issuing context."""

    PATTERN = re.compile(r"\b([A-PR-WY][0-9]{7}|[PSD][A-Z]{2}[0-9]{5})\b")
    CONTEXT_WORDS = ("passport", "passport no", "passport number", "travel document", "mea")

    def __init__(self) -> None:
        super().__init__(
            supported_entities=["PASSPORT"],
            name="india_passport_validator",
            supported_language="en",
        )

    def load(self) -> None:
        pass

    def analyze(self, text: str, entities: list[str], nlp_artifacts=None) -> list[RecognizerResult]:
        if "PASSPORT" not in entities:
            return []
        results: list[RecognizerResult] = []
        lower_text = text.lower()
        for match in self.PATTERN.finditer(text):
            raw = match.group(1)
            start, end = match.start(1), match.end(1)
            window = lower_text[max(0, start - 60) : min(len(text), end + 30)]
            has_context = any(kw in window for kw in self.CONTEXT_WORDS)
            if has_context and validate_indian_passport(raw):
                results.append(RecognizerResult("PASSPORT", start, end, 0.96))
        return results


class IndiaAddressRecognizer(EntityRecognizer):
    """Detects structured & semi-structured Indian residential/business addresses."""

    LABELED_PIN_PATTERN = re.compile(
        r"(?:(?:Residential|Permanent|Current|Registered|Delivery|Mailing|Home|Property|Schedule|Premises|Office)[ \t]+)?"
        r"(?:Address|Addr|Residence|Location|Property|Situated[ \t]+at|(?:having[ \t]+its[ \t]+)?Office[ \t]+at|Residing[ \t]+at|Resides[ \t]+at|Pata)[ \t]*[:\-][ \t]*"
        r"([^\n;]{4,180}?(?:\r?\n[^\n;]{1,100})?\b[1-9][0-9]{2}[ \t]?[0-9]{3}\b)",
        re.IGNORECASE,
    )
    LABELED_CITY_PATTERN = re.compile(
        r"(?:(?:Residential|Permanent|Current|Registered|Delivery|Mailing|Home|Property|Schedule|Premises|Office)[ \t]+)?"
        r"(?:Address|Addr|Residence|Location|Property|Situated[ \t]+at|Office[ \t]+at|Residing[ \t]+at|Pata)[ \t]*[:\-][ \t]*"
        r"([^\n;.]+?\b(?:Bengaluru|Bangalore|Mumbai|Delhi|New Delhi|Hyderabad|Chennai|Pune|Kolkata|Ahmedabad|Jaipur|Lucknow|Davangere|Mysuru|Hubballi|Surat|Kochi|Noida|Gurugram|Chandigarh|Indore|Bhopal|Nagpur|Patna|Karnataka|Maharashtra|Tamil Nadu|Telangana|Gujarat|Uttar Pradesh|Rajasthan|West Bengal|Kerala|Haryana)\b[^\n;.]*)",
        re.IGNORECASE,
    )
    UNLABELED_PIN_PATTERN = re.compile(
        r"((?:Flat|House|Plot|Door|No\.?|H\.No\.?|D\.No\.?|Sy\.?[ \t]*No\.?|Survey[ \t]*No\.?|Site[ \t]*No\.?|Khasra[ \t]*No\.?|Khata[ \t]*No\.?|Bldg|Building|Apt|Apartment|Villa|#)[ \t]*[A-Za-z0-9\-\/]+(?:,[ \t\r\n]*[^,\n]{2,55}){1,6}[ \t]*[-–,:]*[ \t]*[1-9][0-9]{2}[ \t]?[0-9]{3}\b)",
        re.IGNORECASE,
    )
    HINGLISH_ADDR_PATTERN = re.compile(
        r"(?:mera[ \t]+(?:ghar|address|pata)|rehta[ \t]+hu[n]?|rehti[ \t]+hu[n]?|both[ \t]+residing[ \t]+at|residing[ \t]+at|resides[ \t]+at|address[ \t]+to)[ \t]*[:\-]?[ \t]*([^\n;]{4,180}?(?:\r?\n[^\n;]{1,100})?\b[1-9][0-9]{2}[ \t]?[0-9]{3}\b)",
        re.IGNORECASE,
    )
    VILLAGE_TALUK_PATTERN = re.compile(
        r"\b([A-Za-z0-9\t \-]{2,35}\b(?:Village|Gram|Grama)\b[ \t\r\n,]*"
        r"(?:[A-Za-z0-9\t \-]{2,35}\b(?:Post|Hobli|Taluk|Taluka|Tq|District|Dist|Tehsil|Mandal)\b[ \t\r\n,]*){1,4}"
        r"(?:[A-Za-z\t \-]{2,30}\b(?:Taluk|Taluka|Tq|District|Dist|Karnataka|Maharashtra|Tamil Nadu|Telangana|India)\b)?\.?)",
        re.IGNORECASE,
    )
    URBAN_STREET_PATTERN = re.compile(
        r"\b(\d{1,3}(?:st|nd|rd|th)?[ \t]+(?:Cross|Main|Stage|Block|Phase|Lane|Road|Street)\b[ \t\r\n,]*"
        r"(?:[A-Za-z0-9\t \-\.]{2,45}\b(?:Main|Cross|Nagar|Nagara|Colony|Layout|Enclave|Vihar|Road|Street)\b[ \t\r\n,]*){1,4}"
        r"(?:(?:Near|Opp|Opposite|Behind)[ \t]+[A-Za-z0-9\t \-\.]{2,35}[ \t\r\n,]*){0,2}"
        r"(?:[A-Za-z\t ]{3,30}\b(?:DAVANAGERE|Davangere|Bengaluru|Bangalore|Mumbai|Delhi|Hyderabad|Chennai|Pune|Kolkata|Ahmedabad|Jaipur|Lucknow|Mysuru|Hubballi|Karnataka|Maharashtra|Tamil Nadu|Telangana|India)?\.?)?)",
        re.IGNORECASE,
    )
    UNLABELED_CIVIL_ADDR_PATTERN = re.compile(
        r"\b((?:Flat|House|Plot|Door|No\.?|H\.No\.?|D\.No\.?|Site[ \t]*No\.?|Khata[ \t]*No\.?|Survey[ \t]*No\.?|Sy\.?[ \t]*No\.?|Bldg|Building|Apt|Apartment|Villa)[ \t]*[A-Za-z0-9\-\/]+"
        r"(?:,[ \t\r\n]*[^,\n]{2,45}\b(?:Road|Rd|Street|St|Lane|Cross|Main|Nagar|Nagara|Colony|Layout|Enclave|Vihar|Phase|Sector|Block|Village|Post|Taluk|Dist|District)\b){1,4}"
        r"(?:,[ \t\r\n]*[A-Za-z\t ]{3,30}\b(?:Bengaluru|Bangalore|Mumbai|Delhi|Hyderabad|Chennai|Pune|Kolkata|Ahmedabad|Jaipur|Lucknow|Davangere|Davanagere|Mysuru|Hubballi|Surat|Noida|Gurugram|Karnataka|Maharashtra|Tamil Nadu|Telangana|India)?\.?)?)",
        re.IGNORECASE,
    )

    _CITY_STATE_RE = (
        r"(?:DAVANAGERE|Davangere|Bengaluru|Bangalore|Mumbai|Delhi|New[ \t]+Delhi|Hyderabad|Chennai|Pune|"
        r"Kolkata|Ahmedabad|Jaipur|Lucknow|Mysuru|Mysore|Hubballi|Hubli|Belgaum|Belagavi|Mangaluru|Mangalore|"
        r"Ballari|Bellary|Shimoga|Shivamogga|Tumakuru|Tumkur|Surat|Kochi|Noida|Gurugram|Gurgaon|Chandigarh|"
        r"Indore|Bhopal|Nagpur|Patna|Karnataka|Maharashtra|Tamil[ \t]+Nadu|Telangana|Andhra[ \t]+Pradesh|"
        r"Gujarat|Uttar[ \t]+Pradesh|Rajasthan|West[ \t]+Bengal|Kerala|Haryana|India)"
    )

    NAMED_AREA_LANDMARK_PATTERN = re.compile(
        r"\b([A-Za-z0-9\t \-\.]{2,45}\b(?:Extension|Extn?\.?|Nagar|Nagara|Colony|Layout|Enclave|Vihar|Badavane|Mohalla|Circle|Chowk|Marg|Road|Street|Block|Phase|Stage|Cross|Main)\b[ \t\r\n,]*"
        r"(?:[A-Za-z0-9\t \-\.]{2,45}\b(?:Block|Phase|Stage|Cross|Main)\b[ \t\r\n,]*){0,2}"
        r"(?:(?:Near|Opp|Opposite|Behind|In[ \t]+front[ \t]+of|Next[ \t]+to|Beside|Facing)[ \t]+[A-Za-z0-9\t \-\.]{2,45}[ \t\r\n,]*){0,2}"
        rf"(?:[A-Za-z0-9\t \-\.]{{0,30}}\b{_CITY_STATE_RE}\b[ \t]*(?:City|Town)?\.?)?)",
        re.IGNORECASE,
    )

    def __init__(self) -> None:
        super().__init__(
            supported_entities=["ADDRESS"],
            name="india_address_recognizer",
            supported_language="en",
        )

    def load(self) -> None:
        pass

    def analyze(self, text: str, entities: list[str], nlp_artifacts=None) -> list[RecognizerResult]:
        if "ADDRESS" not in entities:
            return []
        results: list[RecognizerResult] = []
        for pattern, score in (
            (self.LABELED_PIN_PATTERN, 0.96),
            (self.UNLABELED_PIN_PATTERN, 0.93),
            (self.HINGLISH_ADDR_PATTERN, 0.92),
            (self.VILLAGE_TALUK_PATTERN, 0.92),
            (self.URBAN_STREET_PATTERN, 0.91),
            (self.NAMED_AREA_LANDMARK_PATTERN, 0.91),
            (self.UNLABELED_CIVIL_ADDR_PATTERN, 0.90),
            (self.LABELED_CITY_PATTERN, 0.88),
        ):
            for match in pattern.finditer(text):
                val = match.group(1).strip().rstrip(".,;")
                if len(val) < 10:
                    continue
                start = match.start(1)
                end = start + len(val)
                results.append(RecognizerResult("ADDRESS", start, end, score))
        return results


class IndiaPersonContextRecognizer(EntityRecognizer):
    """Supplements spaCy NER with Indian honorifics, court/legal roles, parentage cues, and Hinglish name cues."""

    _HONORIFIC_BASE = r"(?:(?:Late[ \t]+)?(?:Sri|Shri|Shree|Sou|Sau|Smt|Kumari|Kum|Ku|Mr|Mrs|Ms|Dr|Prof|Adv)|Late)"
    _HONORIFIC_SEP_RE = rf"{_HONORIFIC_BASE}(?:\.[ \t]*|[ \t]+)"
    _SAME_LINE_WS = r"[ \t]+"
    _WRAP_NAME_WS = r"(?:[ \t]+|[ \t]*\r?\n[ \t]*(?![A-Za-z \t./-]{1,35}:))"
    _INITIAL_WORD = r"[A-Z]\.?(?![/\\\-a-zA-Z])"
    _TITLE_WORD = rf"(?:(?:[A-Z]\.?[ \t]*){{1,3}})?[A-Z][a-z\u00C0-\u024F]{{1,25}}"
    _TITLE_NAME_BODY_SINGLE = rf"{_TITLE_WORD}(?:{_SAME_LINE_WS}(?:{_TITLE_WORD}|{_INITIAL_WORD})){{0,3}}"
    _TITLE_NAME_BODY_WRAP = rf"{_TITLE_WORD}(?:{_WRAP_NAME_WS}(?:{_TITLE_WORD}|{_INITIAL_WORD})){{0,3}}"
    _CAPS_NAME_BODY = r"[A-Z]{2,20}(?:[ \t]+[A-Z]{2,20}){1,3}"
    _LEADING_HONORIFIC_STRIP = re.compile(
        rf"^{_HONORIFIC_BASE}(?:\.\s*|\s+)",
        re.IGNORECASE,
    )

    LABELED_NAME_PATTERN = re.compile(
        r"(?:(?:Applicant|Customer|Cust|Client|Candidate|User|Claimant|Policyholder|Insured|Account[ \t]+Holder|Beneficiary|Employee|Complainant|Patient|Nominee|Vendor|Vendee|Buyer|Seller|Lessor|Lessee|Licensor|Licensee|Executant|Petitioner|Respondent|Plaintiff|Defendant|Deponent|Testator|Donor|Donee|Witness|Advocate|Counsel|First[ \t]+Party|Second[ \t]+Party|Owner|Co-Owner|Authorized[ \t]+Signatory|Purchaser|Holder|Full|Contact)?[ \t]*Name|"
        r"Vendor|Vendee|Buyer|Seller|Lessor|Lessee|Executant|Claimant|Petitioner|Respondent|Plaintiff|Defendant|Deponent|Testator|Witness|Advocate)[ \t]*[:\-=][ \t]*"
        rf"((?:(?i:{_HONORIFIC_SEP_RE}))?(?:{_TITLE_NAME_BODY_SINGLE}|{_CAPS_NAME_BODY}))"
    )
    PARENT_SPOUSE_PATTERN = re.compile(
        r"(?<![A-Za-z])(?i:S[/\\|io\-]?o|D[/\\|io\-]?o|W[/\\|io\-]?o|C[/\\|io\-]?o|H[/\\|io\-]?o|Father'?s[ \t]+Name|Mother'?s[ \t]+Name|Spouse'?s[ \t]+Name)[ \t.:\-=]+"
        rf"((?:(?i:{_HONORIFIC_SEP_RE}))?(?:{_TITLE_NAME_BODY_SINGLE}|{_CAPS_NAME_BODY}))\b"
    )
    COURT_PARTY_PATTERN = re.compile(
        r"(?<![A-Za-z])(?i:Plaintiff|Defendant|Petitioner|Respondent|Applicant|Appellant|Opposite[ \t]+Party|Accused|Witness)[s]?"
        r"(?:[ \t]*(?:No\.?|Nos\.?)?[ \t]*\d{1,2}[ \t]*[.:\-]?)?[ \t]*[:\-]?[ \t]*"
        rf"((?:(?i:{_HONORIFIC_SEP_RE}))?(?:{_TITLE_NAME_BODY_SINGLE}|{_CAPS_NAME_BODY}))\b"
    )
    HONORIFIC_NAME_PATTERN = re.compile(
        rf"(?<![A-Za-z])(?i:{_HONORIFIC_SEP_RE})({_TITLE_NAME_BODY_SINGLE}|{_TITLE_NAME_BODY_WRAP}|{_CAPS_NAME_BODY})\b"
    )
    HINGLISH_NAME_PATTERN = re.compile(
        r"(?i:mera[ \t]+naam|my[ \t]+name[ \t]+is|naam[ \t]*[:\-])[ \t]*([A-Z][a-z]{1,25}(?:[ \t]+[A-Z][a-z]{1,25}){0,2})"
    )

    _NON_NAMES_LOWER = {
        "loan", "application", "number", "address", "bank", "account", "insurance",
        "claim", "support", "ticket", "policy", "india", "private", "limited", "llp",
        "january", "february", "march", "april", "may", "june", "july",
        "august", "september", "october", "november", "december",
        "holder", "claimant", "applicant", "customer", "amount", "name",
        "deed", "sale", "lease", "agreement", "contract", "notice", "legal",
        "property", "schedule", "district", "state", "court", "tribunal",
        "registrar", "sub-registrar", "authority", "corporation", "clause", "section",
        "stamp", "duty", "witness", "party", "execution", "registration",
        "age", "yrs", "years", "occupation", "occ", "service", "pan", "residing",
        "developers", "developer", "promoter", "promoters", "balance", "land",
        "project", "building", "area", "said", "page", "note", "dummy", "document",
        "plaintiff", "defendant", "defendants", "petitioner", "respondent", "applicant",
        "appellant", "accused", "advocate", "counsel", "coolie", "agriculturist",
        "farmer", "year", "sio", "dio", "wio", "cio", "s/o", "d/o", "w/o", "c/o", "apmc",
    }

    def __init__(self) -> None:
        super().__init__(
            supported_entities=["PERSON"],
            name="india_person_context_recognizer",
            supported_language="en",
        )

    def load(self) -> None:
        pass

    def analyze(self, text: str, entities: list[str], nlp_artifacts=None) -> list[RecognizerResult]:
        if "PERSON" not in entities:
            return []
        results: list[RecognizerResult] = []
        for pattern, score in (
            (self.LABELED_NAME_PATTERN, 0.95),
            (self.PARENT_SPOUSE_PATTERN, 0.94),
            (self.COURT_PARTY_PATTERN, 0.93),
            (self.HONORIFIC_NAME_PATTERN, 0.91),
            (self.HINGLISH_NAME_PATTERN, 0.90),
        ):
            for match in pattern.finditer(text):
                raw_span = match.group(1)
                start = match.start(1)
                stripped_match = self._LEADING_HONORIFIC_STRIP.match(raw_span)
                if stripped_match:
                    offset = stripped_match.end()
                    raw_span = raw_span[offset:]
                    start += offset
                candidate = raw_span.strip()
                words = candidate.split()
                if not words or any(w.lower().strip(".,") in self._NON_NAMES_LOWER for w in words):
                    continue
                if len(candidate) < 3:
                    continue
                # Require at least 2 words for ALL-CAPS matches unless explicitly multi-word
                if candidate.isupper() and len(words) < 2:
                    continue
                end = start + len(candidate)
                results.append(RecognizerResult("PERSON", start, end, score))
        return results


class _Group1RegexRecognizer(EntityRecognizer):
    """Emits Presidio spans strictly for regex capture group 1 (excluding label prefixes)."""

    def __init__(
        self,
        entity_type: str,
        name: str,
        patterns: list[tuple[re.Pattern[str], float]],
    ) -> None:
        super().__init__(
            supported_entities=[entity_type],
            name=name,
            supported_language="en",
        )
        self._entity_type = entity_type
        self._compiled = patterns

    def load(self) -> None:
        pass

    def analyze(self, text: str, entities: list[str], nlp_artifacts=None) -> list[RecognizerResult]:
        if self._entity_type not in entities:
            return []
        results: list[RecognizerResult] = []
        for pat, score in self._compiled:
            for match in pat.finditer(text):
                start, end = match.start(1), match.end(1)
                if end > start:
                    results.append(RecognizerResult(self._entity_type, start, end, score))
        return results


def build_extended_indian_recognizers() -> list[EntityRecognizer]:
    """Extended Indian & financial recognizers clearly separate from the 7 mandatory entities."""
    phone_recognizer = PatternRecognizer(
        supported_entity="PHONE_NUMBER",
        name="india_phone_recognizer",
        patterns=[
            Pattern("in_mobile_intl", r"(?<!\d)(\+91[\s\-]?[6-9][0-9]{9})(?!\d)", 0.95),
            Pattern("in_mobile_0", r"(?<!\d)(0[6-9][0-9]{9})(?!\d)", 0.88),
            Pattern("in_mobile_plain", r"\b([6-9][0-9]{9})\b", 0.72),
        ],
        context=["phone", "ph", "mobile", "mob", "mbl", "contact", "call", "whatsapp", "wa", "tel", "cell", "no", "num"],
    )

    phone_context_recognizer = _Group1RegexRecognizer(
        entity_type="PHONE_NUMBER",
        name="india_phone_context_recognizer",
        patterns=[
            (
                re.compile(
                    r"(?:(?:Phone|Ph\.?|Phn|Mobile|Mob\.?|Mbl|Cell|Telephone|Tel\.?|Contact|Whatsapp|WA|Call)[ \t]*(?:No\.?|Nos\.?|Num(?:ber)?|Nmbr|Nbr|#|Id)?[ \t]*[:\-=]?[ \t]*)((?:\+91[\s\-]?|91[\s\-]?|0)?[1-9][0-9]{9}|(?:\+91[\s\-]?|0)?[1-9][0-9]{2,4}[\s\-][0-9]{5,8})(?!\d)",
                    re.IGNORECASE,
                ),
                0.96,
            )
        ],
    )

    ifsc_recognizer = PatternRecognizer(
        supported_entity="IFSC",
        name="india_ifsc_recognizer",
        patterns=[Pattern("in_ifsc", r"\b([A-Z]{4}0[A-Z0-9]{6})\b", 0.94)],
        context=["ifsc", "branch", "bank", "neft", "rtgs", "imps"],
    )

    bank_acct_recognizer = _Group1RegexRecognizer(
        entity_type="BANK_ACCOUNT",
        name="india_bank_account_recognizer",
        patterns=[
            (
                re.compile(
                    r"(?:(?:A/c|Ac\.?|Acct|Account|Bank[ \t]*A/c)[ \t]*(?:No\.?|Nos\.?|Num(?:ber)?|Nmbr|Nbr|#)?[ \t]*[:\-=]?[ \t]*)([0-9]{9,18})\b",
                    re.IGNORECASE,
                ),
                0.96,
            )
        ],
    )

    upi_recognizer = PatternRecognizer(
        supported_entity="UPI_ID",
        name="india_upi_recognizer",
        patterns=[
            Pattern(
                "in_upi",
                r"\b([a-zA-Z0-9.\-_]{2,40}@(?:okaxis|okicici|okhdfcbank|oksbi|ybl|ibl|axl|paytm|upi|apl|sbi|hdfcbank|icici))\b",
                0.96,
            )
        ],
        context=["upi", "vpa", "payment", "gpay", "phonepe", "paytm"],
    )

    dob_recognizer = _Group1RegexRecognizer(
        entity_type="DATE_OF_BIRTH",
        name="india_dob_recognizer",
        patterns=[
            (
                re.compile(
                    r"(?:(?:DOB|Date[ \t]+of[ \t]+Birth|Birth[ \t]+Date|D\.O\.B\.?)[ \t]*[:\-]?[ \t]*)([0-3]?[0-9][/\-.][0-1]?[0-9][/\-.](?:19|20)[0-9]{2}|(?:19|20)[0-9]{2}[/\-.][0-1]?[0-9][/\-.][0-3]?[0-9])",
                    re.IGNORECASE,
                ),
                0.95,
            )
        ],
    )

    customer_id_recognizer = _Group1RegexRecognizer(
        entity_type="CUSTOMER_ID",
        name="enterprise_customer_id_recognizer",
        patterns=[
            (
                re.compile(
                    r"(?:(?:Customer[ \t]+ID|Cust[ \t]+ID|CIF|Policy[ \t]+No\.?|Loan[ \t]+ID|Claim[ \t]+ID|Employee[ \t]+ID|EMP[ \t]+ID)[ \t]*[:\-][ \t]*)([A-Z]{2,5}[\-_]?[0-9]{4,10})\b",
                    re.IGNORECASE,
                ),
                0.93,
            )
        ],
    )

    property_legal_id_recognizer = _Group1RegexRecognizer(
        entity_type="PROPERTY_LEGAL_ID",
        name="india_property_legal_id_recognizer",
        patterns=[
            (
                re.compile(
                    r"(?:(?:Sale[ \t]+Deed[ \t]+(?:Reg(?:istration)?\.?[ \t]+)?No\.?|Deed[ \t]+(?:Reg(?:istration)?\.?[ \t]+)?No\.?|Sub-Registrar[ \t]+(?:Reg\.?[ \t]+)?No\.?|Property[ \t]+ID|PID[ \t]+No\.?|Khata[ \t]+No\.?|Khasra[ \t]+No\.?|Survey[ \t]+No\.?|Sy\.?[ \t]*No\.?|CNR[ \t]+No\.?|Writ[ \t]+Petition[ \t]+No\.?|Case[ \t]+No\.?|Suit[ \t]+No\.?|O\.?S\.?[ \t]+No\.?|Bar[ \t]+Council[ \t]+(?:No\.?|ID)|RERA[ \t]+Reg(?:istration)?\.?[ \t]+No\.?)[ \t]*[:\-]?[ \t]*)((?=[A-Za-z0-9/\-_]*[0-9])[A-Za-z0-9][A-Za-z0-9/\-_]{2,32})",
                    re.IGNORECASE,
                ),
                0.93,
            )
        ],
    )

    return [
        phone_recognizer,
        phone_context_recognizer,
        ifsc_recognizer,
        bank_acct_recognizer,
        upi_recognizer,
        dob_recognizer,
        customer_id_recognizer,
        property_legal_id_recognizer,
    ]
