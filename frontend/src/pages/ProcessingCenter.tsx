/**
 * ==============================================================================
 * Privacy Gateway AI (MINEARENA PS-02) — Privacy Processing Studio & Workbench
 * ==============================================================================
 * Tech Stack:
 *  - React 19 + TypeScript (useMemo, useRef, useState, useEffect)
 *  - Tailwind CSS: Clean enterprise white cards, pastel badges, monospace viewers
 *  - Lucide React: Action, entity, and security state icons
 *  - RapidOCR / PDF/DOCX Parser Integration: Multimodal document text extraction
 *  - Client Exporters: PDF & JSON DPDP Compliance Certificates & Sanitized Texts
 *
 * Core Capabilities:
 *  1. Interactive Scenario Presets: Home Loan, Hinglish KYC, Policy Block, Outage Fallback,
 *     Forged Token injection, and Property / Legal contracts.
 *  2. Multimodal Dropzone: Drag-and-drop intake for PDF, DOCX, TXT, CSV, and image OCR.
 *  3. Safety Character Counter: Live `chars / 120,000` limit check to prevent payload overflow.
 *  4. 3-Panel Inspection Workbench:
 *     - Panel A: Source Document with interactive Raw / Highlighted Entity Spans.
 *     - Panel B: Outbound Gate (7 itemized checks), zero-PII sanitized text, AES vault proof,
 *       and 1-click Download Sanitized Doc & PDF Compliance Certificate.
 *     - Panel C: End-to-end execution trace, RBAC unmasking statistics, and structured
 *       Property/Legal analysis cards (Parties, IDs, Financials, Risks).
 * ==============================================================================
 */

import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  AlertTriangle,
  BarChart3,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Copy,
  Cpu,
  Database,
  Download,
  FileCheck2,
  FileJson,
  FileText,
  FileUp,
  FlaskConical,
  Hash,
  IndianRupee,
  KeyRound,
  Lock,
  Play,
  RotateCcw,
  Scale,
  ScanSearch,
  ScanText,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  UploadCloud,
  Users,
  X,
  XCircle,
} from "lucide-react";
import { DocumentEvaluationMetrics } from "../components/DocumentEvaluationMetrics";
import { PipelineVisualizer } from "../components/PipelineVisualizer";
import { api, ApiError } from "../services/api";
import {
  downloadComplianceCertificateJson,
  downloadComplianceCertificatePdf,
  downloadSanitizedDocument,
  parseStructuredAnalysisSections,
  type AnalysisCardSection,
} from "../utils/exportHelpers";
import type {
  DatasetDocument,
  DetectedEntity,
  DocumentEvaluationReport,
  DocumentUploadMeta,
  ProcessResponse,
  TokenizationMode,
  UserProfile,
} from "../types/api";

interface JudgeScenario {
  id: string;
  shortLabel: string;
  label: string;
  badge: string;
  tone: "emerald" | "sky" | "amber" | "rose";
  text: string;
  task: string;
  purpose: string;
  category: string;
  mode: TokenizationMode;
  provider: string;
  simulateTampered?: boolean;
  simulateOffline?: boolean;
  simulateForged?: boolean;
}

const JUDGE_SCENARIOS: JudgeScenario[] = [
  {
    id: "loan-default",
    shortLabel: "Home Loan",
    label: "1. Retail Home Loan",
    badge: "Standard Flow",
    tone: "emerald",
    purpose: "loan_underwriting",
    category: "loan_application",
    mode: "cryptographic_random",
    provider: "gemini",
    task: "Summarize this loan application, verify disbursement readiness, and list key underwriting items while preserving all placeholder tokens verbatim.",
    text: `RETAIL HOME LOAN APPLICATION\nApplicant Name: Vikramaditya Kulkarni\nDOB: 14/05/1988\nAadhaar Number: 5678 9012 3456\nPAN Number: ABCPK5678R\nResidential Address: Plot 27, Shanti Niketan Colony, Kothrud, Pune, Maharashtra - 411038\nMobile: +91 9845012300 | Email: vikram.kulkarni@example.in\nDisbursement Bank A/c No: 304958102900 (IFSC: SBIN0004100)\nDeclaration: I, Vikramaditya Kulkarni, confirm my PAN ABCPK5678R for loan sanction of INR 24,50,000.`,
  },
  {
    id: "hinglish-support",
    shortLabel: "Hinglish KYC",
    label: "2. Hinglish Support + Invalid Ref",
    badge: "Code-Mixed",
    tone: "sky",
    purpose: "customer_support",
    category: "support_ticket",
    mode: "typed_sequential",
    provider: "gemini",
    task: "Triage this Hinglish escalation and draft next support steps keeping every placeholder intact.",
    text: `SUPPORT TICKET (HINGLISH)\nNamaste team, mera naam Aarav Sharma hai. Mera Aadhaar 4339 1048 2714 aur PAN BHKPS5100M KYC portal pe link nahi ho raha.\nMera address: Flat 402, Sai Krupa Residency, 4th Main, Vidyanagar, Davangere, Karnataka - 577005 hai.\nPlease call me on +91-9731004500. Note: Invalid ref 1000 0000 0000 ignore karein.`,
  },
  {
    id: "policy-block",
    shortLabel: "Policy Block",
    label: "3. Marketing Strict Block",
    badge: "Policy Block",
    tone: "rose",
    purpose: "marketing_analytics",
    category: "kyc_document",
    mode: "cryptographic_random",
    provider: "gemini",
    task: "Extract campaign segmentation metrics from this KYC document.",
    text: `ENTERPRISE E-KYC VERIFICATION RECORD\nAccount Holder Name: Mr. Suresh Reddy\nAadhaar UID: 322901847302\nPAN: KLMFR3040R\nPassport No: P7102400\nPermanent Address: House No. 18-4-212, Jubilee Hills Road No. 12, Hyderabad, Telangana - 500033`,
  },
  {
    id: "tamper-attack",
    shortLabel: "Leak Tamper",
    label: "4. Outbound Leak Tamper",
    badge: "Gate FAIL",
    tone: "rose",
    purpose: "loan_underwriting",
    category: "loan_application",
    mode: "format_preserving",
    provider: "local_slm",
    simulateTampered: true,
    task: "Underwrite this applicant and verify PAN credit score.",
    text: `URGENT CREDIT CARD DISBURSEMENT\nName: Deepa Nambiar\nAadhaar: 9012 3456 7890\nPAN: BZVPN1234K\nPhone: +91 9448123456\nAddress: Flat 102, Palm Meadows, Whitefield, Bengaluru, Karnataka - 560066`,
  },
  {
    id: "offline-fallback",
    shortLabel: "SLM Fallback",
    label: "5. Cloud Outage → SLM Fallback",
    badge: "Fallback Proof",
    tone: "amber",
    purpose: "loan_underwriting",
    category: "loan_application",
    mode: "cryptographic_random",
    provider: "gemini",
    simulateOffline: true,
    task: "Evaluate this SME loan application during cloud LLM outage and preserve all tokens verbatim.",
    text: `SME WORKING CAPITAL APPLICATION\nCompany: Bharat Forge Solutions\nProprietor: Rameshwar Sen\nAadhaar: 4123 4567 8901\nPAN: ABCPS4321M\nGSTIN: 29ABCDE1234F1Z5\nRegistered Office: Plot 14, Peenya Industrial Area Phase 2, Bengaluru, Karnataka - 560058\nMobile: +91 9886012345\nRequested Loan: INR 50,00,000`,
  },
  {
    id: "forged-token",
    shortLabel: "Forged Token",
    label: "6. Forged LLM Injection Guard",
    badge: "Post-LLM Guard",
    tone: "rose",
    purpose: "customer_support",
    category: "support_ticket",
    mode: "cryptographic_random",
    provider: "local_slm",
    simulateForged: true,
    task: "Triage this support ticket and test gate against hallucinated placeholder tokens.",
    text: `SUPPORT ESCALATION\nUser: Kavita Nair\nPhone: +91 9742012345\nEmail: kavita.nair@example.com\nIssue: Address update verification pending since 3 days.`,
  },
  {
    id: "property-deed",
    shortLabel: "Sale Deed",
    label: "7. Sale Deed & Encumbrance",
    badge: "Property Doc",
    tone: "emerald",
    purpose: "property_verification",
    category: "property_document",
    mode: "format_preserving",
    provider: "gemini",
    task: "Analyze this property deed into 4 structured sections — 1. Ownership Chain / Parties, 2. Deed, Survey & CNR IDs, 3. Financial Consideration & Deadlines, and 4. Risk & Red-Flag Clauses — while preserving every masked token verbatim.",
    text: `DEED OF ABSOLUTE SALE\nSale Deed Reg No: BLR-BMH-08421-2025-26 | Khata No: KHT-412/B | Survey No: SY-142/3A\nVendor: Shri Rajeshwar Rao | Aadhaar: 3456 7890 1236 | PAN: ABCPR4512D\nVendee: Smt. Meenakshi Nair | PAN: ABCPN7834M | Mobile: +91 9845011223\nProperty Address: Plot 42, 4th Cross, HSR Layout Sector 2, Bengaluru, Karnataka - 560102\nConsideration Value: INR 1,45,00,000 paid via RTGS with Nil Encumbrance Certificate.`,
  },
  {
    id: "legal-notice",
    shortLabel: "Legal Notice",
    label: "8. Legal Arbitration Notice",
    badge: "Legal Doc",
    tone: "sky",
    purpose: "legal_review",
    category: "legal_document",
    mode: "cryptographic_random",
    provider: "gemini",
    task: "Analyze this legal notice into 4 structured sections — 1. Ownership Chain / Parties, 2. Deed, Survey & CNR IDs, 3. Financial Consideration & Deadlines, and 4. Risk & Red-Flag Clauses — while preserving every masked token verbatim.",
    text: `LEGAL NOTICE UNDER SECTION 138 & ARBITRATION CLAUSE\nCNR No: KABL01-004129-2025 | Suit No: 412/2025\nPetitioner: Vikramaditya Menon | PAN: ABCPM9012L | Phone: +91 9880123456\nPetitioner Address: Flat 12B, Embassy Heritage, Malleshwaram, Bengaluru, Karnataka - 560055\nRespondent: Horizon Buildcon LLP | GSTIN: 29ABCFH1234M1Z5\nAdvocate: Adv. Kavita Deshpande | Bar Council No: KAR/4812/2014 | Email: kavita.adv@example.in\nClaim Amount: INR 38,75,000 security deposit refund within 15 days under Lease Clause 14(b).`,
  },
];

const TIER_STYLES: Record<string, string> = {
  AADHAAR: "bg-rose-50 text-rose-800 border-rose-200",
  PAN: "bg-amber-50 text-amber-800 border-amber-200",
  GSTIN: "bg-orange-50 text-orange-800 border-orange-200",
  PERSON: "bg-blue-50 text-blue-800 border-blue-200",
  ADDRESS: "bg-indigo-50 text-indigo-800 border-indigo-200",
  PASSPORT: "bg-fuchsia-50 text-fuchsia-800 border-fuchsia-200",
  VOTER_ID: "bg-purple-50 text-purple-800 border-purple-200",
  PROPERTY_LEGAL_ID: "bg-teal-50 text-teal-800 border-teal-200",
};

const TONE_DOTS: Record<JudgeScenario["tone"], string> = {
  emerald: "bg-emerald-500",
  sky: "bg-blue-500",
  amber: "bg-amber-500",
  rose: "bg-rose-500",
};

function renderHighlightedText(text: string, detections: DetectedEntity[]): React.ReactNode {
  if (!detections.length) return text;
  const sorted = [...detections].sort((a, b) => a.start - b.start);
  const nodes: React.ReactNode[] = [];
  let cursor = 0;

  sorted.forEach((d, idx) => {
    const start = Math.max(cursor, d.start);
    if (d.end <= start) return;
    if (start > cursor) {
      nodes.push(<span key={`t-${idx}`}>{text.slice(cursor, start)}</span>);
    }
    const cls = TIER_STYLES[d.entity_type] || "bg-emerald-50 text-emerald-800 border-emerald-200";
    nodes.push(
      <mark
        key={`m-${idx}`}
        title={`${d.entity_type} (${d.recognizer}, conf=${Math.round(d.confidence * 100)}%)`}
        className={`inline-flex items-baseline gap-1 px-1.5 py-0.5 rounded-md border text-xs font-mono font-medium ${cls}`}
      >
        <span>{text.slice(start, d.end)}</span>
        <span className="text-[9px] uppercase font-bold opacity-80">{d.entity_type}</span>
      </mark>
    );
    cursor = d.end;
  });
  if (cursor < text.length) {
    nodes.push(<span key="tail">{text.slice(cursor)}</span>);
  }
  return nodes;
}

const SwitchPill: React.FC<{
  checked: boolean;
  onChange: (next: boolean) => void;
  label: string;
  tone?: "emerald" | "amber" | "rose" | "fuchsia" | "sky";
  title?: string;
}> = ({ checked, onChange, label, tone = "emerald", title }) => {
  const toneMap = {
    emerald: {
      activeBg: "bg-emerald-50 border-emerald-300 text-emerald-800",
      track: "bg-emerald-500",
    },
    sky: {
      activeBg: "bg-blue-50 border-blue-300 text-blue-800",
      track: "bg-blue-500",
    },
    amber: {
      activeBg: "bg-amber-50 border-amber-300 text-amber-800",
      track: "bg-amber-500",
    },
    rose: {
      activeBg: "bg-rose-50 border-rose-300 text-rose-800",
      track: "bg-rose-500",
    },
    fuchsia: {
      activeBg: "bg-purple-50 border-purple-300 text-purple-800",
      track: "bg-purple-500",
    },
  }[tone];

  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      title={title}
      onClick={() => onChange(!checked)}
      className={`inline-flex items-center gap-2 px-2.5 py-1 rounded-xl border text-[11px] font-semibold transition cursor-pointer select-none shadow-2xs ${
        checked
          ? toneMap.activeBg
          : "bg-white border-slate-200 text-slate-600 hover:text-slate-900 hover:border-slate-300 hover:bg-slate-50"
      }`}
    >
      <span
        className={`relative inline-flex h-3.5 w-6 shrink-0 items-center rounded-full transition-colors ${
          checked ? toneMap.track : "bg-slate-300"
        }`}
      >
        <span
          className={`inline-block h-2.5 w-2.5 transform rounded-full bg-white shadow-xs transition-transform ${
            checked ? "translate-x-3" : "translate-x-0.5"
          }`}
        />
      </span>
      <span className="whitespace-nowrap">{label}</span>
    </button>
  );
};

const CopyButton: React.FC<{ value: string; label?: string }> = ({ value, label }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(value);
      setCopied(true);
      setTimeout(() => setCopied(false), 1600);
    } catch {
      // Ignore clipboard write restrictions
    }
  };

  return (
    <button
      type="button"
      onClick={handleCopy}
      className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-[10px] font-semibold text-slate-700 hover:text-slate-900 transition shadow-2xs cursor-pointer"
    >
      {copied ? <Check className="w-3 h-3 text-emerald-600" /> : <Copy className="w-3 h-3 text-slate-500" />}
      <span>{copied ? "Copied" : label || "Copy"}</span>
    </button>
  );
};

interface ProcessingCenterProps {
  user: UserProfile;
  loadedDocument?: DatasetDocument | null;
  onClearLoadedDocument?: () => void;
  searchFilter?: string;
}

export const ProcessingCenter: React.FC<ProcessingCenterProps> = ({
  user,
  loadedDocument,
  onClearLoadedDocument,
  searchFilter = "",
}) => {
  const [samples, setSamples] = useState<DatasetDocument[]>([]);
  const [activeScenarioId, setActiveScenarioId] = useState<string | null>(JUDGE_SCENARIOS[0].id);
  const [text, setText] = useState(JUDGE_SCENARIOS[0].text);
  const [task, setTask] = useState(JUDGE_SCENARIOS[0].task);
  const [purpose, setPurpose] = useState(JUDGE_SCENARIOS[0].purpose);
  const [category, setCategory] = useState(JUDGE_SCENARIOS[0].category);
  const [mode, setMode] = useState<TokenizationMode>(JUDGE_SCENARIOS[0].mode);
  const [provider, setProvider] = useState(JUDGE_SCENARIOS[0].provider);
  const [restoreResponse, setRestoreResponse] = useState(true);
  const [enableFallback, setEnableFallback] = useState(true);

  const [simulateOffline, setSimulateOffline] = useState(false);
  const [simulateTampered, setSimulateTampered] = useState(false);
  const [simulateForged, setSimulateForged] = useState(false);
  const [showRedTeam, setShowRedTeam] = useState(false);

  const [highlightMode, setHighlightMode] = useState(false);
  const [showVaultProof, setShowVaultProof] = useState(true);
  const [outputView, setOutputView] = useState<"cards" | "summary" | "raw">("cards");

  const [loading, setLoading] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [autoRunOnUpload, setAutoRunOnUpload] = useState(true);
  const [isDragOver, setIsDragOver] = useState(false);
  const [uploadedDocMeta, setUploadedDocMeta] = useState<DocumentUploadMeta | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [detectionsPreview, setDetectionsPreview] = useState<DetectedEntity[]>([]);
  const [result, setResult] = useState<ProcessResponse | null>(null);
  const [lastRequestedProvider, setLastRequestedProvider] = useState<string>(JUDGE_SCENARIOS[0].provider);

  const [evalReport, setEvalReport] = useState<DocumentEvaluationReport | null>(null);
  const [evaluatingDoc, setEvaluatingDoc] = useState(false);
  const [showEvalMetrics, setShowEvalMetrics] = useState(true);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  useEffect(() => {
    api.datasetSamples().then(setSamples).catch(() => {});
  }, []);

  useEffect(() => {
    if (loadedDocument) {
      setActiveScenarioId(null);
      setText(loadedDocument.text);
      setPurpose(loadedDocument.purpose);
      setCategory(loadedDocument.category);
      setUploadedDocMeta(null);
      setTask(
        "Summarize this enterprise record, list verification obligations, and preserve every masked placeholder verbatim."
      );
      setResult(null);
      setDetectionsPreview([]);
      setHighlightMode(false);
      onClearLoadedDocument?.();
    }
  }, [loadedDocument, onClearLoadedDocument]);

  const activeSimCount =
    Number(simulateOffline) + Number(simulateTampered) + Number(simulateForged);

  const applyScenario = (sc: JudgeScenario) => {
    const nextOffline = Boolean(sc.simulateOffline);
    const nextTampered = Boolean(sc.simulateTampered);
    const nextForged = Boolean(sc.simulateForged);
    setActiveScenarioId(sc.id);
    setText(sc.text);
    setTask(sc.task);
    setPurpose(sc.purpose);
    setCategory(sc.category);
    setMode(sc.mode);
    setProvider(sc.provider);
    setSimulateTampered(nextTampered);
    setSimulateOffline(nextOffline);
    setSimulateForged(nextForged);
    if (nextOffline || nextTampered || nextForged) {
      setShowRedTeam(true);
    }
    setUploadedDocMeta(null);
    setResult(null);
    setOutputView("cards");
    setDetectionsPreview([]);
    setHighlightMode(false);
    setError(null);
  };

  const canSubmit = user.permissions.includes("process:submit");

  const handleFileUpload = async (file: File) => {
    setError(null);
    setUploading(true);
    setSelectedFile(file);
    try {
      const extracted = await api.extractDocument(file);
      setUploadedDocMeta(extracted.document);
      setText(extracted.extracted_text);
      setActiveScenarioId(null);
      setResult(null);
      setDetectionsPreview(extracted.detections || []);
      setHighlightMode(false);

      if (extracted.document.suggested_category) {
        setCategory(extracted.document.suggested_category);
      }
      if (extracted.document.suggested_purpose) {
        setPurpose(extracted.document.suggested_purpose);
      }

      if (
        extracted.document.suggested_category === "property_document" ||
        extracted.document.suggested_category === "legal_document"
      ) {
        setTask(
          "Analyze this document into 4 structured sections — 1. Ownership Chain / Parties, 2. Deed, Survey & CNR IDs, 3. Financial Consideration & Deadlines, and 4. Risk & Red-Flag Clauses — while preserving every masked token verbatim."
        );
      }

      setEvaluatingDoc(true);
      api
        .evaluateDocument(file)
        .then((rep) => {
          setEvalReport(rep);
          setShowEvalMetrics(true);
        })
        .catch((err) => {
          console.warn("Auto-evaluate uploaded doc failed (using local metrics fallback):", err);
        })
        .finally(() => {
          setEvaluatingDoc(false);
        });

      if (autoRunOnUpload && canSubmit) {
        setTimeout(async () => {
          setLoading(true);
          setLastRequestedProvider(provider);
          try {
            const res = await api.process({
              text: extracted.extracted_text,
              task,
              document_category: extracted.document.suggested_category || category,
              purpose: extracted.document.suggested_purpose || purpose,
              tokenization_mode: mode,
              provider,
              restore_response: restoreResponse,
              enable_fallback: enableFallback,
              simulate_tampered_outbound: simulateTampered,
              simulate_provider_offline: simulateOffline,
              simulate_forged_token: simulateForged,
            });
            setResult(res);
            setOutputView("cards");
            setDetectionsPreview(res.detections);
            setHighlightMode(true);
          } catch (runErr) {
            setError(runErr instanceof ApiError ? runErr.message : "Auto-run failed");
          } finally {
            setLoading(false);
          }
        }, 150);
      }
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Document upload / OCR extraction failed");
    } finally {
      setUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const handleReevaluate = async (file: File) => {
    setEvaluatingDoc(true);
    try {
      const rep = await api.evaluateDocument(file);
      setEvalReport(rep);
      setShowEvalMetrics(true);
    } catch (err) {
      console.warn("Re-evaluate document failed:", err);
    } finally {
      setEvaluatingDoc(false);
    }
  };

  const handleAnalyzeOnly = async () => {
    setError(null);
    setAnalyzing(true);
    try {
      const res = await api.analyze(text, purpose, category);
      setDetectionsPreview(res.detections);
      setHighlightMode(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Local analysis failed");
    } finally {
      setAnalyzing(false);
    }
  };

  const handleExecutePipeline = async () => {
    setError(null);
    if (text.length > 120000) {
      setError(
        `Document payload (${text.length.toLocaleString()} characters) exceeds the maximum allowed gateway limit of 120,000 characters. Please truncate or split the text.`
      );
      return;
    }
    setLastRequestedProvider(provider);
    setLoading(true);
    try {
      const res = await api.process({
        text,
        task,
        document_category: category,
        purpose,
        tokenization_mode: mode,
        provider,
        restore_response: restoreResponse,
        enable_fallback: enableFallback,
        simulate_tampered_outbound: simulateTampered,
        simulate_provider_offline: simulateOffline,
        simulate_forged_token: simulateForged,
      });
      setResult(res);
      setOutputView("cards");
      setDetectionsPreview(res.detections);
      setHighlightMode(true);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Gateway execution error");
    } finally {
      setLoading(false);
    }
  };

  const activeDetections = result?.detections ?? detectionsPreview;

  const entityBreakdown = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const d of activeDetections) {
      counts[d.entity_type] = (counts[d.entity_type] || 0) + 1;
    }
    return Object.entries(counts).sort((a, b) => b[1] - a[1]);
  }, [activeDetections]);

  const activeResponseText =
    outputView === "raw" && result?.raw_llm_response
      ? result.raw_llm_response
      : result?.final_response ?? "Blocked locally before reaching LLM provider.";

  const structuredSections = useMemo(
    () => parseStructuredAnalysisSections(activeResponseText),
    [activeResponseText]
  );

  const effectiveOutputView =
    outputView === "cards" && structuredSections.length === 0 ? "summary" : outputView;

  const renderSectionMeta = (key: AnalysisCardSection["key"]) => {
    switch (key) {
      case "parties":
        return {
          icon: <Users className="w-4 h-4 text-blue-600" />,
          card: "border-blue-100 bg-blue-50/40",
          title: "text-blue-900",
        };
      case "ids":
        return {
          icon: <Hash className="w-4 h-4 text-teal-600" />,
          card: "border-teal-100 bg-teal-50/40",
          title: "text-teal-900",
        };
      case "financials":
        return {
          icon: <IndianRupee className="w-4 h-4 text-amber-600" />,
          card: "border-amber-100 bg-amber-50/40",
          title: "text-amber-900",
        };
      case "risks":
        return {
          icon: <Scale className="w-4 h-4 text-rose-600" />,
          card: "border-rose-100 bg-rose-50/40",
          title: "text-rose-900",
        };
    }
  };

  return (
    <div className="space-y-6">
      {/* Unified Studio Command Deck */}
      <section className="bg-white border border-slate-150 rounded-2xl shadow-[0_4px_20px_-4px_rgba(0,0,0,0.05)] overflow-hidden">
        {/* Top Row: Presets & Dataset Selector */}
        <div className="px-5 py-3.5 border-b border-slate-100 flex flex-col lg:flex-row lg:items-center justify-between gap-3 bg-white">
          <div className="flex items-center gap-2 min-w-0 overflow-x-auto no-scrollbar">
            <span className="inline-flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wider text-slate-400 mr-1 shrink-0">
              <Sparkles className="w-3.5 h-3.5 text-blue-600" />
              Presets
            </span>
            {JUDGE_SCENARIOS.map((sc) => {
              const isActive = activeScenarioId === sc.id;
              return (
                <button
                  key={sc.id}
                  type="button"
                  title={`${sc.label} (${sc.badge})`}
                  onClick={() => applyScenario(sc)}
                  className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl text-xs font-semibold border transition cursor-pointer shrink-0 shadow-2xs ${
                    isActive
                      ? "bg-blue-50 border-blue-300 text-blue-700 shadow-xs ring-2 ring-blue-500/20"
                      : "bg-white border-slate-200 text-slate-700 hover:border-slate-300 hover:bg-slate-50"
                  }`}
                >
                  <span className={`w-2 h-2 rounded-full shrink-0 ${TONE_DOTS[sc.tone]}`} />
                  <span className="whitespace-nowrap">{sc.shortLabel}</span>
                </button>
              );
            })}
          </div>

          <div className="flex items-center gap-2.5 shrink-0">
            {samples.length > 0 && (
              <select
                aria-label="Load sample from 50-document Indian dataset"
                defaultValue=""
                onChange={(e) => {
                  const doc = samples.find((s) => s.doc_id === e.target.value);
                  if (doc) {
                    setActiveScenarioId(null);
                    setUploadedDocMeta(null);
                    setText(doc.text);
                    setPurpose(doc.purpose);
                    setCategory(doc.category);
                    setResult(null);
                    setDetectionsPreview([]);
                    setHighlightMode(false);
                  }
                }}
                className="text-xs font-semibold bg-white border border-slate-200 hover:border-slate-300 text-slate-800 rounded-xl px-3 py-1.5 focus:outline-none focus:ring-2 focus:ring-blue-500/20 cursor-pointer max-w-[220px] shadow-2xs"
              >
                <option value="" disabled>
                  Dataset Corpus (50 Docs)...
                </option>
                {samples.map((s) => (
                  <option key={s.doc_id} value={s.doc_id}>
                    {s.doc_id} — {s.title}
                  </option>
                ))}
              </select>
            )}

            <button
              type="button"
              onClick={() => setShowRedTeam((v) => !v)}
              className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-xl border text-xs font-semibold transition cursor-pointer whitespace-nowrap shadow-2xs ${
                activeSimCount > 0
                  ? "bg-amber-50 border-amber-300 text-amber-800 ring-2 ring-amber-500/20"
                  : "bg-white border-slate-200 text-slate-700 hover:border-slate-300 hover:bg-slate-50"
              }`}
            >
              <FlaskConical className="w-3.5 h-3.5 text-amber-600" />
              <span>Red-Team</span>
              {activeSimCount > 0 && (
                <span className="px-1.5 py-0.2 rounded-full bg-amber-200 text-amber-900 text-[10px] font-bold">
                  {activeSimCount}
                </span>
              )}
              {showRedTeam ? (
                <ChevronUp className="w-3.5 h-3.5 text-slate-500" />
              ) : (
                <ChevronDown className="w-3.5 h-3.5 text-slate-500" />
              )}
            </button>
          </div>
        </div>

        {/* Middle Row: Document Intake Dropzone */}
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setIsDragOver(true);
          }}
          onDragLeave={() => setIsDragOver(false)}
          onDrop={(e) => {
            e.preventDefault();
            setIsDragOver(false);
            const dropped = e.dataTransfer.files?.[0];
            if (dropped) handleFileUpload(dropped);
          }}
          className={`px-5 py-3.5 border-b transition ${
            isDragOver
              ? "bg-blue-50/60 border-blue-400"
              : "bg-slate-50/40 border-slate-100 hover:bg-slate-50/70"
          }`}
        >
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
            <div className="flex items-center gap-3.5 min-w-0">
              <div
                className={`w-10 h-10 rounded-2xl flex items-center justify-center shrink-0 border shadow-2xs ${
                  isDragOver
                    ? "bg-blue-100 border-blue-300 text-blue-700"
                    : "bg-white border-slate-200 text-blue-600"
                }`}
              >
                <UploadCloud className="w-5 h-5" />
              </div>
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2 text-xs font-bold text-slate-900">
                  <span>Upload Property, Legal, Image Scan (OCR), or KYC Document</span>
                  <span className="text-[10px] px-2 py-0.5 rounded-full bg-blue-50 border border-blue-200 text-blue-700 font-mono font-bold">
                    PDF • DOCX • PNG / JPG (OCR) • TXT • CSV
                  </span>
                </div>
                <p className="text-[11px] text-slate-500 truncate mt-0.5">
                  Drag &amp; drop any Sale Deed, Legal Notice, Aadhaar/PAN Photo, or Agreement — OCR &amp; PII detection run 100% locally before any LLM call.
                </p>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-2.5 shrink-0">
              <SwitchPill
                checked={autoRunOnUpload}
                onChange={setAutoRunOnUpload}
                label="Auto-run"
                tone="emerald"
                title="Automatically execute Gateway pipeline after local document extraction"
              />
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.docx,.png,.jpg,.jpeg,.webp,.bmp,.tif,.tiff,.txt,.md,.csv,.json,.log,.xml,.html"
                className="hidden"
                onChange={(e) => {
                  const picked = e.target.files?.[0];
                  if (picked) handleFileUpload(picked);
                }}
              />
              <button
                type="button"
                disabled={uploading || !canSubmit}
                onClick={() => fileInputRef.current?.click()}
                className="inline-flex items-center gap-2 px-3.5 py-2 rounded-xl bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white text-xs font-bold shadow-md shadow-blue-500/20 transition cursor-pointer whitespace-nowrap"
              >
                <FileUp className="w-4 h-4" />
                <span>{uploading ? "Running OCR / Extract..." : "Upload Document"}</span>
              </button>
            </div>
          </div>

          {uploadedDocMeta && (
            <div className="mt-3 pt-3 border-t border-slate-200/80 flex flex-wrap items-center justify-between gap-2 text-xs">
              <div className="flex flex-wrap items-center gap-2">
                <span className="px-2.5 py-1 rounded-lg bg-white border border-slate-200 text-slate-800 font-bold shadow-2xs">
                  {uploadedDocMeta.filename} ({(uploadedDocMeta.file_size_bytes / 1024).toFixed(1)} KB)
                </span>
                {uploadedDocMeta.image_dimensions && (
                  <span className="px-2.5 py-1 rounded-lg bg-white border border-slate-200 text-slate-600 font-mono">
                    {uploadedDocMeta.image_dimensions}px
                  </span>
                )}
                {uploadedDocMeta.page_count != null && (
                  <span className="px-2.5 py-1 rounded-lg bg-white border border-slate-200 text-slate-600">
                    {uploadedDocMeta.page_count} page{uploadedDocMeta.page_count === 1 ? "" : "s"}
                  </span>
                )}
                {uploadedDocMeta.ocr_used && (
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-purple-50 border border-purple-200 text-purple-700 font-bold">
                    <ScanText className="w-3.5 h-3.5 text-purple-600" />
                    Local OCR
                    {uploadedDocMeta.ocr_confidence != null
                      ? ` • ${Math.round(uploadedDocMeta.ocr_confidence * 100)}% conf`
                      : ""}
                    {uploadedDocMeta.ocr_line_count != null
                      ? ` • ${uploadedDocMeta.ocr_line_count} lines`
                      : ""}
                    {uploadedDocMeta.ocr_processing_ms != null
                      ? ` • ${Math.round(uploadedDocMeta.ocr_processing_ms)}ms`
                      : ""}
                  </span>
                )}
                <span className="px-2.5 py-1 rounded-lg bg-white border border-slate-200 text-slate-600">
                  {uploadedDocMeta.word_count.toLocaleString()} words • {uploadedDocMeta.extraction_method}
                </span>
                <span className="px-2.5 py-1 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-800 font-bold">
                  Classified: {uploadedDocMeta.suggested_category.replace(/_/g, " ")} →{" "}
                  {uploadedDocMeta.suggested_purpose.replace(/_/g, " ")}
                </span>
                {uploadedDocMeta.classification_signals.length > 0 && (
                  <span className="text-slate-500 text-[11px]">
                    Cues: {uploadedDocMeta.classification_signals.slice(0, 4).join(", ")}
                  </span>
                )}
              </div>
              <button
                type="button"
                onClick={() => setUploadedDocMeta(null)}
                className="text-slate-400 hover:text-slate-700 p-1 rounded-lg hover:bg-slate-100"
                title="Dismiss file summary"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>

        {/* Policy Binding & Execution Row */}
        <div className="px-5 py-4 flex flex-col lg:flex-row lg:items-end gap-3 bg-white">
          <div className="flex-1 grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-3">
            <div>
              <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-1.5">
                Document Category
              </label>
              <select
                value={category}
                onChange={(e) => setCategory(e.target.value)}
                className="w-full text-xs font-semibold bg-white border border-slate-200 hover:border-slate-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 focus:outline-none rounded-xl px-3 py-2 text-slate-800 cursor-pointer shadow-2xs"
              >
                <option value="property_document">Property Document</option>
                <option value="legal_document">Legal Document</option>
                <option value="loan_application">Loan Application</option>
                <option value="kyc_document">KYC Document</option>
                <option value="insurance_claim">Insurance Claim</option>
                <option value="support_ticket">Support Ticket</option>
                <option value="general_document">General Document</option>
              </select>
            </div>

            <div>
              <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-1.5">
                Business Purpose
              </label>
              <select
                value={purpose}
                onChange={(e) => setPurpose(e.target.value)}
                className="w-full text-xs font-semibold bg-white border border-slate-200 hover:border-slate-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 focus:outline-none rounded-xl px-3 py-2 text-slate-800 cursor-pointer shadow-2xs"
              >
                <option value="property_verification">Property Verification</option>
                <option value="legal_review">Legal Review &amp; Compliance</option>
                <option value="loan_underwriting">Loan Underwriting</option>
                <option value="kyc_verification">KYC Verification</option>
                <option value="customer_support">Customer Support Triage</option>
                <option value="insurance_claims">Insurance Claims</option>
                <option value="marketing_analytics">Marketing Analytics (Strict Block)</option>
                <option value="document_summarization">Document Summarization</option>
              </select>
            </div>

            <div>
              <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-1.5">
                Tokenization Mode
              </label>
              <select
                value={mode}
                onChange={(e) => setMode(e.target.value as TokenizationMode)}
                className="w-full text-xs font-semibold bg-white border border-slate-200 hover:border-slate-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 focus:outline-none rounded-xl px-3 py-2 text-slate-800 cursor-pointer shadow-2xs"
              >
                <option value="cryptographic_random">Cryptographic Bracket</option>
                <option value="typed_sequential">Typed Sequential</option>
                <option value="format_preserving">Format-Preserving</option>
              </select>
            </div>

            <div>
              <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-1.5">
                Target LLM Provider
              </label>
              <select
                value={provider}
                onChange={(e) => setProvider(e.target.value)}
                className="w-full text-xs font-semibold bg-white border border-slate-200 hover:border-slate-300 focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 focus:outline-none rounded-xl px-3 py-2 text-slate-800 cursor-pointer shadow-2xs"
              >
                <option value="gemini">Google Gemini (Cloud LLM — Priority)</option>
                <option value="openai">OpenAI (Chat Completions)</option>
                <option value="local_slm">On-Prem Local SLM (Fallback / Air-Gapped)</option>
              </select>
            </div>
          </div>

          <div className="flex items-center gap-2.5 shrink-0">
            <button
              type="button"
              onClick={handleAnalyzeOnly}
              disabled={!canSubmit || analyzing || !text.trim()}
              className="inline-flex items-center justify-center gap-1.5 px-3.5 py-2 rounded-xl border border-slate-200 bg-white hover:bg-slate-50 text-xs font-bold text-slate-700 disabled:opacity-40 transition cursor-pointer whitespace-nowrap shadow-2xs"
            >
              <ScanSearch className="w-4 h-4 text-blue-600" />
              <span>{analyzing ? "Scanning..." : "Scan Only"}</span>
            </button>
            <button
              type="button"
              onClick={handleExecutePipeline}
              disabled={!canSubmit || loading || !text.trim()}
              className="inline-flex items-center justify-center gap-2 px-5 py-2 rounded-xl bg-[#168FF0] hover:bg-blue-600 text-xs font-bold text-white shadow-md shadow-blue-500/25 disabled:opacity-40 transition cursor-pointer whitespace-nowrap"
            >
              <Play className="w-4 h-4 fill-current" />
              <span>{loading ? "Running..." : "Run Gateway"}</span>
            </button>
          </div>
        </div>

        {/* Runtime Guardrails & Collapsible Red-Team Strip */}
        <div className="px-5 py-3 bg-slate-50/60 border-t border-slate-100 flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2.5">
            <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500 mr-1">
              Runtime Guards
            </span>
            <SwitchPill
              checked={restoreResponse}
              onChange={setRestoreResponse}
              label="RBAC Restoration"
              tone="emerald"
              title="Attempt authorized local PII unmasking on the LLM response"
            />
            <SwitchPill
              checked={enableFallback}
              onChange={setEnableFallback}
              label="Local SLM Fallback"
              tone="sky"
              title="Automatically route to on-prem SLM if cloud provider is unavailable or unconfigured"
            />
            <button
              type="button"
              onClick={() => setShowEvalMetrics(!showEvalMetrics)}
              className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-xl text-xs font-semibold border transition cursor-pointer shadow-2xs ${
                showEvalMetrics
                  ? "bg-blue-50 border-blue-300 text-blue-700 shadow-xs"
                  : "bg-white border-slate-200 text-slate-600 hover:text-slate-900"
              }`}
              title="Toggle detailed document evaluation metrics scorecard"
            >
              <BarChart3 className="w-3.5 h-3.5 text-blue-600" />
              <span>Evaluation Metrics</span>
              <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-blue-100 text-blue-800 font-mono font-bold">
                {result?.security_decision ? `${result.security_decision} • ${result.raw_pii_leak_count} LEAKS` : "ACTIVE"}
              </span>
            </button>
          </div>

          {(showRedTeam || activeSimCount > 0) && (
            <div className="flex flex-wrap items-center gap-2">
              <span className="text-[10px] font-bold uppercase tracking-wider text-amber-700 mr-1">
                Fault Injection
              </span>
              <SwitchPill
                checked={simulateOffline}
                onChange={setSimulateOffline}
                label="Cloud Outage"
                tone="amber"
              />
              <SwitchPill
                checked={simulateTampered}
                onChange={setSimulateTampered}
                label="Tampered PII Leak"
                tone="rose"
              />
              <SwitchPill
                checked={simulateForged}
                onChange={setSimulateForged}
                label="Forged Token"
                tone="fuchsia"
              />
              {activeSimCount > 0 && (
                <button
                  type="button"
                  onClick={() => {
                    setSimulateOffline(false);
                    setSimulateTampered(false);
                    setSimulateForged(false);
                  }}
                  className="inline-flex items-center gap-1 px-2.5 py-1 rounded-xl text-xs text-slate-600 hover:text-slate-900 border border-slate-200 bg-white shadow-2xs cursor-pointer"
                >
                  <RotateCcw className="w-3 h-3" />
                  Reset
                </button>
              )}
            </div>
          )}
        </div>
      </section>

      {!canSubmit && (
        <div className="p-4 rounded-2xl bg-amber-50 border border-amber-200 text-amber-800 text-xs flex items-center gap-2.5 shadow-2xs">
          <ShieldAlert className="w-4 h-4 shrink-0 text-amber-600" />
          <span>
            Current role <strong>{user.role}</strong> is read-only (<code className="font-mono">audit:read</code>). Switch to Admin,
            Privacy Officer, Loan Underwriter, or Analyst in the header to run the gateway.
          </span>
        </div>
      )}

      {error && (
        <div className="p-4 rounded-2xl bg-rose-50 border border-rose-200 text-rose-800 text-xs flex items-center gap-2.5 shadow-2xs">
          <AlertTriangle className="w-4 h-4 shrink-0 text-rose-600" />
          <span>{error}</span>
        </div>
      )}

      {/* Document Evaluation Metrics */}
      {showEvalMetrics && (
        <DocumentEvaluationMetrics
          report={evalReport}
          uploadedDocMeta={uploadedDocMeta}
          result={result}
          detectionsPreview={detectionsPreview}
          originalText={text}
          datasetSamples={samples}
          onClose={() => setShowEvalMetrics(false)}
          onRequestReevaluate={selectedFile ? () => handleReevaluate(selectedFile) : undefined}
          isEvaluating={evaluatingDoc}
        />
      )}

      {/* Interactive Pipeline, Post-Masking Recheck & Fallback SLM Visualizer */}
      <PipelineVisualizer
        result={result}
        loading={loading}
        detectionsPreview={detectionsPreview}
        selectedProvider={provider}
        requestedProvider={lastRequestedProvider}
        enableFallback={enableFallback}
        simulateOffline={simulateOffline}
        simulateTampered={simulateTampered}
        simulateForged={simulateForged}
        purpose={purpose}
        userRole={user.role}
      />

      {/* Three-Column Workbench */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5 items-stretch">
        {/* PANEL A: Source & Local Detection */}
        <div className="bg-white border border-slate-150 rounded-2xl p-5 flex flex-col gap-3.5 shadow-[0_4px_20px_-4px_rgba(0,0,0,0.05)]">
          <div className="flex items-center justify-between gap-2 pb-3 border-b border-slate-100">
            <div className="flex items-center gap-2.5 min-w-0">
              <div className="w-8 h-8 rounded-xl bg-blue-50 border border-blue-100 flex items-center justify-center shrink-0 text-blue-600 shadow-2xs">
                <FileText className="w-4 h-4" />
              </div>
              <div className="min-w-0">
                <h3 className="text-xs font-bold text-slate-900 tracking-tight truncate">
                  Panel A • Input &amp; Local NER
                </h3>
                <div className="text-[11px] text-slate-400">
                  {activeDetections.length > 0
                    ? `${activeDetections.length} sensitive entity span${activeDetections.length === 1 ? "" : "s"} identified locally`
                    : "Ready for local Presidio + Indic PII scan"}
                </div>
              </div>
            </div>

            <div className="inline-flex rounded-xl bg-slate-100 p-0.5 shrink-0">
              <button
                type="button"
                onClick={() => setHighlightMode(false)}
                className={`px-2.5 py-1 rounded-lg text-xs font-bold transition cursor-pointer ${
                  !highlightMode ? "bg-white text-slate-900 shadow-xs" : "text-slate-500 hover:text-slate-900"
                }`}
              >
                Raw
              </button>
              <button
                type="button"
                disabled={activeDetections.length === 0}
                onClick={() => setHighlightMode(true)}
                className={`px-2.5 py-1 rounded-lg text-xs font-bold transition cursor-pointer disabled:opacity-40 ${
                  highlightMode ? "bg-blue-600 text-white shadow-xs" : "text-slate-500 hover:text-slate-900"
                }`}
              >
                Spans ({activeDetections.length})
              </button>
            </div>
          </div>

          <div>
            <label className="block text-[10px] font-bold uppercase tracking-wider text-slate-500 mb-1">
              Enterprise Task Prompt
            </label>
            <input
              type="text"
              value={task}
              onChange={(e) => setTask(e.target.value)}
              className="w-full text-xs font-medium bg-slate-50/60 border border-slate-200 focus:bg-white focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 focus:outline-none rounded-xl px-3 py-2 text-slate-800"
            />
          </div>

          <div className="flex-1 flex flex-col min-h-[250px]">
            <div className="flex items-center justify-between mb-1.5">
              <span className="text-[10px] font-bold uppercase tracking-wider text-slate-500">
                Source Document Payload
              </span>
              <span
                className={`text-[11px] font-mono font-semibold ${
                  text.length > 120000 ? "text-rose-600" : "text-slate-400"
                }`}
              >
                {text.length.toLocaleString()} / 120,000 chars
                {text.length > 120000 && " (Limit Exceeded)"}
              </span>
            </div>
            {highlightMode && activeDetections.length > 0 ? (
              <div className="flex-1 min-h-[230px] max-h-[320px] overflow-y-auto p-3.5 rounded-xl bg-slate-50 border border-slate-200 text-xs leading-relaxed whitespace-pre-wrap text-slate-800 font-mono">
                {renderHighlightedText(text, activeDetections)}
              </div>
            ) : (
              <textarea
                value={text}
                onChange={(e) => setText(e.target.value)}
                rows={11}
                placeholder="Paste document text or upload a PDF/DOCX/TXT/CSV file above..."
                className="flex-1 w-full min-h-[230px] text-xs font-mono bg-slate-50/60 border border-slate-200 focus:bg-white focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 rounded-xl p-3.5 text-slate-800 leading-relaxed focus:outline-none"
              />
            )}
          </div>

          {/* Entity Breakdown + List */}
          <div className="border-t border-slate-100 pt-3 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                Local Detections ({activeDetections.length})
              </span>
              {entityBreakdown.length > 0 && (
                <div className="flex flex-wrap gap-1 justify-end">
                  {entityBreakdown.slice(0, 4).map(([etype, count]) => (
                    <span
                      key={etype}
                      className="text-[10px] px-2 py-0.5 rounded-full bg-slate-100 border border-slate-200 text-slate-700 font-mono font-bold"
                    >
                      {etype}×{count}
                    </span>
                  ))}
                </div>
              )}
            </div>
            <div className="max-h-44 overflow-y-auto space-y-1.5 pr-0.5">
              {activeDetections.length === 0 ? (
                <div className="text-xs text-slate-400 py-4 text-center rounded-xl bg-slate-50 border border-slate-100">
                  Run <strong>Scan Only</strong> or <strong>Run Gateway</strong> to inspect local PII detections.
                </div>
              ) : (
                activeDetections.map((d, i) => (
                  <div
                    key={`${d.start}-${d.end}-${i}`}
                    title={`Recognizer: ${d.recognizer}`}
                    className="flex items-center justify-between text-xs px-3 py-2 rounded-xl bg-slate-50/70 border border-slate-150 hover:bg-white transition"
                  >
                    <div className="flex items-center gap-2 min-w-0">
                      <span
                        className={`px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wide shrink-0 ${
                          d.category_tier === "mandatory"
                            ? "bg-rose-50 text-rose-700 border border-rose-200"
                            : "bg-blue-50 text-blue-700 border border-blue-200"
                        }`}
                      >
                        {d.entity_type}
                      </span>
                      <span className="font-mono text-slate-800 font-semibold truncate">{d.matched_text}</span>
                    </div>
                    <span className="text-[11px] font-mono text-slate-400 shrink-0 ml-2 font-bold">
                      {Math.round(d.confidence * 100)}%
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>

        {/* PANEL B: Outbound Security Gate & AES-256-GCM Vault */}
        <div className="bg-white border border-slate-150 rounded-2xl p-5 flex flex-col gap-3.5 shadow-[0_4px_20px_-4px_rgba(0,0,0,0.05)]">
          <div className="flex items-center justify-between gap-2 pb-3 border-b border-slate-100">
            <div className="flex items-center gap-2.5 min-w-0">
              <div className="w-8 h-8 rounded-xl bg-emerald-50 border border-emerald-100 flex items-center justify-center shrink-0 text-emerald-600 shadow-2xs">
                <ShieldCheck className="w-4 h-4" />
              </div>
              <div className="min-w-0">
                <h3 className="text-xs font-bold text-slate-900 tracking-tight truncate">
                  Panel B • Outbound Gate &amp; Vault
                </h3>
                <div className="text-[11px] text-slate-400">
                  Zero-leak inspection &amp; AES-256-GCM vaulting
                </div>
              </div>
            </div>

            {result ? (
              <span
                className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wide border shrink-0 ${
                  result.security_decision === "PASS"
                    ? "bg-emerald-50 border-emerald-200 text-emerald-700"
                    : "bg-rose-50 border-rose-200 text-rose-700"
                }`}
              >
                {result.security_decision} • {result.raw_pii_leak_count} Leaks
              </span>
            ) : (
              <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-slate-100 border border-slate-200 text-slate-500 shrink-0">
                Standby
              </span>
            )}
          </div>

          {!result ? (
            <div className="flex-1 flex flex-col items-center justify-center text-center p-6 border border-dashed border-slate-200 rounded-2xl bg-slate-50/50">
              <div className="w-12 h-12 rounded-2xl bg-white border border-slate-200 shadow-2xs flex items-center justify-center mb-3">
                <Lock className="w-6 h-6 text-slate-400" />
              </div>
              <div className="text-xs font-bold text-slate-800 mb-1">
                Fail-Closed Outbound Inspection
              </div>
              <p className="text-[11px] text-slate-500 max-w-[260px] leading-relaxed">
                Run Gateway to verify all 7 outbound security checks, inspect canonical SHA-256 payload digests, and view AES-256-GCM vault ciphertexts.
              </p>
            </div>
          ) : (
            <>
              <div
                className={`p-3.5 rounded-2xl border text-xs flex items-start gap-2.5 ${
                  result.security_decision === "PASS"
                    ? "bg-emerald-50/70 border-emerald-200 text-emerald-900"
                    : "bg-rose-50/70 border-rose-200 text-rose-900"
                }`}
              >
                {result.security_decision === "PASS" ? (
                  <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0 mt-0.5" />
                ) : (
                  <XCircle className="w-4 h-4 text-rose-600 shrink-0 mt-0.5" />
                )}
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-bold">
                      Security Gate: {result.security_decision} (Leaks: {result.raw_pii_leak_count})
                    </span>
                    <CopyButton value={result.outbound_payload_sha256} label="SHA" />
                  </div>
                  <div className="text-[11px] opacity-90 mt-0.5">{result.security_reason}</div>
                  <div className="text-[10px] font-mono opacity-70 truncate mt-1">
                    SHA-256: {result.outbound_payload_sha256}
                  </div>
                </div>
              </div>

              {/* Itemized Gate Checks */}
              <div className="space-y-1.5">
                {result.gate_checks.map((chk) => {
                  const isSkipped = chk.detail?.toLowerCase().includes("not evaluated");
                  return (
                    <div
                      key={chk.name}
                      title={chk.detail}
                      className="flex items-center justify-between gap-2 text-xs px-3 py-2 rounded-xl bg-slate-50/70 border border-slate-150"
                    >
                      <div className="min-w-0">
                        <div className="text-slate-800 font-bold truncate">{chk.name}</div>
                        <div className="text-[10px] text-slate-500 truncate">{chk.detail}</div>
                      </div>
                      <span
                        className={`font-bold text-[10px] px-2 py-0.5 rounded-full uppercase shrink-0 border ${
                          chk.passed
                            ? "bg-emerald-50 border-emerald-200 text-emerald-700"
                            : isSkipped
                              ? "bg-slate-100 border-slate-200 text-slate-500"
                              : "bg-rose-50 border-rose-200 text-rose-700"
                        }`}
                      >
                        {chk.passed ? "PASS" : isSkipped ? "SKIPPED" : "BLOCKED"}
                      </span>
                    </div>
                  );
                })}
              </div>

              <div>
                <div className="flex items-center justify-between gap-2 mb-1.5">
                  <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider truncate">
                    Sanitized Outbound Text (Zero Raw PII)
                  </span>
                  <div className="flex items-center gap-1.5 shrink-0">
                    <button
                      type="button"
                      disabled={result.security_decision !== "PASS" || result.raw_pii_leak_count > 0}
                      title={
                        result.security_decision === "PASS"
                          ? "Download zero-PII sanitized document (.txt)"
                          : "Disabled because Security Gate blocked this payload"
                      }
                      onClick={() => downloadSanitizedDocument(result, uploadedDocMeta?.filename)}
                      className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg border border-emerald-200 bg-emerald-50 hover:bg-emerald-100 text-[10px] font-bold text-emerald-700 disabled:opacity-40 transition cursor-pointer shadow-2xs"
                    >
                      <Download className="w-3 h-3" />
                      <span>Sanitized Doc</span>
                    </button>
                    <CopyButton value={result.sanitized_outbound_payload} />
                  </div>
                </div>
                <pre className="max-h-36 overflow-y-auto p-3 rounded-xl bg-slate-50 border border-slate-200 text-xs font-mono text-emerald-800 whitespace-pre-wrap leading-relaxed font-semibold">
                  {result.sanitized_outbound_payload}
                </pre>
              </div>

              {/* Zero-PII Compliance Certificate Exports */}
              <div className="p-3 rounded-2xl bg-blue-50/60 border border-blue-100 flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2 text-xs text-blue-900 font-bold">
                  <FileCheck2 className="w-4 h-4 text-blue-600 shrink-0" />
                  <span>DPDP Compliance Certificate</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <button
                    type="button"
                    onClick={() =>
                      downloadComplianceCertificatePdf(result, user, uploadedDocMeta?.filename)
                    }
                    className="inline-flex items-center gap-1 px-3 py-1 rounded-lg border border-blue-300 bg-blue-600 hover:bg-blue-700 text-[10px] font-bold text-white transition cursor-pointer shadow-xs"
                  >
                    <Download className="w-3 h-3" />
                    <span>PDF Certificate</span>
                  </button>
                  <button
                    type="button"
                    onClick={() =>
                      downloadComplianceCertificateJson(result, user, uploadedDocMeta?.filename)
                    }
                    className="inline-flex items-center gap-1 px-2.5 py-1 rounded-lg border border-slate-200 bg-white hover:bg-slate-50 text-[10px] font-semibold text-slate-700 transition cursor-pointer shadow-2xs"
                  >
                    <FileJson className="w-3 h-3 text-amber-500" />
                    <span>JSON</span>
                  </button>
                </div>
              </div>

              {/* AES-256-GCM Vault Proof Drawer */}
              <div className="border-t border-slate-100 pt-2.5">
                <button
                  type="button"
                  onClick={() => setShowVaultProof((v) => !v)}
                  className="w-full flex items-center justify-between text-[10px] font-bold text-slate-600 uppercase tracking-wider cursor-pointer"
                >
                  <span className="flex items-center gap-1.5">
                    <Database className="w-3.5 h-3.5 text-amber-600" />
                    AES-256-GCM Vault Proof ({result.vault_metadata.length})
                  </span>
                  {showVaultProof ? (
                    <ChevronUp className="w-3.5 h-3.5 text-slate-400" />
                  ) : (
                    <ChevronDown className="w-3.5 h-3.5 text-slate-400" />
                  )}
                </button>
                {showVaultProof && (
                  <div className="mt-2.5 max-h-40 overflow-y-auto space-y-1.5 pr-0.5">
                    {result.vault_metadata.map((vm, i) => (
                      <div
                        key={`${vm.placeholder}-${i}`}
                        className="p-2.5 rounded-xl bg-slate-50 border border-slate-200/80 text-[10px] font-mono space-y-0.5"
                      >
                        <div className="flex justify-between text-amber-800 font-bold">
                          <span className="truncate">{vm.placeholder}</span>
                          <span className="shrink-0 ml-2">{vm.entity_type}</span>
                        </div>
                        <div className="text-slate-600 truncate">Nonce: {vm.nonce_hex}</div>
                        <div className="text-slate-600 truncate">
                          Cipher: {vm.ciphertext_preview_hex}
                        </div>
                        <div className="text-slate-400 truncate">GCM Tag: {vm.auth_tag_hex}</div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </>
          )}
        </div>

        {/* PANEL C: Execution Trace, Restoration & Response */}
        <div className="bg-white border border-slate-150 rounded-2xl p-5 flex flex-col gap-3.5 shadow-[0_4px_20px_-4px_rgba(0,0,0,0.05)]">
          <div className="flex items-center justify-between gap-2 pb-3 border-b border-slate-100">
            <div className="flex items-center gap-2.5 min-w-0">
              <div className="w-8 h-8 rounded-xl bg-purple-50 border border-purple-100 flex items-center justify-center shrink-0 text-purple-600 shadow-2xs">
                <Cpu className="w-4 h-4" />
              </div>
              <div className="min-w-0">
                <h3 className="text-xs font-bold text-slate-900 tracking-tight truncate">
                  Panel C • Trace &amp; Local Restoration
                </h3>
                <div className="text-[11px] text-slate-400">
                  RBAC unmasking, token integrity &amp; latency trace
                </div>
              </div>
            </div>

            {result ? (
              <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-slate-100 border border-slate-200 text-slate-700 shrink-0">
                {result.total_latency_ms}ms
              </span>
            ) : (
              <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-slate-100 border border-slate-200 text-slate-500 shrink-0">
                Awaiting
              </span>
            )}
          </div>

          {!result ? (
            <div className="flex-1 flex flex-col items-center justify-center text-center p-6 border border-dashed border-slate-200 rounded-2xl bg-slate-50/50">
              <div className="w-12 h-12 rounded-2xl bg-white border border-slate-200 shadow-2xs flex items-center justify-center mb-3">
                <KeyRound className="w-6 h-6 text-slate-400" />
              </div>
              <div className="text-xs font-bold text-slate-800 mb-1">
                RBAC Restoration &amp; Output
              </div>
              <p className="text-[11px] text-slate-500 max-w-[260px] leading-relaxed">
                Authorized responses, forged-token blocks, cloud-to-SLM fallback telemetry, and end-to-end execution traces appear here.
              </p>
            </div>
          ) : (
            <>
              {/* Provider / Fallback Badge */}
              <div className="flex flex-wrap items-center gap-2 text-xs">
                <span className="px-2.5 py-1 rounded-xl bg-slate-100 border border-slate-200 text-slate-800 font-bold">
                  Provider: {result.provider}{" "}
                  <span className="text-slate-500 font-normal">({result.model})</span>
                </span>
                {result.fallback_triggered && (
                  <span className="px-2.5 py-1 rounded-xl bg-amber-50 border border-amber-300 text-amber-800 font-bold">
                    Local SLM Fallback
                  </span>
                )}
                <span className="px-2.5 py-1 rounded-xl bg-slate-100 border border-slate-200 text-slate-600 font-mono text-[10px] font-bold">
                  {result.local_processing_ms}ms local
                </span>
              </div>

              {result.restoration && (
                <div className="grid grid-cols-3 gap-2.5 text-center">
                  <div className="p-3 rounded-2xl bg-slate-50/70 border border-slate-150">
                    <div className="text-[10px] font-bold text-slate-500 uppercase">Restored</div>
                    <div className="text-xl font-extrabold text-emerald-600 mt-1">
                      {result.restoration.restored_count}
                    </div>
                  </div>
                  <div className="p-3 rounded-2xl bg-slate-50/70 border border-slate-150">
                    <div className="text-[10px] font-bold text-slate-500 uppercase">Forged/Unknown</div>
                    <div className="text-xl font-extrabold text-rose-600 mt-1">
                      {result.restoration.unknown_or_forged_placeholders.length}
                    </div>
                  </div>
                  <div className="p-3 rounded-2xl bg-slate-50/70 border border-slate-150">
                    <div className="text-[10px] font-bold text-slate-500 uppercase">New LLM PII</div>
                    <div className="text-xl font-extrabold text-amber-600 mt-1">
                      {result.restoration.newly_generated_pii_count}
                    </div>
                  </div>
                </div>
              )}

              {result.restoration && !result.restoration.authorized && (
                <div className="p-3.5 rounded-2xl bg-amber-50 border border-amber-200 text-amber-800 text-xs flex items-center gap-2.5">
                  <ShieldAlert className="w-4 h-4 shrink-0 text-amber-600" />
                  <span>
                    RBAC Enforced: Role <strong>{user.role}</strong> is not authorized to unmask PII
                    for <strong>{result.purpose}</strong>. Placeholders remain sealed.
                  </span>
                </div>
              )}

              {result.restoration &&
                result.restoration.unknown_or_forged_placeholders.length > 0 && (
                  <div className="p-3.5 rounded-2xl bg-rose-50 border border-rose-200 text-rose-800 text-xs">
                    <strong>[UNVERIFIED_TOKEN_BLOCKED]</strong> Unrecognized placeholder(s) flagged &amp;
                    kept un-restored:{" "}
                    <span className="font-mono font-bold">
                      {result.restoration.unknown_or_forged_placeholders.join(", ")}
                    </span>
                  </div>
                )}

              <div className="flex-1 flex flex-col">
                <div className="flex items-center justify-between gap-2 mb-2">
                  <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider truncate">
                    Output ({result.restoration?.restoration_status ?? result.status})
                  </span>
                  <div className="flex items-center gap-1.5 shrink-0">
                    <div className="inline-flex rounded-xl bg-slate-100 p-0.5">
                      {structuredSections.length > 0 && (
                        <button
                          type="button"
                          onClick={() => setOutputView("cards")}
                          className={`px-2.5 py-1 rounded-lg text-[10px] font-bold transition cursor-pointer ${
                            effectiveOutputView === "cards"
                              ? "bg-blue-600 text-white shadow-xs"
                              : "text-slate-600 hover:text-slate-900"
                          }`}
                        >
                          Cards
                        </button>
                      )}
                      <button
                        type="button"
                        onClick={() => setOutputView("summary")}
                        className={`px-2.5 py-1 rounded-lg text-[10px] font-bold transition cursor-pointer ${
                          effectiveOutputView === "summary"
                            ? "bg-white text-slate-900 shadow-xs"
                            : "text-slate-600 hover:text-slate-900"
                        }`}
                      >
                        Summary
                      </button>
                      {result.raw_llm_response && (
                        <button
                          type="button"
                          onClick={() => setOutputView("raw")}
                          className={`px-2.5 py-1 rounded-lg text-[10px] font-bold transition cursor-pointer ${
                            effectiveOutputView === "raw"
                              ? "bg-blue-600 text-white shadow-xs"
                              : "text-slate-600 hover:text-slate-900"
                          }`}
                        >
                          Raw Masked
                        </button>
                      )}
                    </div>
                    <CopyButton value={activeResponseText} />
                  </div>
                </div>

                {effectiveOutputView === "cards" && structuredSections.length > 0 ? (
                  <div className="flex-1 min-h-[210px] max-h-80 overflow-y-auto space-y-2.5 pr-0.5">
                    {structuredSections.map((sec) => {
                      const meta = renderSectionMeta(sec.key);
                      return (
                        <div
                          key={sec.key}
                          className={`p-3 rounded-2xl border ${meta.card} space-y-1.5 shadow-2xs`}
                        >
                          <div className={`flex items-center gap-2 text-xs font-bold ${meta.title}`}>
                            {meta.icon}
                            <span>{sec.title}</span>
                          </div>
                          {sec.items.length === 0 ? (
                            <div className="text-xs text-slate-500">No entries flagged.</div>
                          ) : (
                            <ul className="space-y-1 text-xs text-slate-800 leading-relaxed">
                              {sec.items.map((item, idx) => (
                                <li key={idx} className="flex items-start gap-2">
                                  <span className="text-blue-500 mt-1">•</span>
                                  <span className="break-words font-medium">{item}</span>
                                </li>
                              ))}
                            </ul>
                          )}
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <pre className="flex-1 min-h-[175px] max-h-72 overflow-y-auto p-3.5 rounded-2xl bg-slate-50 border border-slate-200 text-xs font-mono text-slate-800 whitespace-pre-wrap leading-relaxed font-medium">
                    {activeResponseText}
                  </pre>
                )}
              </div>

              {/* Execution Trace Strip */}
              <div className="border-t border-slate-100 pt-2.5">
                <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400 mb-1.5">
                  Execution Trace
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {result.execution_trace.map((step, idx) => (
                    <span
                      key={idx}
                      className="text-[10px] font-mono px-2 py-0.5 rounded-md bg-slate-100 border border-slate-200 text-slate-700 font-semibold"
                    >
                      {step}
                    </span>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
};
