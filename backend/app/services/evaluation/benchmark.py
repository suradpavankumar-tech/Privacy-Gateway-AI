"""
=========================================================================================
benchmark.py — 50-Document Indian Enterprise Evaluation Benchmark Suite
=========================================================================================

Tech Stack:
 - Python 3.11+ / Dataclasses (Evaluation summary metrics and per-entity records)
 - SQLAlchemy (Audit & benchmark run persistence)
 - Statistical Metrics (Precision, Recall, F1-score, Zero-Leak validation)
 - In-Memory Isolated Vault (`fakeredis` for sandboxed evaluation execution)

Key Architectural Responsibilities:
 1. Standardized Corpus Evaluation:
    - Runs automated privacy and detection benchmarks against the 50-document Indian
      enterprise corpus (`indian-enterprise-50-v2.0`).
    - Spans property deeds, loan agreements, court petitions, and KYC identification forms.

 2. Span Alignment & IoU Metric Scoring:
    - Compares predicted entity boundaries with ground-truth spans using relaxed 60% IoU matching.
    - Aggregates True Positives (TP), False Positives (FP), and False Negatives (FN).

 3. Zero-Leak Verification & Telemetry:
    - Verifies that zero raw PII leaks across all benchmark documents.
    - Records microsecond latency statistics and entity-level performance breakdowns.
=========================================================================================
"""

from __future__ import annotations

import json
import uuid
from collections import defaultdict
from pathlib import Path
from typing import Any

import fakeredis
from sqlalchemy.orm import Session

from app.models.entities import EvaluationResult
from app.schemas.gateway import OutboundPayloadSchema, SecurityDecision, TokenizationMode
from app.services.detection.engine import (
    ALL_SUPPORTED_ENTITIES,
    MANDATORY_ENTITIES,
    get_detection_engine,
)
from app.services.privacy_vault.vault import PrivacyVault
from app.services.restoration.restorer import ResponseIntelligenceEngine
from app.services.security_gate.gate import OutboundSecurityGate
from app.services.tokenization.tokenizer import TokenizerEngine

DATASET_VERSION = "indian-enterprise-50-v2.0"


def _spans_match(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
    """Match if spans overlap by at least 60% of ground truth and 50% of predicted span."""
    inter = max(0, min(a_end, b_end) - max(a_start, b_start))
    if inter == 0:
        return False
    gt_len = max(1, b_end - b_start)
    pred_len = max(1, a_end - a_start)
    return (inter / gt_len) >= 0.6 and (inter / pred_len) >= 0.5


def resolve_dataset_dir() -> Path:
    candidates = [
        Path("/dataset"),
        Path(__file__).resolve().parents[4] / "dataset",
        Path(__file__).resolve().parents[3] / "dataset",
    ]
    for path in candidates:
        if (path / "synthetic_documents" / "indian_enterprise_50.json").exists():
            return path
    return candidates[1]


def load_dataset_corpus() -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
    dataset_dir = resolve_dataset_dir()
    docs_path = dataset_dir / "synthetic_documents" / "indian_enterprise_50.json"
    anns_path = dataset_dir / "annotations" / "ground_truth_50.json"

    docs = json.loads(docs_path.read_text(encoding="utf-8"))
    annotations = json.loads(anns_path.read_text(encoding="utf-8"))

    anns_by_doc: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for ann in annotations:
        anns_by_doc[ann["doc_id"]].append(ann)
    return docs, anns_by_doc


def run_benchmark_suite(
    db: Session | None = None,
    tokenization_mode: TokenizationMode = TokenizationMode.CRYPTOGRAPHIC_RANDOM,
    category_filter: str | None = None,
) -> dict[str, Any]:
    docs, anns_by_doc = load_dataset_corpus()
    if category_filter and category_filter != "all":
        docs = [d for d in docs if d.get("category") == category_filter]

    detector = get_detection_engine()
    detector.initialize()

    bench_redis = fakeredis.FakeRedis(decode_responses=False)
    bench_vault = PrivacyVault(redis_client=bench_redis)
    tokenizer = TokenizerEngine(vault=bench_vault)
    gate = OutboundSecurityGate()
    restorer = ResponseIntelligenceEngine(vault=bench_vault)

    tp_by_type: dict[str, int] = defaultdict(int)
    fp_by_type: dict[str, int] = defaultdict(int)
    fn_by_type: dict[str, int] = defaultdict(int)

    latencies_ms: list[float] = []
    outbound_leakage_count = 0

    reinsertion_total_tokens = 0
    reinsertion_correct_tokens = 0
    per_doc_results: list[dict[str, Any]] = []

    for doc in docs:
        doc_id = doc["doc_id"]
        text = doc["text"]
        gt_list = anns_by_doc.get(doc_id, [])

        detections, det_ms = detector.detect(text)
        latencies_ms.append(det_ms)

        doc_tp = 0
        doc_fp = 0
        doc_fn = 0
        matched_gt_indices: set[int] = set()
        for det in detections:
            matched_idx = None
            for idx, gt in enumerate(gt_list):
                if idx in matched_gt_indices:
                    continue
                if gt["entity_type"] == det.entity_type and _spans_match(
                    det.start, det.end, gt["start"], gt["end"]
                ):
                    matched_idx = idx
                    break
            if matched_idx is not None:
                matched_gt_indices.add(matched_idx)
                tp_by_type[det.entity_type] += 1
                doc_tp += 1
            else:
                fp_by_type[det.entity_type] += 1
                doc_fp += 1

        for idx, gt in enumerate(gt_list):
            if idx not in matched_gt_indices:
                fn_by_type[gt["entity_type"]] += 1
                doc_fn += 1

        req_id = f"bench-{doc_id}-{uuid.uuid4().hex[:6]}"
        tok_res = tokenizer.tokenize(
            org_id="bench-org",
            request_id=req_id,
            text=text,
            detections=detections,
            mode=tokenization_mode,
        )
        outbound = OutboundPayloadSchema(
            request_id=req_id,
            organization_id="bench-org",
            provider="gemini",
            model="gemini-3.8-flash",
            purpose=doc["purpose"],
            system_prompt="Summarize safely.",
            user_prompt=tok_res.sanitized_text,
        )
        gate_res = gate.inspect_and_authorize(
            payload=outbound,
            known_sensitive_values=[gt["expected_value"] for gt in gt_list],
            allowed_placeholders=[p.placeholder for p in tok_res.placeholders],
            policy_approved=True,
        )

        doc_leaks = 0
        outbound_lower = outbound.user_prompt.lower()
        for gt in gt_list:
            if gt["expected_value"].lower() in outbound_lower:
                outbound_leakage_count += 1
                doc_leaks += 1

        ph_list = [p.placeholder for p in tok_res.placeholders]
        doc_reinsertion_ok = True
        if ph_list:
            reversed_phs = list(reversed(ph_list))
            synthetic_llm_resp = (
                "Summary (paraphrased & reordered): Verified entities -> "
                + " | ".join(reversed_phs)
                + f". Repeated reference: {ph_list[0]}."
            )
            outcome = restorer.process_response(
                org_id="bench-org",
                request_id=req_id,
                response_text=synthetic_llm_resp,
                authorized_to_restore=True,
                restore_requested=True,
            )
            for ph in ph_list:
                reinsertion_total_tokens += 1
                expected_orig = tok_res.placeholder_to_original[ph]
                if expected_orig in outcome.final_text and ph not in outcome.final_text:
                    reinsertion_correct_tokens += 1
                else:
                    doc_reinsertion_ok = False

        per_doc_results.append(
            {
                "doc_id": doc_id,
                "title": doc.get("title", doc_id),
                "category": doc.get("category", "general"),
                "gt_count": len(gt_list),
                "detected_count": len(detections),
                "tp": doc_tp,
                "fp": doc_fp,
                "fn": doc_fn,
                "outbound_leaks": doc_leaks,
                "gate_decision": gate_res.decision.value,
                "reinsertion_passed": doc_reinsertion_ok,
                "latency_ms": det_ms,
            }
        )

    fail_closed_checks = 0
    fail_closed_passed = 0

    fail_closed_checks += 1
    tampered_payload = OutboundPayloadSchema(
        request_id="fc-1",
        organization_id="bench-org",
        provider="gemini",
        model="gemini-3.8-flash",
        purpose="loan_underwriting",
        system_prompt="System",
        user_prompt="Leaked PAN ABCDE1234F inside payload",
    )
    if gate.inspect_and_authorize(tampered_payload, known_sensitive_values=["ABCDE1234F"]).decision == SecurityDecision.FAIL:
        fail_closed_passed += 1

    fail_closed_checks += 1
    if gate.inspect_and_authorize(tampered_payload, policy_approved=None).decision == SecurityDecision.UNKNOWN:
        fail_closed_passed += 1

    fail_closed_checks += 1
    bad_prov_payload = OutboundPayloadSchema(
        request_id="fc-3",
        organization_id="bench-org",
        provider="untrusted_llm",
        model="x",
        purpose="loan_underwriting",
        system_prompt="System",
        user_prompt="Safe sanitized <PERSON_ABC123>",
    )
    if gate.inspect_and_authorize(bad_prov_payload).decision == SecurityDecision.FAIL:
        fail_closed_passed += 1

    entity_metrics: dict[str, dict[str, Any]] = {}
    total_tp = sum(tp_by_type.values())
    total_fp = sum(fp_by_type.values())
    total_fn = sum(fn_by_type.values())

    for ent in ALL_SUPPORTED_ENTITIES:
        tp = tp_by_type[ent]
        fp = fp_by_type[ent]
        fn = fn_by_type[ent]
        if tp == 0 and fp == 0 and fn == 0:
            continue
        prec = round(tp / (tp + fp), 4) if (tp + fp) > 0 else 0.0
        rec = round(tp / (tp + fn), 4) if (tp + fn) > 0 else 0.0
        f1 = round((2 * prec * rec) / (prec + rec), 4) if (prec + rec) > 0 else 0.0
        entity_metrics[ent] = {
            "tier": "mandatory" if ent in MANDATORY_ENTITIES else "extended",
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "precision": prec,
            "recall": rec,
            "f1": f1,
        }

    overall_prec = round(total_tp / (total_tp + total_fp), 4) if (total_tp + total_fp) > 0 else 0.0
    overall_rec = round(total_tp / (total_tp + total_fn), 4) if (total_tp + total_fn) > 0 else 0.0
    overall_f1 = (
        round((2 * overall_prec * overall_rec) / (overall_prec + overall_rec), 4)
        if (overall_prec + overall_rec) > 0
        else 0.0
    )
    reinsertion_acc = (
        round(reinsertion_correct_tokens / reinsertion_total_tokens, 4)
        if reinsertion_total_tokens > 0
        else 1.0
    )
    fail_closed_rate = round(fail_closed_passed / fail_closed_checks, 4)

    latencies_ms.sort()
    p50_ms = round(latencies_ms[len(latencies_ms) // 2], 2) if latencies_ms else 0.0
    p95_ms = round(latencies_ms[min(len(latencies_ms) - 1, int(0.95 * len(latencies_ms)))], 2) if latencies_ms else 0.0

    report = {
        "dataset_version": DATASET_VERSION,
        "detector_version": detector.VERSION,
        "tokenization_mode": tokenization_mode.value,
        "category_filter": category_filter or "all",
        "total_documents": len(docs),
        "total_ground_truth_entities": total_tp + total_fn,
        "overall_precision": overall_prec,
        "overall_recall": overall_rec,
        "overall_f1": overall_f1,
        "outbound_leakage_count": outbound_leakage_count,
        "reinsertion_accuracy": reinsertion_acc,
        "p50_latency_ms": p50_ms,
        "p95_latency_ms": p95_ms,
        "fail_closed_pass_rate": fail_closed_rate,
        "entity_metrics": entity_metrics,
        "per_doc_results": per_doc_results,
    }

    if db is not None and not category_filter:
        row = EvaluationResult(
            dataset_version=DATASET_VERSION,
            detector_version=detector.VERSION,
            total_documents=len(docs),
            overall_precision=overall_prec,
            overall_recall=overall_rec,
            overall_f1=overall_f1,
            outbound_leakage_count=outbound_leakage_count,
            reinsertion_accuracy=reinsertion_acc,
            p50_latency_ms=p50_ms,
            p95_latency_ms=p95_ms,
            fail_closed_pass_rate=fail_closed_rate,
            report_payload=report,
        )
        db.add(row)
        db.commit()

    return report
