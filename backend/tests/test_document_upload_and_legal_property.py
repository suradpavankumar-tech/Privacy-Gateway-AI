from __future__ import annotations

import io
from docx import Document

from app.services.detection.indian_validators import compute_verhoeff_check_digit
from app.services.documents.extractor import classify_uploaded_document


def _login(client, email: str, password: str) -> str:
    resp = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200
    return resp.json()["access_token"]


def _build_minimal_pdf(text_lines: list[str]) -> bytes:
    """Create a valid PDF 1.4 with Type1 Helvetica text stream readable by pypdf."""
    escaped = []
    for idx, line in enumerate(text_lines):
        safe = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        dy = "0" if idx == 0 else "-16"
        escaped.append(f"0 {dy} Td ({safe}) Tj")
    stream_body = "BT\n/F1 11 Tf\n50 750 Td\n" + "\n".join(escaped) + "\nET\n"
    stream_bytes = stream_body.encode("latin-1")

    objs = [
        b"1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n",
        b"2 0 obj\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\nendobj\n",
        b"3 0 obj\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>\nendobj\n",
        b"4 0 obj\n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>\nendobj\n",
        f"5 0 obj\n<< /Length {len(stream_bytes)} >>\nstream\n".encode("ascii")
        + stream_bytes
        + b"endstream\nendobj\n",
    ]
    buf = io.BytesIO()
    buf.write(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objs:
        offsets.append(buf.tell())
        buf.write(obj)
    xref_pos = buf.tell()
    buf.write(f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode("ascii"))
    for off in offsets[1:]:
        buf.write(f"{off:010d} 00000 n \n".encode("ascii"))
    buf.write(
        f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n".encode("ascii")
    )
    return buf.getvalue()


def test_classify_property_and_legal_documents():
    prop = classify_uploaded_document(
        "DEED OF SALE executed at Sub-Registrar Office. Survey No: 142/3A. Vendor: Ramesh Kulkarni.",
        "sale_deed.pdf",
    )
    assert prop.category == "property_document"
    assert prop.purpose == "property_verification"

    legal = classify_uploaded_document(
        "LEGAL NOTICE under Section 138. Petitioner: Sunita Rao vs Respondent. Jurisdiction: High Court.",
        "notice.docx",
    )
    assert legal.category == "legal_document"
    assert legal.purpose == "legal_review"


def test_upload_extract_and_process_property_pdf(client, stub_gemini):
    token = _login(client, "admin@bharatfin.in", "Admin@2026!")
    headers = {"Authorization": f"Bearer {token}"}
    aadhaar = "34567890123" + compute_verhoeff_check_digit("34567890123")

    pdf_bytes = _build_minimal_pdf(
        [
            "ABSOLUTE SALE DEED",
            "Sale Deed Reg No: BLR-HSR-04582-2025",
            "Khata No: 412/B",
            "Vendor: Ramesh Kulkarni",
            f"Vendor Aadhaar: {aadhaar[:4]} {aadhaar[4:8]} {aadhaar[8:12]}",
            "Vendee: Meenakshi Nair",
            "Vendee PAN: ABCPN5678K",
            "Property Address: Plot 42, Survey No 142, HSR Layout, Bengaluru, Karnataka - 560102",
        ]
    )

    ext_resp = client.post(
        "/api/v1/documents/extract",
        headers=headers,
        files={"file": ("property_sale_deed.pdf", pdf_bytes, "application/pdf")},
    )
    assert ext_resp.status_code == 200, ext_resp.text
    ext = ext_resp.json()
    assert ext["document"]["suggested_category"] == "property_document"
    assert ext["document"]["suggested_purpose"] == "property_verification"
    assert ext["document"]["page_count"] == 1
    assert ext["entity_count"] >= 5
    types = set(ext["detected_entity_counts"].keys())
    assert {"PERSON", "AADHAAR", "PAN", "ADDRESS", "PROPERTY_LEGAL_ID"}.issubset(types)

    proc_resp = client.post(
        "/api/v1/documents/process",
        headers=headers,
        files={"file": ("property_sale_deed.pdf", pdf_bytes, "application/pdf")},
        data={"tokenization_mode": "format_preserving", "restore_response": "true"},
    )
    assert proc_resp.status_code == 200, proc_resp.text
    body = proc_resp.json()
    gw = body["gateway_result"]
    assert gw["security_decision"] == "PASS"
    assert gw["raw_pii_leak_count"] == 0
    assert aadhaar[:4] + " " + aadhaar[4:8] + " " + aadhaar[8:12] not in gw["sanitized_outbound_payload"]
    assert "ABCPN5678K" not in gw["sanitized_outbound_payload"]
    assert "BLR-HSR-04582-2025" not in gw["sanitized_outbound_payload"]
    assert "ABCPN5678K" in (gw["final_response"] or "")


def test_upload_extract_and_process_legal_docx(client, stub_gemini):
    token = _login(client, "admin@bharatfin.in", "Admin@2026!")
    headers = {"Authorization": f"Bearer {token}"}

    doc = Document()
    doc.add_heading("LEGAL NOTICE UNDER ARBITRATION CLAUSE", level=1)
    doc.add_paragraph("CNR No: KABL01-004129-2025")
    doc.add_paragraph("Petitioner: Vikramaditya Rao")
    doc.add_paragraph("Respondent: Arjun Deshpande")
    doc.add_paragraph("Advocate: Kavita Menon | Bar Council No: KAR/4812/2014")
    doc.add_paragraph("Petitioner PAN: ABCPR9012L | Phone: +91 9845098450 | Email: vikram.rao@example.in")
    doc.add_paragraph("Jurisdiction: High Court of Karnataka. Claim amount INR 24,50,000 for breach of contract.")
    buf = io.BytesIO()
    doc.save(buf)
    docx_bytes = buf.getvalue()

    ext_resp = client.post(
        "/api/v1/documents/extract",
        headers=headers,
        files={
            "file": (
                "legal_arbitration_notice.docx",
                docx_bytes,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )
    assert ext_resp.status_code == 200, ext_resp.text
    ext = ext_resp.json()
    assert ext["document"]["suggested_category"] == "legal_document"
    assert ext["document"]["suggested_purpose"] == "legal_review"
    types = set(ext["detected_entity_counts"].keys())
    assert {"PERSON", "PAN", "PHONE_NUMBER", "EMAIL_ADDRESS", "PROPERTY_LEGAL_ID"}.issubset(types)

    proc_resp = client.post(
        "/api/v1/documents/process",
        headers=headers,
        files={
            "file": (
                "legal_arbitration_notice.docx",
                docx_bytes,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
        data={"tokenization_mode": "cryptographic_random", "provider": "local_slm"},
    )
    assert proc_resp.status_code == 200, proc_resp.text
    gw = proc_resp.json()["gateway_result"]
    assert gw["security_decision"] == "PASS"
    assert gw["purpose"] == "legal_review"
    assert "ABCPR9012L" not in gw["sanitized_outbound_payload"]
    assert "KAR/4812/2014" not in gw["sanitized_outbound_payload"]
    assert "ABCPR9012L" in (gw["final_response"] or "")


def test_rejects_unsupported_extension_and_empty_file(client):
    token = _login(client, "admin@bharatfin.in", "Admin@2026!")
    headers = {"Authorization": f"Bearer {token}"}

    bad_ext = client.post(
        "/api/v1/documents/extract",
        headers=headers,
        files={"file": ("payload.exe", b"MZ...", "application/octet-stream")},
    )
    assert bad_ext.status_code == 400

    empty_txt = client.post(
        "/api/v1/documents/extract",
        headers=headers,
        files={"file": ("empty.txt", b"   ", "text/plain")},
    )
    assert empty_txt.status_code == 400


def test_real_world_property_deed_tables_honorifics_and_problem_statement(client, stub_gemini):
    token = _login(client, "admin@bharatfin.in", "Admin@2026!")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Problem statement containing 'mandatory'/'standard', literal example placeholders
    # (<PERSON_1>, <AADHAAR_1>, etc.), and ML headings ('NER Model', 'Small Language Model')
    # must pass Security Gate cleanly without false unregistered-token blocks.
    ps_text = (
        "PROBLEM STATEMENT PS-02: Enterprise Privacy Gateway AI\n"
        "Mandatory entities must be masked as <PERSON_1>, <AADHAAR_1>, <PAN_1>, <ADDRESS_1>, "
        "<GSTIN_1>, <VOTER_ID_1>, <PASSPORT_1> using NER Model or Small Language Model.\n"
        "Example Input: Applicant Name: Rajesh Kumar | PAN: ABCPK1234M\n"
        "Architectural section: Enterprise Privacy Gateway ensures zero outbound leak in mandatory flows.\n"
        "In the mandatory flow, NER model and Small Language Model avoid standard false positives.\n"
    ).encode("utf-8")
    ps_resp = client.post(
        "/api/v1/documents/process",
        headers=headers,
        files={"file": ("problem_statement.txt", ps_text, "text/plain")},
        data={"provider": "local_slm", "restore_response": "true"},
    )
    assert ps_resp.status_code == 200, ps_resp.text
    ps_body = ps_resp.json()
    assert ps_body["document"]["suggested_category"] == "general_document"
    assert ps_body["gateway_result"]["security_decision"] == "PASS"
    assert ps_body["gateway_result"]["raw_pii_leak_count"] == 0

    # 2. Multi-party Indian Property Agreement with Marathi honorifics (Sou./Shri.), no-space dots,
    # 3+3 spaced PIN code, ALL-CAPS labeled name, Survey No Area table header, and repeated 85/1.
    deed_lines = [
        "AGREEMENT TO SELL UNIT",
        "Office at: 9, Siddhivinayak, Golibar Maidan Chowk, Camp, Pune: 411 001",
        "Partner Rajeshkumar Naupatlal Sakla | PAN: AAVFS4918C",
        "Name: MR. AVIRAJ SINGH | PAN: ARUPS2665N",
        "Residing At: E-402, Park Royale, Sr. No. 14, Rahatani, Pune - 411 017",
        "1)Shri. Shivaji Parghale, 2)Sou.Sakhubai Parghale, 3)Smt. Ratnabai Parghale",
        "Balance Land and Said Balance building carpet area 412 Sq.fts.",
        "Survey No Area Sq.mts. | 1 85/1 800 08",
        "Clause 4: Survey No: 85/1 verified. Partner Rajeshkumar Naupatlal Sakla confirms balance land schedule.",
    ]
    pdf_bytes = _build_minimal_pdf(deed_lines)
    deed_resp = client.post(
        "/api/v1/documents/process",
        headers=headers,
        files={"file": ("agreement_to_sell.pdf", pdf_bytes, "application/pdf")},
        data={"provider": "local_slm", "restore_response": "true"},
    )
    assert deed_resp.status_code == 200, deed_resp.text
    deed_gw = deed_resp.json()["gateway_result"]
    assert deed_gw["security_decision"] == "PASS", deed_gw["security_reason"]
    assert deed_gw["raw_pii_leak_count"] == 0
    assert "AVIRAJ SINGH" not in deed_gw["sanitized_outbound_payload"]
    assert "Shivaji Parghale" not in deed_gw["sanitized_outbound_payload"]
    assert "Sakhubai Parghale" not in deed_gw["sanitized_outbound_payload"]
    assert "411 001" not in deed_gw["sanitized_outbound_payload"]
    assert "85/1" not in deed_gw["sanitized_outbound_payload"]


def _render_test_document_image(lines: list[str], fmt: str = "PNG") -> bytes:
    from PIL import Image, ImageDraw, ImageFont

    font_candidates = [
        r"C:\Windows\Fonts\arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    font = None
    for path in font_candidates:
        try:
            font = ImageFont.truetype(path, 26)
            break
        except OSError:
            continue
    if font is None:
        font = ImageFont.load_default(size=24)

    height = 80 + len(lines) * 54
    img = Image.new("RGB", (1180, height), "white")
    draw = ImageDraw.Draw(img)
    y = 32
    for line in lines:
        draw.text((36, y), line, fill="black", font=font)
        y += 52

    buf = io.BytesIO()
    if fmt.upper() == "JPEG":
        img.save(buf, format="JPEG", quality=95)
    elif fmt.upper() == "PDF":
        img.save(buf, format="PDF", resolution=150.0)
    else:
        img.save(buf, format="PNG")
    return buf.getvalue()


def test_ocr_extracts_pii_from_png_image(client):
    token = _login(client, "admin@bharatfin.in", "Admin@2026!")
    headers = {"Authorization": f"Bearer {token}"}
    aadhaar = "34567890123" + compute_verhoeff_check_digit("34567890123")
    formatted_aadhaar = f"{aadhaar[:4]} {aadhaar[4:8]} {aadhaar[8:12]}"

    png_bytes = _render_test_document_image(
        [
            "RETAIL HOME LOAN KYC FORM",
            "Applicant Name: Rajeshwar Rao",
            f"Aadhaar: {formatted_aadhaar}",
            "PAN Number: ABCPK5678K",
            "GSTIN: 27ABCPK5678K1Z5",
            "Mobile: +91 9845011223 | Email: rajesh@example.in",
            "Address: Plot 42, HSR Layout, Bengaluru - 560102",
        ],
        fmt="PNG",
    )

    resp = client.post(
        "/api/v1/documents/extract",
        headers=headers,
        files={"file": ("kyc_card_scan.png", png_bytes, "image/png")},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    doc = body["document"]
    assert doc["ocr_used"] is True
    assert doc["extraction_method"] == "rapidocr-onnxruntime"
    assert (doc["ocr_confidence"] or 0.0) >= 0.75
    assert (doc["ocr_line_count"] or 0) >= 5
    assert doc["image_dimensions"]
    assert doc["suggested_category"] in {"loan_application", "kyc_document"}

    types = set(body["detected_entity_counts"].keys())
    assert {"AADHAAR", "PAN", "GSTIN", "PHONE_NUMBER", "EMAIL_ADDRESS", "PERSON", "ADDRESS"}.issubset(
        types
    ), f"Detected types: {types} | Extracted text:\n{body['extracted_text']}"


def test_ocr_process_jpeg_property_scan_and_scanned_pdf(client, stub_gemini):
    token = _login(client, "admin@bharatfin.in", "Admin@2026!")
    headers = {"Authorization": f"Bearer {token}"}
    aadhaar = "45678901234" + compute_verhoeff_check_digit("45678901234")
    formatted_aadhaar = f"{aadhaar[:4]} {aadhaar[4:8]} {aadhaar[8:12]}"

    deed_lines = [
        "ABSOLUTE SALE DEED",
        "Sale Deed Reg No: BLR-HSR-04582-2025",
        "Vendor: Ramesh Kulkarni",
        f"Vendor Aadhaar: {formatted_aadhaar}",
        "Vendee: Meenakshi Nair",
        "Vendee PAN: ABCPN5678K",
        "Property Address: Plot 42, Survey No 142, HSR Layout, Bengaluru - 560102",
    ]
    jpg_bytes = _render_test_document_image(deed_lines, fmt="JPEG")
    proc_resp = client.post(
        "/api/v1/documents/process",
        headers=headers,
        files={"file": ("sale_deed_scan.jpg", jpg_bytes, "image/jpeg")},
        data={"tokenization_mode": "cryptographic_random", "provider": "local_slm", "restore_response": "true"},
    )
    assert proc_resp.status_code == 200, proc_resp.text
    body = proc_resp.json()
    assert body["document"]["ocr_used"] is True
    assert body["document"]["suggested_category"] == "property_document"
    gw = body["gateway_result"]
    assert gw["security_decision"] == "PASS", gw["security_reason"]
    assert gw["raw_pii_leak_count"] == 0
    assert "ABCPN5678K" not in gw["sanitized_outbound_payload"]
    assert aadhaar not in gw["sanitized_outbound_payload"].replace(" ", "")
    assert "ABCPN5678K" in (gw["final_response"] or "")

    # Scanned image-only PDF (no selectable text layer) must fall back to pypdfium2+rapidocr
    scanned_pdf_bytes = _render_test_document_image(deed_lines, fmt="PDF")
    pdf_resp = client.post(
        "/api/v1/documents/extract",
        headers=headers,
        files={"file": ("scanned_deed.pdf", scanned_pdf_bytes, "application/pdf")},
    )
    assert pdf_resp.status_code == 200, pdf_resp.text
    pdf_body = pdf_resp.json()
    assert pdf_body["document"]["ocr_used"] is True
    assert pdf_body["document"]["extraction_method"] == "pypdfium2+rapidocr"
    assert pdf_body["document"]["page_count"] == 1
    assert {"AADHAAR", "PAN", "PROPERTY_LEGAL_ID"}.issubset(
        set(pdf_body["detected_entity_counts"].keys())
    )

    bad_img = client.post(
        "/api/v1/documents/extract",
        headers=headers,
        files={"file": ("corrupt.png", b"not-a-valid-png", "image/png")},
    )
    assert bad_img.status_code == 400
