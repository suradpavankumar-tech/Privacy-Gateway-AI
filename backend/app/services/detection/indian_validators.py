"""
=========================================================================================
indian_validators.py — Mathematical Checksum & Structural Validation for Indian Identifiers
=========================================================================================

Tech Stack:
 - Python 3.11+ (High-speed bitwise and modular arithmetic)
 - Abstract Algebra / Number Theory (Dihedral Group D5 for Verhoeff check digit algorithm)
 - Luhn Modulo 10 & Modulo 36 Checksums

Key Architectural Responsibilities:
 1. Aadhaar 12-Digit Verhoeff Algorithm:
    - Implements dihedral group D5 multiplication and permutation matrices to validate
      the 12th check digit of Indian Aadhaar numbers.
    - Catches all single-digit errors and 100% of adjacent transposition errors.

 2. PAN (Permanent Account Number) Validation:
    - Validates 10-character structure (`[A-Z]{3}[ABCFGHLJPT][A-Z][0-9]{4}[A-Z]`).
    - Enforces 4th-character entity semantics (P = Individual, C = Company, H = HUF, F = Firm).

 3. GSTIN Modulo-36 Checksum:
    - Validates 15-character GSTIN numbers (2-digit state code, embedded 10-char PAN,
      entity index, default 'Z', and final weighted modulo-36 checksum).

 4. Banking & Payment Identifiers:
    - Validates 11-character RBI IFSC codes, Voter IDs (EPIC), Indian Passports,
      and 16-digit payment card numbers via the Luhn algorithm.
=========================================================================================
"""

from __future__ import annotations

import re

# Verhoeff algorithm tables for Aadhaar 12-digit validation
_VERHOEFF_D = (
    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
    (1, 2, 3, 4, 0, 6, 7, 8, 9, 5),
    (2, 3, 4, 0, 1, 7, 8, 9, 5, 6),
    (3, 4, 0, 1, 2, 8, 9, 5, 6, 7),
    (4, 0, 1, 2, 3, 9, 5, 6, 7, 8),
    (5, 9, 8, 7, 6, 0, 4, 3, 2, 1),
    (6, 5, 9, 8, 7, 1, 0, 4, 3, 2),
    (7, 6, 5, 9, 8, 2, 1, 0, 4, 3),
    (8, 7, 6, 5, 9, 3, 2, 1, 0, 4),
    (9, 8, 7, 6, 5, 4, 3, 2, 1, 0),
)

_VERHOEFF_P = (
    (0, 1, 2, 3, 4, 5, 6, 7, 8, 9),
    (1, 5, 7, 6, 2, 8, 3, 0, 9, 4),
    (5, 8, 0, 3, 7, 9, 6, 1, 4, 2),
    (8, 9, 1, 6, 0, 4, 3, 5, 2, 7),
    (9, 4, 5, 3, 1, 2, 6, 8, 7, 0),
    (4, 2, 8, 6, 5, 7, 3, 9, 0, 1),
    (2, 7, 9, 3, 8, 0, 6, 4, 1, 5),
    (7, 0, 4, 6, 9, 1, 3, 2, 5, 8),
)

_GSTIN_CHARSET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
_PAN_ENTITY_CHARS = set("ABCFGHLJPT")
_VALID_GST_STATES = {f"{i:02d}" for i in range(1, 39)} | {"97", "99"}


def normalize_digits(value: str) -> str:
    return re.sub(r"[\s\-]+", "", value.strip())


def compute_verhoeff_check_digit(base_11: str) -> str:
    """Compute the 12th Verhoeff check digit for an 11-digit numeric string."""
    inv = (0, 4, 3, 2, 1, 5, 6, 7, 8, 9)
    c = 0
    for i, ch in enumerate(reversed(base_11)):
        c = _VERHOEFF_D[c][_VERHOEFF_P[(i + 1) % 8][int(ch)]]
    return str(inv[c])


def validate_aadhaar_verhoeff(value: str) -> bool:
    digits = normalize_digits(value)
    if len(digits) != 12 or not digits.isdigit():
        return False
    if digits[0] in ("0", "1"):
        return False
    # Reject trivial repeating sequences like 222222222222
    if len(set(digits)) <= 2:
        return False
    c = 0
    for i, ch in enumerate(reversed(digits)):
        c = _VERHOEFF_D[c][_VERHOEFF_P[i % 8][int(ch)]]
    return c == 0


def validate_pan(value: str) -> bool:
    cleaned = value.strip().upper()
    if not re.fullmatch(r"[A-Z]{3}[ABCFGHLJPT][A-Z][0-9]{4}[A-Z]", cleaned):
        return False
    return cleaned[3] in _PAN_ENTITY_CHARS


def compute_gstin_check_char(first_14: str) -> str:
    factor = 2
    total = 0
    n = len(_GSTIN_CHARSET)
    for ch in reversed(first_14.upper()):
        code_point = _GSTIN_CHARSET.index(ch)
        addend = factor * code_point
        factor = 1 if factor == 2 else 2
        addend = (addend // n) + (addend % n)
        total += addend
    remainder = total % n
    check_code_point = (n - remainder) % n
    return _GSTIN_CHARSET[check_code_point]


def validate_gstin(value: str) -> bool:
    cleaned = value.strip().upper()
    if not re.fullmatch(r"[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]", cleaned):
        return False
    if cleaned[:2] not in _VALID_GST_STATES:
        return False
    if not validate_pan(cleaned[2:12]):
        return False
    return compute_gstin_check_char(cleaned[:14]) == cleaned[14]


def validate_luhn(value: str) -> bool:
    digits = normalize_digits(value)
    if not digits.isdigit() or not (13 <= len(digits) <= 19):
        return False
    total = 0
    reverse_digits = digits[::-1]
    for idx, ch in enumerate(reverse_digits):
        n = int(ch)
        if idx % 2 == 1:
            n *= 2
            if n > 9:
                n -= 9
        total += n
    return total % 10 == 0


def validate_ifsc(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Z]{4}0[A-Z0-9]{6}", value.strip().upper()))


def validate_voter_id(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Z]{3}[0-9]{7}", value.strip().upper()))


def validate_indian_passport(value: str) -> bool:
    cleaned = value.strip().upper()
    return bool(
        re.fullmatch(r"[A-PR-WY][0-9]{7}", cleaned)
        or re.fullmatch(r"[PSD][A-Z]{2}[0-9]{5}", cleaned)
    )
