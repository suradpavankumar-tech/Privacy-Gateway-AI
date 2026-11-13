from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

# Allow running directly from repo root
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.services.detection.indian_validators import (  # noqa: E402
    compute_gstin_check_char,
    compute_verhoeff_check_digit,
)


def make_aadhaar(base11: str, sep: str = " ") -> str:
    check = compute_verhoeff_check_digit(base11)
    full = base11 + check
    return f"{full[0:4]}{sep}{full[4:8]}{sep}{full[8:12]}" if sep else full


def make_gstin(state: str, pan: str, entity_num: str = "1") -> str:
    prefix14 = f"{state}{pan}{entity_num}Z"
    return prefix14 + compute_gstin_check_char(prefix14)


def build_annotated_doc(
    doc_id: str,
    category: str,
    purpose: str,
    title: str,
    segments: list[tuple[str, str | None]],
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """Assemble text from (literal_text, entity_type_or_None) segments with exact char offsets."""
    text_parts: list[str] = []
    annotations: list[dict[str, Any]] = []
    cursor = 0
    for content, entity_type in segments:
        start = cursor
        text_parts.append(content)
        cursor += len(content)
        if entity_type is not None:
            annotations.append(
                {
                    "doc_id": doc_id,
                    "category": category,
                    "entity_type": entity_type,
                    "start": start,
                    "end": cursor,
                    "expected_value": content,
                }
            )
    full_text = "".join(text_parts)
    for ann in annotations:
        assert full_text[ann["start"] : ann["end"]] == ann["expected_value"]
    return (
        {
            "doc_id": doc_id,
            "category": category,
            "purpose": purpose,
            "title": title,
            "text": full_text,
        },
        annotations,
    )


_NAMES = [
    "Aarav Sharma", "Priya Nair", "Vikramaditya Kulkarni", "Ananya Chatterjee",
    "Suresh Reddy", "Fatima Begum", "Harpreet Singh", "Karthik Subramanian",
    "Neha Deshpande", "Arjun Malhotra", "Deepika Joshi", "Mohammed Irfan",
    "Sneha Patil", "Rajeshwari Iyer", "Siddharth Verma", "Pooja Agarwal",
    "Rohan Hegde", "Lakshmi Narayanan", "Kunal Banerjee", "Divya Menon",
]

_ADDRESSES = [
    "Flat 402, Sai Krupa Residency, 4th Main, Vidyanagar, Davangere, Karnataka - 577005",
    "House No. 18-4-212, Jubilee Hills Road No. 12, Hyderabad, Telangana - 500033",
    "Plot 27, Shanti Niketan Colony, Kothrud, Pune, Maharashtra - 411038",
    "Door No. 14/3, Anna Nagar East, 2nd Avenue, Chennai, Tamil Nadu - 600102",
    "Flat 9B, Parkview Enclave, Sector 18, Gurugram, Haryana - 122015",
    "No. 56, 3rd Cross, Indiranagar Stage 2, Bengaluru, Karnataka - 560038",
    "B-204, Silver Oak Apartments, Satellite Road, Ahmedabad, Gujarat - 380015",
    "House 74, Civil Lines, Near Clock Tower, Jaipur, Rajasthan - 302006",
    "Flat 12, Lakeview Gardens, Salt Lake Sector V, Kolkata, West Bengal - 700091",
    "Door 8/115, Marine Drive Extension, Ernakulam, Kochi, Kerala - 682031",
]

_CITIES_STATES = [
    ("29", "BLR"), ("36", "HYD"), ("27", "PUN"), ("33", "CHE"), ("06", "GUR"),
    ("29", "BLR"), ("24", "AMD"), ("08", "JAI"), ("19", "KOL"), ("32", "KOC"),
]


def generate_50_documents() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    docs: list[dict[str, Any]] = []
    anns: list[dict[str, Any]] = []

    # 1. 15 Loan Applications
    for i in range(15):
        doc_id = f"LOAN-{i+1:03d}"
        name = _NAMES[i % len(_NAMES)]
        addr = _ADDRESSES[i % len(_ADDRESSES)]
        state_code, _ = _CITIES_STATES[i % len(_CITIES_STATES)]
        aadhaar = make_aadhaar(f"{2 + (i % 7)}{104857690 + i * 137:010d}"[:11], sep=" " if i % 2 == 0 else "-")
        surname_ch = name.split()[-1][0].upper()
        pan = f"ABCP{surname_ch}{1020 + i:04d}{'ABCDEFGHJKLMNPQR'[i % 16]}"
        phone = f"+91 98{45012300 + i * 111:08d}"
        email = f"{name.lower().replace(' ', '.')}.{i+1}@example.in"
        ifsc = f"SBIN000{4100 + i:04d}"
        acct = f"30495810{2900 + i:04d}"
        gstin = make_gstin(state_code, pan) if i % 3 == 0 else None

        segments: list[tuple[str, str | None]] = [
            ("RETAIL HOME LOAN APPLICATION\nApplicant Name: ", None),
            (name, "PERSON"),
            ("\nDOB: ", None),
            (f"{10 + (i % 18):02d}/0{(i % 9) + 1}/19{82 + (i % 15):02d}", "DATE_OF_BIRTH"),
            ("\nAadhaar Number: ", None),
            (aadhaar, "AADHAAR"),
            ("\nPAN Number: ", None),
            (pan, "PAN"),
            ("\nResidential Address: ", None),
            (addr, "ADDRESS"),
            ("\nMobile: ", None),
            (phone, "PHONE_NUMBER"),
            (" | Email: ", None),
            (email, "EMAIL_ADDRESS"),
            (f"\nDisbursement Bank A/c No: ", None),
            (acct, "BANK_ACCOUNT"),
            (" (IFSC: ", None),
            (ifsc, "IFSC"),
            (")\n", None),
        ]
        if gstin:
            segments.extend([("Business GSTIN: ", None), (gstin, "GSTIN"), ("\n", None)])
        # Repeated entity to test request-scoped consistency
        segments.extend(
            [
                ("Declaration: I, ", None),
                (name, "PERSON"),
                (f", confirm my PAN ", None),
                (pan, "PAN"),
                (f" for loan sanction of INR {12 + i},50,000.\n", None),
            ]
        )
        d, a = build_annotated_doc(
            doc_id=doc_id,
            category="loan_application",
            purpose="loan_underwriting",
            title=f"Retail Loan Application #{i+1}",
            segments=segments,
        )
        docs.append(d)
        anns.extend(a)

    # 2. 15 KYC Documents
    for i in range(15):
        doc_id = f"KYC-{i+1:03d}"
        name = _NAMES[(i + 5) % len(_NAMES)]
        addr = _ADDRESSES[(i + 3) % len(_ADDRESSES)]
        state_code, _ = _CITIES_STATES[(i + 3) % len(_CITIES_STATES)]
        aadhaar = make_aadhaar(f"{3 + (i % 6)}{229018473 + i * 251:010d}"[:11], sep="")
        surname_ch = name.split()[-1][0].upper()
        pan = f"KLMF{surname_ch}{3040 + i:04d}{'RSTUVWXYZABCDEF'[i % 15]}"
        voter = f"KAC{4501200 + i * 17:07d}"
        passport = f"P{7102400 + i * 23:07d}"
        gstin = make_gstin(state_code, pan)
        upi = f"{name.split()[0].lower()}{i+1}@okicici"

        segments = [
            ("ENTERPRISE E-KYC VERIFICATION RECORD\nCustomer ID: ", None),
            (f"CIF{880100 + i}", "CUSTOMER_ID"),
            ("\nAccount Holder Name: Mr. ", None),
            (name, "PERSON"),
            ("\nAadhaar UID: ", None),
            (aadhaar, "AADHAAR"),
            ("\nPAN: ", None),
            (pan, "PAN"),
            ("\nVoter ID (EPIC): ", None),
            (voter, "VOTER_ID"),
            ("\nPassport No: ", None),
            (passport, "PASSPORT"),
            ("\nGSTIN: ", None),
            (gstin, "GSTIN"),
            ("\nPermanent Address: ", None),
            (addr, "ADDRESS"),
            ("\nVerified UPI VPA: ", None),
            (upi, "UPI_ID"),
            ("\nRemarks: KYC status pending compliance sign-off for ", None),
            (name, "PERSON"),
            (".\n", None),
        ]
        d, a = build_annotated_doc(
            doc_id=doc_id,
            category="kyc_document",
            purpose="kyc_verification",
            title=f"Enterprise KYC Record #{i+1}",
            segments=segments,
        )
        docs.append(d)
        anns.extend(a)

    # 3. 10 Customer Support Tickets (including Hinglish / code-mixed & 1 negative example)
    for i in range(10):
        doc_id = f"SUP-{i+1:03d}"
        if i == 9:
            # Benign non-PII support ticket (negative control)
            segments = [
                (
                    "SUPPORT TICKET #99410\n"
                    "Subject: API Rate Limit Documentation Query\n"
                    "Message: Hello team, could you confirm the standard monthly SLA, "
                    "OAuth2 token expiry window, and invoice format for enterprise plans? "
                    "Reference Code: DOC-FAQ-2026. No personal customer details attached.\n",
                    None,
                )
            ]
        elif i % 2 == 0:
            name = _NAMES[(i + 7) % len(_NAMES)]
            addr = _ADDRESSES[(i + 4) % len(_ADDRESSES)]
            aadhaar = make_aadhaar(f"{4 + (i % 5)}{339104827 + i * 97:010d}"[:11], sep=" ")
            pan = f"BHKP{name.split()[-1][0].upper()}{5100 + i:04d}M"
            phone = f"+91-97{31004500 + i * 333:08d}"
            segments = [
                ("SUPPORT TICKET (HINGLISH)\nNamaste team, mera naam ", None),
                (name, "PERSON"),
                (" hai. Mera Aadhaar ", None),
                (aadhaar, "AADHAAR"),
                (" aur PAN ", None),
                (pan, "PAN"),
                (" KYC portal pe link nahi ho raha. Mera address: ", None),
                (addr, "ADDRESS"),
                (" hai. Please call me on ", None),
                (phone, "PHONE_NUMBER"),
                (". Note: Invalid ref 1000 0000 0000 ignore karein.\n", None),
            ]
        else:
            name = _NAMES[(i + 11) % len(_NAMES)]
            email = f"support.user{i}@corp-mail.in"
            voter = f"MHA{7821000 + i * 41:07d}"
            segments = [
                ("CUSTOMER SUPPORT ESCALATION\nComplainant Name: ", None),
                (name, "PERSON"),
                ("\nEmail: ", None),
                (email, "EMAIL_ADDRESS"),
                ("\nVoter ID submitted: ", None),
                (voter, "VOTER_ID"),
                ("\nIssue: Unable to update registered address to ", None),
                (_ADDRESSES[(i + 2) % len(_ADDRESSES)], "ADDRESS"),
                (".\n", None),
            ]
        d, a = build_annotated_doc(
            doc_id=doc_id,
            category="support_ticket",
            purpose="customer_support",
            title=f"Customer Support Ticket #{i+1}",
            segments=segments,
        )
        docs.append(d)
        anns.extend(a)

    # 4. 10 Insurance Claims (including 1 negative control)
    for i in range(10):
        doc_id = f"INS-{i+1:03d}"
        if i == 9:
            segments = [
                (
                    "INSURANCE POLICY GENERAL ENDORSEMENT FAQ\n"
                    "Cashless hospitalization pre-authorization requires hospital tariff sheet, "
                    "discharge summary template, and IRDAI network code NWP-402.\n",
                    None,
                )
            ]
        else:
            name = _NAMES[(i + 9) % len(_NAMES)]
            addr = _ADDRESSES[(i + 6) % len(_ADDRESSES)]
            aadhaar = make_aadhaar(f"{5 + (i % 4)}{618293045 + i * 193:010d}"[:11], sep="-")
            pan = f"DRTP{name.split()[-1][0].upper()}{7100 + i:04d}N"
            passport = f"J{8204100 + i * 19:07d}"
            phone = f"+91 99{12003400 + i * 211:08d}"
            acct = f"50100293{8100 + i:04d}"
            ifsc = f"HDFC000{1200 + i:04d}"
            segments = [
                ("HEALTH & MOTOR INSURANCE CLAIM FORM\nClaimant Name: ", None),
                (name, "PERSON"),
                ("\nPolicy No: ", None),
                (f"POL{202600 + i}", "CUSTOMER_ID"),
                ("\nAadhaar: ", None),
                (aadhaar, "AADHAAR"),
                (" | PAN: ", None),
                (pan, "PAN"),
                ("\nPassport Number: ", None),
                (passport, "PASSPORT"),
                ("\nAddress: ", None),
                (addr, "ADDRESS"),
                ("\nContact Mobile: ", None),
                (phone, "PHONE_NUMBER"),
                ("\nSettlement Bank A/c No: ", None),
                (acct, "BANK_ACCOUNT"),
                (" IFSC: ", None),
                (ifsc, "IFSC"),
                ("\nClaim Amount Requested: INR 1,85,000.\n", None),
            ]
        d, a = build_annotated_doc(
            doc_id=doc_id,
            category="insurance_claim",
            purpose="insurance_claims",
            title=f"Insurance Claim #{i+1}",
            segments=segments,
        )
        docs.append(d)
        anns.extend(a)

    return docs, anns


def main() -> None:
    docs, anns = generate_50_documents()
    docs_dir = REPO_ROOT / "dataset" / "synthetic_documents"
    anns_dir = REPO_ROOT / "dataset" / "annotations"
    docs_dir.mkdir(parents=True, exist_ok=True)
    anns_dir.mkdir(parents=True, exist_ok=True)

    (docs_dir / "indian_enterprise_50.json").write_text(
        json.dumps(docs, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (anns_dir / "ground_truth_50.json").write_text(
        json.dumps(anns, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"Generated {len(docs)} synthetic documents and {len(anns)} ground-truth annotations.")


if __name__ == "__main__":
    main()
