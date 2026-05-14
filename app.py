import json
from datetime import datetime
from pathlib import Path
import sys

import streamlit as st

ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from document_processor import process_uploaded_file
from structured_extractor import extract_structured_data
from retriever import retrieve_evidence, build_or_update_index, chunk_text
from draft_generator import generate_draft
from edit_learner import load_learned_rules, save_edit_and_learn
from evaluator import evaluate_run

DATA_DIR = ROOT_DIR / "data"
EXTRACTED_DIR = DATA_DIR / "extracted"
OUTPUTS_DIR = DATA_DIR / "outputs"
EDITS_DIR = DATA_DIR / "edits"

for directory in [DATA_DIR, EXTRACTED_DIR, OUTPUTS_DIR, EDITS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)


def initialize_state() -> None:
    defaults = {
        "processed_document": None,
        "extracted_text": "",
        "extracted_char_count": 0,
        "file_info": {},
        "structured_data": {},
        "chunk_count": 0,
        "retrieved_evidence": [],
        "generated_draft": "",
        "edited_draft": "",
        "learned_rules": load_learned_rules(),
        "processing_warning": "",
        "ocr_warning": "",
        "evaluation": {},
        "document_name": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def get_workflow_progress() -> str:
    """Return a compact progress string based on current state."""
    has_file = bool(st.session_state.get("extracted_text"))
    has_chunks = st.session_state.get("chunk_count", 0) > 0
    has_evidence = bool(st.session_state.get("retrieved_evidence"))
    has_draft = bool(st.session_state.get("generated_draft"))
    has_eval = bool(st.session_state.get("evaluation"))
    
    progress = "Upload"
    if has_file:
        progress += " → Extract ✓"
    if has_chunks:
        progress += " → Retrieve ✓"
    if has_draft:
        progress += " → Draft ✓"
    if has_eval:
        progress += " → Eval ✓"
    return progress


def render_sidebar() -> None:
    st.sidebar.title("📋 Workflow")
    steps = [
        "📤 Upload document",
        "📖 Process text / OCR",
        "🔍 Review extraction",
        "✍️ Generate grounded draft",
        "📝 Edit and learn",
        "📊 Inspect evaluation",
    ]
    for step in steps:
        st.sidebar.write(step)
    st.sidebar.markdown("---")
    st.sidebar.markdown(
        """
        <div style="
            color: rgba(49, 51, 63, 0.58);
            text-align: left;
            line-height: 1.2;
        ">
            <div style="font-size: 18px; font-weight: 500;">Legal Document AI Assistant</div>
            <div style="margin-top: 8px; font-size: 15px; font-weight: 500;">Built by Papri</div>
            <div style="font-size: 14px; font-weight: 400;">Data Analyst &amp; AI Engineer</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def save_run_artifact(payload: dict) -> Path:
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    safe_name = payload.get("document_name", "document").replace(" ", "_")
    output_path = OUTPUTS_DIR / f"{safe_name}_{timestamp}.json"
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return output_path


def main() -> None:
    st.set_page_config(page_title="Legal Document AI Assistant", layout="wide")
    initialize_state()
    render_sidebar()

    # Watermark styling
    st.markdown("""
    <style>
        .watermark {
            text-align: center;
            color: #000000;
            font-size: 13px;
            font-weight: 400;
            letter-spacing: 2px;
            margin-top: 24px;
            margin-bottom: 12px;
            font-family: -apple-system, BlinkMacSystemFont, sans-serif;
        }
    </style>
    """, unsafe_allow_html=True)

    st.title("Legal Document AI Assistant")
    st.caption("Process legal documents with AI extraction, retrieval, and draft generation.")
    
    # Compact progress bar
    st.markdown(f"**Progress:** `{get_workflow_progress()}`")
    st.markdown("---")

    col_left, col_right = st.columns([1, 1])

    with col_left:
        st.subheader("📤 Upload & Process")
        uploaded_file = st.file_uploader(
            "Select a document",
            type=["pdf", "png", "jpg", "jpeg", "txt"],
            accept_multiple_files=False,
        )

        if st.button("Process Document", type="primary", use_container_width=True):
            if uploaded_file is None:
                st.warning("Upload a file before processing.")
            else:
                with st.spinner("Processing document..."):
                    file_bytes = uploaded_file.getvalue()
                    file_name = uploaded_file.name
                    result = process_uploaded_file(file_bytes, file_name, EXTRACTED_DIR)
                    st.session_state.processed_document = result
                    st.session_state.extracted_text = result.get("extracted_text", "")
                    st.session_state.extracted_char_count = result.get("extracted_char_count", 0)
                    st.session_state.document_name = result.get("document_name", file_name)
                    st.session_state.processing_warning = result.get("warning", "")
                    st.session_state.ocr_warning = result.get("ocr_warning", "")
                    st.session_state.file_info = {
                        "file_name": result.get("document_name", file_name),
                        "file_ext": result.get("file_ext", Path(file_name).suffix.lower()),
                        "file_size": result.get("file_size", 0),
                        "page_count": result.get("pdf_page_count", None),
                        "pdf_error": result.get("pdf_error", ""),
                        "pymupdf_chars": result.get("pymupdf_chars", 0),
                    }

                    if not st.session_state.extracted_text:
                        st.session_state.structured_data = {}
                        st.session_state.retrieved_evidence = []
                        st.session_state.generated_draft = ""
                        st.session_state.edited_draft = ""
                        st.session_state.evaluation = {}
                        if result.get("file_ext") == ".pdf":
                            if result.get("pdf_page_count", 0) == 0 and not result.get("pdf_error"):
                                st.error("PyMuPDF opened the file but found 0 pages.")
                            elif result.get("pdf_error"):
                                st.error(f"PyMuPDF error: {result.get('pdf_error')}")
                        st.warning("No text was extracted from the document.")
                    else:
                        st.session_state.structured_data = extract_structured_data(
                            st.session_state.extracted_text, result.get("document_name", file_name)
                        )
                        build_or_update_index(
                            document_name=st.session_state.document_name,
                            extracted_text=st.session_state.extracted_text,
                        )
                        st.session_state.chunk_count = len(chunk_text(st.session_state.extracted_text))
                        st.success("Document processed successfully.")

        draft_type = st.selectbox(
            "Draft type",
            ["Case Fact Summary", "Internal Legal Memo", "Document Checklist"],
        )

        if st.button("Generate Draft", use_container_width=True):
            if not st.session_state.extracted_text:
                st.warning("Process a document first.")
            else:
                with st.spinner("Retrieving evidence and generating draft..."):
                    evidence = retrieve_evidence(
                        query=draft_type,
                        document_name=st.session_state.document_name,
                        extracted_text=st.session_state.extracted_text,
                        structured_data=st.session_state.structured_data,
                        top_k=4,
                    )
                    st.session_state.retrieved_evidence = evidence if evidence else []
                    st.session_state.generated_draft = generate_draft(
                        draft_type=draft_type,
                        structured_data=st.session_state.structured_data,
                        extracted_text=st.session_state.extracted_text,
                        evidence=evidence or [],
                        learned_rules=st.session_state.learned_rules,
                    )
                    st.session_state.edited_draft = st.session_state.generated_draft
                    st.session_state.evaluation = evaluate_run(
                        extracted_text=st.session_state.extracted_text,
                        retrieved_evidence=evidence or [],
                        draft_text=st.session_state.generated_draft,
                        chunk_count=st.session_state.get("chunk_count", 0),
                    )
                    st.success("Draft generated.")

    with col_right:
        st.subheader("📊 Status & Debug")
        
        file_info = st.session_state.get("file_info", {}) or {}
        if file_info:
            st.write(f"**File:** {file_info.get('file_name')}")
            st.write(f"**Size:** {file_info.get('file_size')} bytes")
            if file_info.get("page_count") is not None:
                st.write(f"**PDF Pages:** {file_info.get('page_count')}")
            st.write(f"**Extracted Chars:** {st.session_state.get('extracted_char_count', 0)}")
            if file_info.get("pymupdf_chars"):
                st.write(f"**PyMuPDF Chars:** {file_info.get('pymupdf_chars')}")
            if file_info.get("pdf_error"):
                st.error(f"**Error:** {file_info.get('pdf_error')}")
        else:
            st.info("No file processed yet.")

        st.metric("Chunks", st.session_state.get("chunk_count", 0))
        st.metric("Evidence Retrieved", len(st.session_state.get("retrieved_evidence", [])))
        if st.session_state.get("evaluation"):
            score = st.session_state["evaluation"].get("simple_groundedness_score", 0.0)
            st.metric("Groundedness", f"{score:.2f}")

    if st.session_state.processing_warning:
        st.warning(st.session_state.processing_warning)
    if st.session_state.ocr_warning:
        st.warning(st.session_state.ocr_warning)

    st.markdown("---")
    st.subheader("📖 Extracted Text")
    char_count = st.session_state.get("extracted_char_count", 0)
    st.write(f"Characters: {char_count}")
    st.text_area("Extracted text", st.session_state.extracted_text, height=180, disabled=True)

    with st.expander("Preview (first 500 chars)"):
        preview = (st.session_state.extracted_text or "")[:500]
        if preview:
            st.code(preview)
        else:
            st.write("No extracted text to preview.")

    st.subheader("🏗️ Structured Data")
    st.json(st.session_state.structured_data if st.session_state.structured_data else {})

    st.subheader("✍️ Generated Draft")
    st.text_area("Draft", st.session_state.generated_draft, height=220, disabled=True)

    st.subheader("🎯 Retrieved Evidence")
    if st.session_state.retrieved_evidence:
        for index, item in enumerate(st.session_state.retrieved_evidence, start=1):
            with st.expander(f"Evidence {index}"):
                st.write(item.get("text", ""))
                metadata = item.get("metadata", {})
                if metadata:
                    st.json(metadata)
    else:
        st.info("No evidence retrieved yet.")

    st.subheader("📝 Edit & Learn")
    st.session_state.edited_draft = st.text_area(
        "Edit the draft",
        value=st.session_state.edited_draft or st.session_state.generated_draft,
        height=220,
    )

    if st.button("Save Edit and Learn", use_container_width=True):
        if not st.session_state.generated_draft:
            st.warning("Generate a draft before saving an edit.")
        else:
            learned_rule_result = save_edit_and_learn(
                document_name=st.session_state.document_name or (uploaded_file.name if uploaded_file else "unknown_document"),
                original_draft=st.session_state.generated_draft,
                edited_draft=st.session_state.edited_draft,
                retrieved_evidence=st.session_state.retrieved_evidence,
                edits_dir=EDITS_DIR,
            )
            st.session_state.learned_rules = load_learned_rules()
            st.success("Edit saved and learning rules updated.")
            if learned_rule_result.get("new_rules"):
                st.info("New rules extracted from the edit.")

            evaluation_payload = evaluate_run(
                extracted_text=st.session_state.extracted_text,
                retrieved_evidence=st.session_state.retrieved_evidence,
                draft_text=st.session_state.edited_draft,
                chunk_count=st.session_state.get("chunk_count", 0),
            )
            st.session_state.evaluation = evaluation_payload

            save_run_artifact(
                {
                    "document_name": st.session_state.document_name,
                    "timestamp_utc": datetime.utcnow().isoformat(),
                    "original_draft": st.session_state.generated_draft,
                    "edited_draft": st.session_state.edited_draft,
                    "retrieved_evidence": st.session_state.retrieved_evidence,
                    "structured_data": st.session_state.structured_data,
                    "evaluation": st.session_state.evaluation,
                    "learned_rules": st.session_state.learned_rules,
                }
            )

    st.subheader("📚 Learned Rules")
    learned_rules = st.session_state.learned_rules or []
    if learned_rules:
        for rule in learned_rules:
            st.write(f"- {rule}")
    else:
        st.info("No learned rules yet.")

    st.subheader("📊 Evaluation Results")
    st.json(st.session_state.evaluation if st.session_state.evaluation else {})

    # Footer with watermark
    st.markdown("---")
    st.markdown(
        "<div class='watermark'>Developed by Papri ✦</div>",
        unsafe_allow_html=True
    )


if __name__ == "__main__":
    main()
