# Legal Document AI Assistant

## Project Overview
Legal Document AI Assistant is a Streamlit app for processing messy legal-style documents, extracting structured facts, retrieving grounded evidence, generating legal-style drafts, and learning from operator edits.

## Problem Statement
Legal workflows often start with noisy, incomplete, or scanned documents. Analysts need a lightweight tool that can extract text, identify key facts, ground a first-pass draft in evidence, and steadily improve quality from human edits.

## Features
- Upload PDF, PNG, JPG, JPEG, and TXT files.
- Extract text with PyMuPDF for PDFs and pytesseract + Pillow OCR fallback for image/scanned files.
- Warn when Tesseract is unavailable without blocking text-based PDF and TXT processing.
- Extract structured fields: document type, parties, dates, key facts, obligations, risks, and unclear sections.
- Split content into chunks and store them in ChromaDB.
- Retrieve evidence for three draft types: Case Fact Summary, Internal Legal Memo, and Document Checklist.
- Generate drafts with inline evidence references like [Evidence 1].
- Let operators edit drafts, save comparisons, and learn reusable improvement rules.
- Evaluate extraction, evidence retrieval, citation coverage, and a simple groundedness score.

## Architecture Overview
The app is organized into small modules so each stage of the workflow is testable and easy to reason about.

- `app.py` coordinates the Streamlit UI and session state.
- `src/document_processor.py` handles uploads, text extraction, OCR fallback, and saved extracted text.
- `src/structured_extractor.py` performs structured extraction using OpenAI when available, otherwise a deterministic mock extractor.
- `src/retriever.py` chunks text and stores or queries ChromaDB.
- `src/draft_generator.py` generates grounded drafts, again with OpenAI or a mock fallback.
- `src/edit_learner.py` compares drafts, extracts simple reusable rules, and stores them in JSON.
- `src/evaluator.py` calculates lightweight evaluation metrics.

## Folder Structure
```
legal-document-ai-assistant/
├── app.py
├── requirements.txt
├── README.md
├── .env.example
├── data/
│   ├── sample_docs/
│   ├── extracted/
│   ├── outputs/
│   └── edits/
├── src/
│   ├── __init__.py
│   ├── document_processor.py
│   ├── structured_extractor.py
│   ├── retriever.py
│   ├── draft_generator.py
│   ├── edit_learner.py
│   └── evaluator.py
└── samples/
    ├── sample_legal_note.txt
    ├── sample_output.json
    └── sample_evaluation.md
```

## Setup Instructions
1. Create and activate a virtual environment.
2. Install dependencies.
3. Add your OpenAI API key if you want live model output.
4. Start the app with Streamlit.

## Required Tools
- Python 3.10+
- Streamlit
- PyMuPDF
- pytesseract
- Pillow
- ChromaDB
- OpenAI
- python-dotenv
- Tesseract OCR installed locally for image and scanned PDF OCR fallback

## Install Dependencies
```bash
pip install -r requirements.txt
```

## Add OpenAI API Key
Copy `.env.example` to `.env` and set:
```bash
OPENAI_API_KEY=your_real_key_here
```
If the key is missing, the app uses mock structured extraction and mock draft generation so it still works.

## Run the App
```bash
streamlit run app.py
```

## Exact Terminal Commands
```bash
python -m venv venv
```

Windows:
```bash
venv\Scripts\activate
```

Mac/Linux:
```bash
source venv/bin/activate
```

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Sample Input / Output
- Sample input: `samples/sample_legal_note.txt`
- Sample output: `samples/sample_output.json`
- Sample evaluation: `samples/sample_evaluation.md`

## Assumptions and Tradeoffs
- The app prioritizes a reliable first-pass workflow over deep legal reasoning.
- When OpenAI is unavailable, the app falls back to deterministic mock extraction and mock draft generation.
- OCR quality depends on local Tesseract installation and the quality of the input image or scan.
- ChromaDB is used for a simple local retrieval layer rather than a production-grade vector service.

## Evaluation Approach and Sample Results
The evaluation section tracks:
- number of extracted characters
- number of chunks
- number of retrieved evidence passages
- whether the draft contains evidence references
- whether an unsupported-claim warning is present
- a simple groundedness score

Sample result: a text-based document with good extraction and citations should score near 1.0, while a noisy scan with weak retrieval should score lower and show a warning.

## How Operator Edits Improve Future Drafts
When an operator edits a draft, the app stores the original draft, edited draft, document name, timestamp, and retrieved evidence. It then derives simple reusable improvement rules from the diff and saves them in `data/edits/learned_rules.json`. Those rules are injected into future draft generation prompts.

## Submission Notes for GitHub
- Commit the full project folder.
- Include `.env.example` but do not commit your real `.env` file.
- Run the app once before submission to confirm dependencies and file paths work on your machine.
- Keep the `data/` directories in the repo so the app can persist extracted text, outputs, and learned rules.