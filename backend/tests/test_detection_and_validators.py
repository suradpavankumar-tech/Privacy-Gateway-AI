from __future__ import annotations

from app.services.detection.engine import get_detection_engine
from app.services.detection.indian_validators import (
    compute_gstin_check_char,
    compute_verhoeff_check_digit,
    validate_aadhaar_verhoeff,
    validate_gstin,
    validate_indian_passport,
    validate_pan,
    validate_voter_id,
)


def test_indian_validators_checksums():
    aadhaar = "23456789012" + compute_verhoeff_check_digit("23456789012")
    assert validate_aadhaar_verhoeff(aadhaar) is True
    assert validate_aadhaar_verhoeff("123456789012") is False  # starts with 1
    assert validate_aadhaar_verhoeff(aadhaar[:-1] + str((int(aadhaar[-1]) + 1) % 10)) is False

    assert validate_pan("ABCPK1234M") is True
    assert validate_pan("ABCZK1234M") is False  # invalid 4th entity char

    prefix14 = "29ABCPK1234M1Z"
    gstin = prefix14 + compute_gstin_check_char(prefix14)
    assert validate_gstin(gstin) is True
    assert validate_gstin(prefix14 + ("0" if gstin[-1] != "0" else "1")) is False

    assert validate_voter_id("KAC4501200") is True
    assert validate_indian_passport("P7102400") is True


def test_detection_all_mandatory_entities_and_hinglish():
    engine = get_detection_engine()
    aadhaar = "45678901234" + compute_verhoeff_check_digit("45678901234")
    aadhaar_spaced = f"{aadhaar[:4]} {aadhaar[4:8]} {aadhaar[8:12]}"
    gstin = "27ABCPK1234M1Z" + compute_gstin_check_char("27ABCPK1234M1Z")

    text = (
        f"Namaste, mera naam Aarav Sharma hai. "
        f"Aadhaar: {aadhaar_spaced}, PAN: ABCPK1234M, GSTIN: {gstin}, "
        f"Voter ID: KAC4501200, Passport No: P7102400. "
        f"Address: Flat 402, Sai Krupa Residency, Vidyanagar, Davangere, Karnataka - 577005."
    )
    detections, _ = engine.detect(text)
    found_types = {d.entity_type for d in detections}

    for mandatory in ("PERSON", "AADHAAR", "PAN", "GSTIN", "VOTER_ID", "PASSPORT", "ADDRESS"):
        assert mandatory in found_types, f"Missing mandatory entity {mandatory}"

    pan_matches = [d for d in detections if d.entity_type == "PAN"]
    assert len(pan_matches) == 1
    assert pan_matches[0].matched_text == "ABCPK1234M"


def test_labeled_malformed_aadhaar_detected_but_invalid_ref_ignored():
    engine = get_detection_engine()
    text = "Aadhaar Number: 1234-5678-9012\nNote: Invalid ref 1000 0000 0000 ignore karein."
    detections, _ = engine.detect(text)
    aadhaars = [d.matched_text for d in detections if d.entity_type == "AADHAAR"]
    assert "1234-5678-9012" in aadhaars
    assert "1000 0000 0000" not in aadhaars


def test_handwritten_slang_abbreviations_and_trailing_initials():
    engine = get_detection_engine()
    text = (
        "Name : Prem Kumar K\n"
        "Adhaar No: 1234 5678 8765\n"
        "Phone No: +91 1234567890\n"
        "Mob # 9845012345\n"
        "Ph Num = +91-1234567890\n"
        "Ac No: 304958102900\n"
    )
    detections, _ = engine.detect(text)
    by_type: dict[str, list[str]] = {}
    for d in detections:
        by_type.setdefault(d.entity_type, []).append(d.matched_text)

    assert "Prem Kumar K" in by_type.get("PERSON", [])
    assert "1234 5678 8765" in by_type.get("AADHAAR", [])
    assert "+91 1234567890" in by_type.get("PHONE_NUMBER", [])
    assert "9845012345" in by_type.get("PHONE_NUMBER", [])
    assert "+91-1234567890" in by_type.get("PHONE_NUMBER", [])
    assert "304958102900" in by_type.get("BANK_ACCOUNT", [])


def test_court_document_multiple_indian_parties_and_addresses():
    engine = get_detection_engine()
    court_text = (
        "Plaintiff Sri.K.S.Rudrappa\n"
        "S/o Siddappa,\n"
        "Aged 45 years,\n"
        "ALUR VILLAGE,\n"
        "Alur Post,\n"
        "Davanagere Taluk.\n"
        "V/s\n"
        "Defendants 1. Sri.Hanumanthappa,\n"
        "Sio Rudrappa,\n"
        "2. Sri.Hanumanth,\n"
        "S/o Paiakshi,\n"
        "2nd Cross, H.K.R. Nagara, Bharath Colony, Near APMC, DAVANAGERE.\n"
        "3. Sri.Siddeshi,\n"
        "S/o Palakshi,\n"
        "4. Sri.Nagaraj,\n"
        "S/o Kurki Gurusiddappa\n"
    )
    detections, _ = engine.detect(court_text)
    by_type: dict[str, list[str]] = {}
    for d in detections:
        by_type.setdefault(d.entity_type, []).append(d.matched_text)

    persons = by_type.get("PERSON", [])
    assert "K.S.Rudrappa" in persons
    assert "Siddappa" in persons
    assert "Hanumanthappa" in persons
    assert "Rudrappa" in persons
    assert "Hanumanth" in persons
    assert "Paiakshi" in persons
    assert "Siddeshi" in persons
    assert "Palakshi" in persons
    assert "Nagaraj" in persons
    assert "Kurki Gurusiddappa" in persons

    addresses = by_type.get("ADDRESS", [])
    assert len(addresses) >= 2
    assert any("ALUR VILLAGE" in a and "Taluk" in a for a in addresses)
    assert any("2nd Cross" in a and "DAVANAGERE" in a for a in addresses)


def test_court_document_surnames_and_landmark_addresses():
    engine = get_detection_engine()
    court_text = (
        "5. Sri. Revanasiddappa,\n"
        "S/o Kurki Gurusıddappa,\n"
        "6. Smt. Siddamma,\n"
        "W/o Late Dodda Bheemappa,\n"
        "7. Sri.Thippeswamy,\n"
        "S/o Late Dodda Bheemappa,\n"
        "Anjaneya Extension, In front of Anjaneya Temple, DAVANAGERE CITY.\n"
        "8. Sri.Ganesh,\n"
        "9. Sri.Alur Manjúmath,\n"
        "S/o Late Dodda Bheemappa\n"
    )
    detections, _ = engine.detect(court_text)
    by_type: dict[str, list[str]] = {}
    for d in detections:
        by_type.setdefault(d.entity_type, []).append(d.matched_text)

    persons = by_type.get("PERSON", [])
    assert "Revanasiddappa" in persons
    assert "Kurki Gurusıddappa" in persons
    assert "Siddamma" in persons
    assert "Dodda Bheemappa" in persons
    assert "Thippeswamy" in persons
    assert "Ganesh" in persons
    assert "Alur Manjúmath" in persons

    addresses = by_type.get("ADDRESS", [])
    assert any("Anjaneya Extension" in a and "DAVANAGERE" in a for a in addresses)


