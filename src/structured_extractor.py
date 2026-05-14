from __future__ import annotations

import json
import os
import re
from typing import Dict

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - handled at runtime
    OpenAI = None


def _fallback_structured_data(extracted_text: str, document_name: str) -> Dict:
    """Extract structured fields using heuristics."""
    text_lower = extracted_text.lower()
    lines = [line.strip() for line in extracted_text.splitlines() if line.strip()]
    
    # Infer document type
    doc_type_keywords = {
        "agreement": ["agreement", "contract"],
        "assessment": ["assessment", "evaluation", "review"],
        "notice": ["notice", "notification"],
        "memo": ["memo", "memorandum"],
        "letter": ["letter", "correspondence"],
        "policy": ["policy", "procedure"],
        "report": ["report", "findings"],
    }
    document_type = "Legal Document"
    for doc_type, keywords in doc_type_keywords.items():
        if any(kw in text_lower[:500] for kw in keywords):
            document_type = doc_type.title()
            break
    
    # Extract dates (improved regex)
    dates = re.findall(
        r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4})",
        extracted_text,
        re.IGNORECASE,
    )
    dates = list(dict.fromkeys(dates))[:5]  # Remove duplicates
    
    # Extract parties (entities, signatories)
    parties = []
    for line in lines[:20]:
        if any(token in line.lower() for token in ["between", "party", "client", "provider", "by", "from"]):
            if len(line) < 150:  # Likely a single entity reference
                parties.append(line)
    
    # Extract headings (likely to be in uppercase or after special markers)
    headings = []
    for line in lines:
        if line.isupper() and len(line) < 100 and len(line.split()) < 10:
            headings.append(line)
        elif line.startswith(("Section", "Article")):
            headings.append(line[:100])
    
    # Extract key facts (first few substantive lines)
    key_facts = [line for line in lines if len(line) > 20 and len(line) < 200][:5]
    
    # Extract obligations
    obligation_keywords = ["shall", "must", "agree", "required", "obligated", "will", "responsible", "liable", "bound"]
    obligations = [line for line in lines if any(kw in line.lower() for kw in obligation_keywords)][:5]
    
    # Extract risks
    risk_keywords = ["risk", "breach", "terminate", "default", "liable", "damages", "penalty", "loss", "violation", "failure"]
    risks = [line for line in lines if any(kw in line.lower() for kw in risk_keywords)][:5]
    
    # Find unclear sections (very long or complex sentences)
    unclear_sections = [line for line in lines if len(line) > 150 and len(line.split()) > 20][:3]
    
    return {
        "document_type": document_type,
        "parties": parties[:5] or ["Not clearly identified"],
        "dates": dates or ["No dates identified"],
        "headings": headings[:5] or ["No section headings found"],
        "key_facts": key_facts or [f"Document with {len(extracted_text)} characters and {len(lines)} lines"],
        "obligations": obligations or ["No explicit obligations identified"],
        "risks": risks or ["No explicit risks identified"],
        "unclear_sections": unclear_sections or ["No particularly unclear sections detected"],
        "source": "heuristic",
    }


def _call_openai_structured_extraction(extracted_text: str, document_name: str) -> Dict:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key or OpenAI is None:
        return _fallback_structured_data(extracted_text, document_name)

    client = OpenAI(api_key=api_key)
    prompt = f"""
You are extracting structured information from a messy legal document.
Return valid JSON only with these keys:
document_type, parties, dates, key_facts, obligations, risks, unclear_sections.

Rules:
- Use only the text provided.
- If a field is missing, return an empty list or short neutral string.
- Keep values concise and grounded.
- Do not invent facts.

Document name: {document_name}
Text:
{extracted_text[:16000]}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Return structured JSON only."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
        )
        content = response.choices[0].message.content or "{}"
    except Exception:
        return _fallback_structured_data(extracted_text, document_name)
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return _fallback_structured_data(extracted_text, document_name)


def extract_structured_data(extracted_text: str, document_name: str) -> Dict:
    if not extracted_text.strip():
        return {
            "document_type": "Unknown",
            "parties": [],
            "dates": [],
            "key_facts": [],
            "obligations": [],
            "risks": [],
            "unclear_sections": ["No text was extracted from the document."],
            "source": "empty",
        }
    return _call_openai_structured_extraction(extracted_text, document_name)