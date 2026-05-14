from __future__ import annotations

import difflib
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List


BASE_DIR = Path(__file__).resolve().parents[1]
LEARNED_RULES_PATH = BASE_DIR / "data" / "edits" / "learned_rules.json"


def load_learned_rules() -> List[str]:
    if not LEARNED_RULES_PATH.exists():
        return []
    try:
        data = json.loads(LEARNED_RULES_PATH.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return [str(item) for item in data]
        if isinstance(data, dict):
            return [str(item) for item in data.get("rules", [])]
    except Exception:
        return []
    return []


def _extract_rules_from_diff(original_draft: str, edited_draft: str) -> List[str]:
    original_lines = original_draft.splitlines()
    edited_lines = edited_draft.splitlines()
    diff = list(difflib.ndiff(original_lines, edited_lines))
    rules = []
    for line in diff:
        if line.startswith("+ "):
            added = line[2:].strip()
            if len(added) < 8:
                continue
            if any(keyword in added.lower() for keyword in ["evidence", "warning", "include", "avoid", "cite", "ground", "assumption", "checklist"]):
                rules.append(f"Prefer language that preserves the operator change: {added}")
    if not rules and edited_draft.strip() != original_draft.strip():
        rules.append("Mirror operator formatting and phrasing changes in future drafts when they improve clarity.")
    return list(dict.fromkeys(rules))


def save_edit_and_learn(document_name: str, original_draft: str, edited_draft: str, retrieved_evidence: List[Dict], edits_dir: Path) -> Dict:
    edits_dir.mkdir(parents=True, exist_ok=True)
    learned_rules = load_learned_rules()
    new_rules = _extract_rules_from_diff(original_draft, edited_draft)
    combined_rules = list(dict.fromkeys(learned_rules + new_rules))

    LEARNED_RULES_PATH.parent.mkdir(parents=True, exist_ok=True)
    LEARNED_RULES_PATH.write_text(json.dumps(combined_rules, indent=2), encoding="utf-8")

    payload = {
        "document_name": document_name,
        "timestamp_utc": datetime.utcnow().isoformat(),
        "original_draft": original_draft,
        "edited_draft": edited_draft,
        "retrieved_evidence": retrieved_evidence,
        "new_rules": new_rules,
        "all_rules": combined_rules,
    }
    output_path = edits_dir / f"{Path(document_name).stem}_{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}.json"
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    payload["saved_path"] = str(output_path)
    return payload