from __future__ import annotations

from typing import Dict, List


def evaluate_run(extracted_text: str, retrieved_evidence: List[Dict], draft_text: str, chunk_count: int | None = None) -> Dict:
    extracted_characters = len(extracted_text or "")
    chunk_total = chunk_count if chunk_count is not None else len(retrieved_evidence or [])
    evidence_count = len(retrieved_evidence or [])
    evidence_references_present = "[Evidence" in (draft_text or "")
    unsupported_warning = any(token in (draft_text or "").lower() for token in ["warning", "unsupported", "missing evidence", "evidence is limited"])
    groundedness_score = 0.0
    if extracted_characters > 0:
        groundedness_score += 0.3
    if chunk_total > 0:
        groundedness_score += 0.3
    if evidence_references_present:
        groundedness_score += 0.3
    if unsupported_warning:
        groundedness_score += 0.1
    groundedness_score = round(min(1.0, groundedness_score), 2)

    return {
        "number_of_extracted_characters": extracted_characters,
        "number_of_chunks": chunk_total,
        "number_of_retrieved_evidence_passages": evidence_count,
        "draft_contains_evidence_references": evidence_references_present,
        "unsupported_claim_warning": unsupported_warning,
        "simple_groundedness_score": groundedness_score,
    }