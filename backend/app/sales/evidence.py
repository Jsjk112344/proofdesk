"""Deterministic evidence handling: sources, verbatim claims, hypothesis and demo decision.

Everything here is controller code. Claims are verbatim sentences from fetched pages
with their source and capture time. The demonstration decision is a rule over cited
claims, so a model proposal can only add candidate claims; it cannot force a demo.
"""

import re
from urllib.parse import urlsplit

SUPPORTED_CAPABILITY = {
    "id": "document_extraction",
    "label": "Document-workflow automation demonstration",
    "summary": (
        "Structured extraction from semi-structured business documents (invoices, delivery "
        "notes, order forms) executed in a disposable sandbox on labelled synthetic input, "
        "with the result validated against an expected answer."
    ),
}
MIN_EVIDENCE_CHARS = 400
MAX_CLAIMS = 6
_DOCUMENT = re.compile(
    r"\b(invoices?|invoicing|purchase orders?|delivery notes?|proofs? of delivery|"
    r"bills? of lading|receipts?|paperwork|forms?|statements?|remittances?|credit notes?|"
    r"packing lists?|customs declarations?|timesheets?|expense reports?|claim forms?|"
    r"pdfs?|scanned|scans|contracts?|documents?)\b",
    re.IGNORECASE,
)
_MANUAL = re.compile(
    r"\b(manual(?:ly)?|by hand|keyed|keying|re-?keyed|re-?key|retyped?|data entry|"
    r"spreadsheets?|emailed|faxed|fax|paper|backlog|hours|errors?|reconcil\w*|"
    r"typing|transcrib\w*)\b",
    re.IGNORECASE,
)
_OPERATIONS = re.compile(
    r"\b(operations|logistics|finance|accounts payable|accounts receivable|procurement|"
    r"back[- ]office|administration|compliance|onboarding|warehouse|dispatch)\b",
    re.IGNORECASE,
)
_SENTENCE = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"“(])")
_WORD_DIGITS = re.compile(r"\d")
_PLURALS = {"proof of delivery": "proofs of delivery", "bill of lading": "bills of lading"}


def plural(term):
    term = term.lower()
    if term in _PLURALS:
        return _PLURALS[term]
    if term.endswith(("s", "paperwork", "scanned", "scans")):
        return term
    return term[:-1] + "ies" if term.endswith("y") else term + "s"


def document_terms(claims, limit=3):
    """Distinct document terms from excerpts, plural form, first-seen order."""
    seen = []
    for claim in claims:
        for match in _DOCUMENT.finditer(claim["excerpt"]):
            term = plural(match.group(0))
            if term not in seen:
                seen.append(term)
    return seen[:limit]


def cited(ids, limit=4):
    return ", ".join(ids[:limit]) + (" and others" if len(ids) > limit else "")


def normalize(text):
    return " ".join((text or "").split())


def sentences(text):
    for block in (text or "").split("\n"):
        for sentence in _SENTENCE.split(normalize(block)):
            sentence = sentence.strip()
            if 40 <= len(sentence) <= 400:
                yield sentence


def build_sources(pages):
    """Public source records plus bounded text, numbered s1.. in fetch order."""
    sources = []
    for index, page in enumerate(pages, start=1):
        record = page.record()
        record["id"] = f"s{index}"
        record["text_chars"] = len(page.text)
        sources.append({**record, "text": page.text})
    return sources


def strip_text(sources):
    return [{k: v for k, v in s.items() if k != "text"} for s in sources]


def company_name(sources, fallback_url=None):
    for source in sources:
        if source["status"] == "fetched" and source.get("title"):
            title = re.split(r"\s+[|\-–—:]\s+", source["title"])[0].strip()
            if 2 <= len(title) <= 60:
                return title
    host = urlsplit(fallback_url or "").hostname or ""
    return host[4:] if host.startswith("www.") else host or "this company"


def classify(sentence):
    document = bool(_DOCUMENT.search(sentence))
    manual = bool(_MANUAL.search(sentence))
    if document and manual:
        return "document_workflow", "strong"
    if document:
        return "document_workflow", "moderate"
    if _OPERATIONS.search(sentence):
        return "operations", "context"
    return "other", None


def extract_claims(sources):
    """Verbatim sentences ranked by relevance to the supported capability."""
    ranked = []
    seen = set()
    for source in sources:
        if source["status"] != "fetched":
            continue
        for sentence in sentences(source["text"]):
            if "SYNTHETIC" in sentence.upper() and "EXAMPLE" in sentence.upper():
                continue
            key = normalize(sentence).lower()
            if key in seen:
                continue
            topic, strength = classify(sentence)
            if strength is None:
                continue
            seen.add(key)
            ranked.append(
                (
                    {"strong": 0, "moderate": 1, "context": 2}[strength],
                    len(ranked),
                    {
                        "text": sentence,
                        "text_kind": "verbatim",
                        "source_id": source["id"],
                        "excerpt": sentence,
                        "verification": "verbatim_quotation",
                        "topic": topic,
                        "strength": strength,
                    },
                )
            )
    claims = [claim for _, _, claim in sorted(ranked)[:MAX_CLAIMS]]
    for index, claim in enumerate(claims, start=1):
        claim["id"] = f"c{index}"
    return claims


def company_summary(sources):
    for source in sources:
        if source["status"] != "fetched":
            continue
        description = normalize(source.get("description") or "")
        if len(description) >= 40:
            return quotation(description[:400], source["id"], description)
        for sentence in sentences(source["text"]):
            if "SYNTHETIC EXAMPLE" in sentence.upper():
                continue
            return quotation(sentence, source["id"], sentence)
        if source.get("title"):
            return quotation(source["title"], source["id"], source["title"])
    return None


def quotation(text, source_id, excerpt):
    """A verbatim summary record: the text is the quotation itself, never a paraphrase."""
    return {
        "text": text,
        "text_kind": "verbatim",
        "source_id": source_id,
        "excerpt": excerpt,
        "verification": "verbatim_quotation",
    }


def evidence_chars(sources):
    return sum(s["text_chars"] for s in sources if s["status"] == "fetched")


def unknowns(sources, claims):
    items = []
    if not any(_WORD_DIGITS.search(c["excerpt"]) for c in claims if c["strength"] == "strong"):
        items.append("Document volumes, formats and frequency were not stated on fetched pages.")
    items.append("Current tooling or system of record was not identified.")
    items.append("No named decision-maker or contact was found; none was invented.")
    items.append("Budget, timing and buying intent are unknown; nothing here shows intent.")
    missing = [s for s in sources if s["status"] != "fetched"]
    if missing:
        items.append(
            f"{len(missing)} requested page(s) could not be retrieved "
            f"({', '.join(sorted({s['failure_reason'] or 'unknown' for s in missing}))}). "
            "A retrieval failure is not evidence about the prospect."
        )
    return items


def decide_demo(sources, claims):
    """Controller rule. Runs the supported demo only on cited document-workflow evidence."""
    fetched = [s for s in sources if s["status"] == "fetched"]
    if not fetched or evidence_chars(sources) < MIN_EVIDENCE_CHARS:
        return {
            "decision": "skip_insufficient_evidence",
            "capability": SUPPORTED_CAPABILITY["id"],
            "claim_ids": [],
            "reason": (
                "Too little public text was retrieved to judge relevance. The demonstration "
                "was skipped as a research limitation, not as a verdict on the prospect."
            ),
        }
    strong = [c for c in claims if c["strength"] == "strong"]
    moderate = [c for c in claims if c["strength"] == "moderate"]
    if strong or len(moderate) >= 2:
        cited_claims = strong or moderate
        return {
            "decision": "run",
            "capability": SUPPORTED_CAPABILITY["id"],
            "claim_ids": [c["id"] for c in cited_claims],
            "reason": (
                "Fetched pages contain document-handling statements "
                + ("with manual steps" if strong else "without explicit manual steps")
                + f" ({cited([c['id'] for c in cited_claims])}). The supported extraction "
                "demonstration is relevant; it runs on labelled synthetic documents, "
                "never on the prospect's files."
            ),
        }
    return {
        "decision": "skip_irrelevant",
        "capability": SUPPORTED_CAPABILITY["id"],
        "claim_ids": [],
        "reason": (
            "The fetched pages do not mention document-handling work, so the document "
            "extraction demonstration would not be relevant. SalesDesk only demonstrates "
            "that one capability; the outreach stays research-only."
        ),
    }


def hypothesis(company, claims, decision):
    strong = [c for c in claims if c["strength"] == "strong"]
    moderate = [c for c in claims if c["strength"] == "moderate"]
    if decision["decision"] == "skip_insufficient_evidence":
        text = (
            "Too little public text was retrieved to form an opportunity hypothesis. "
            "Ask rather than assume; this is a research limitation."
        )
        ids = []
    elif strong:
        ids = [c["id"] for c in strong]
        text = (
            f"{company} appears to handle {', '.join(document_terms(strong))} with manual "
            f"steps ({cited(ids)}). Structured extraction with checkable results could reduce "
            "manual entry. Volumes, current tooling and ownership are unverified; this is a "
            "hypothesis from public pages, not a confirmed need."
        )
    elif moderate:
        ids = [c["id"] for c in moderate]
        text = (
            f"The site mentions {', '.join(document_terms(moderate))} ({cited(ids)}), but does "
            "not say whether these documents involve manual handling. Treat document "
            "automation as a question to ask, not a confirmed need."
        )
    else:
        text = (
            f"The fetched pages describe {company}'s business without mentioning document-"
            "handling work. No document-automation opportunity is evidenced. Any outreach "
            "should ask an open question rather than pitch extraction."
        )
        ids = []
    return {"text": text, "claim_ids": ids, "label": "hypothesis"}


def deterministic_brief(sources, prospect_url=None):
    """Rule-based brief with no model call. Labelled so the UI never implies a model."""
    claims = extract_claims(sources)
    decision = decide_demo(sources, claims)
    company = company_name(sources, prospect_url)
    return {
        "provenance": "deterministic",
        "company_name": company,
        "company_summary": company_summary(sources),
        "claims": claims,
        "opportunity_hypothesis": hypothesis(company, claims, decision),
        "unknowns": unknowns(sources, claims),
        "evidence_chars": evidence_chars(sources),
    }, decision
