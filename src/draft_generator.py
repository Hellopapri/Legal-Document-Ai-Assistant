from __future__ import annotations

import os
from typing import Dict, List

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - handled at runtime
    OpenAI = None


def _evidence_block(evidence: List[Dict]) -> str:
    lines = []
    for index, item in enumerate(evidence, start=1):
        lines.append(f"[Evidence {index}] {item.get('text', '')}")
    return "\n\n".join(lines)


def _mock_draft(draft_type: str, structured_data: Dict, evidence: List[Dict], learned_rules: List[str]) -> str:
    """Generate a grounded mock draft from retrieved evidence with bullet points and references."""
    document_type = structured_data.get("document_type", "Legal Document")
    
    # Build title based on draft type
    title_map = {
        "Case Fact Summary": f"Fact Summary - {document_type}",
        "Internal Legal Memo": f"Internal Memo - {document_type}",
        "Document Checklist": f"Compliance Checklist - {document_type}",
    }
    title = title_map.get(draft_type, f"{draft_type} - {document_type}")
    
    # Extract key facts and obligations for bullet points
    key_facts = structured_data.get("key_facts", [])[:3]
    obligations = structured_data.get("obligations", [])[:3]
    risks = structured_data.get("risks", [])[:2]
    
    body = [f"# {title}", ""]
    
    # Add evidence-grounded content
    if evidence:
        body.append("## Grounded Evidence")
        for index, item in enumerate(evidence, start=1):
            text_preview = item.get("text", "")[:150]
            relevance = item.get("relevance_score", 0)
            body.append(f"- **[Evidence {index}]** (relevance: {relevance}) {text_preview}...")
        body.append("")
    else:
        body.append("*No evidence retrieved - generating from structured data.*\n")
    
    # Add key facts
    if key_facts:
        body.append("## Key Facts")
        for fact in key_facts:
            if fact:
                body.append(f"- {fact[:100]}")
        body.append("")
    
    # Add obligations
    if obligations:
        body.append("## Obligations")
        for obligation in obligations:
            if obligation:
                body.append(f"- {obligation[:100]}")
        body.append("")
    
    # Add risks
    if risks:
        body.append("## Risks & Considerations")
        for risk in risks:
            if risk:
                body.append(f"- {risk[:100]}")
        body.append("")
    
    # Add learned rules if any
    if learned_rules:
        body.append("## Applied Operator Rules")
        for rule in learned_rules[:5]:
            body.append(f"- {rule}")
        body.append("")
    
    # Add warning if evidence is weak
    if len(evidence) < 2:
        body.append("**⚠️ Warning:** Limited evidence retrieved. Treat as first-pass draft only.")
    
    return "\n".join(body).strip()


def generate_draft(draft_type: str, structured_data: Dict, extracted_text: str, evidence: List[Dict], learned_rules: List[str]) -> str:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key or OpenAI is None:
        return _mock_draft(draft_type, structured_data, evidence, learned_rules)

    evidence_text = _evidence_block(evidence)
    learned_rules_text = "\n".join(f"- {rule}" for rule in learned_rules[:10]) or "- No learned rules yet."
    prompt = f"""
You are drafting a legal-style document using only the provided evidence.
Draft type: {draft_type}

Rules:
- Use only evidence provided below.
- Do not invent facts or legal conclusions.
- Include evidence references inline in the form [Evidence 1], [Evidence 2], etc.
- If evidence is weak or missing, include a clear warning.
- Apply these reusable operator rules when relevant:
{learned_rules_text}

Structured data:
{structured_data}

Evidence:
{evidence_text}

Extracted source text:
{extracted_text[:12000]}
"""

    try:
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Write concise, grounded legal drafts with evidence references."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
        )
        draft = response.choices[0].message.content or ""
    except Exception:
        return _mock_draft(draft_type, structured_data, evidence, learned_rules)
    if "[Evidence" not in draft:
        fallback_evidence = "\n".join(f"[Evidence {index}] {item.get('text', '')}" for index, item in enumerate(evidence, start=1))
        if not fallback_evidence:
            fallback_evidence = "[Evidence 1] No evidence retrieved."
        draft = f"{draft.strip()}\n\n{fallback_evidence}\n\nWarning: draft should include evidence references and the model did not produce them.".strip()
    return draft.strip()