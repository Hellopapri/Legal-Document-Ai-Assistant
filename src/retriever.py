from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Dict, List

try:
    import chromadb
except Exception:  # pragma: no cover - handled at runtime
    chromadb = None


BASE_DIR = Path(__file__).resolve().parents[1]
CHROMA_DIR = BASE_DIR / "data" / "chroma"
CHROMA_DIR.mkdir(parents=True, exist_ok=True)


def chunk_text(text: str, chunk_size: int = 800, overlap: int = 100) -> List[str]:
    """Split text into overlapping chunks of 500-800 characters for retrieval."""
    if not text or not text.strip():
        return []
    
    text = text.strip()
    chunks = []
    start = 0
    
    while start < len(text):
        # Try to end at a sentence boundary near chunk_size
        end = min(len(text), start + chunk_size)
        
        # Look for a sentence boundary (period, newline) before end
        if end < len(text):
            for i in range(end, max(start + 500, end - 100), -1):
                if text[i] in '.\n':
                    end = i + 1
                    break
        
        chunk = text[start:end].strip()
        if chunk and len(chunk) > 100:  # Only include chunks with meaningful content
            chunks.append(chunk)
        
        if end >= len(text):
            break
        
        # Move start forward with overlap
        start = end - overlap
    
    return chunks


def _get_client():
    if chromadb is None:
        return None
    return chromadb.PersistentClient(path=str(CHROMA_DIR))


def build_or_update_index(document_name: str, extracted_text: str) -> Dict[str, int]:
    chunks = chunk_text(extracted_text)
    if not chunks:
        return {"chunks": 0}

    client = _get_client()
    if client is None:
        return {"chunks": len(chunks)}

    collection = client.get_or_create_collection(name="legal_documents")
    ids = []
    metadatas = []
    for index, chunk in enumerate(chunks):
        chunk_id = hashlib.sha1(f"{document_name}-{index}-{chunk}".encode("utf-8")).hexdigest()
        ids.append(chunk_id)
        metadatas.append({"document_name": document_name, "chunk_index": index})
    collection.upsert(ids=ids, documents=chunks, metadatas=metadatas)
    return {"chunks": len(chunks)}


def _rank_chunks(query: str, chunks: List[str], top_k: int) -> List[Dict]:
    query_tokens = set(query.lower().split())
    scored = []
    for index, chunk in enumerate(chunks):
        chunk_tokens = set(chunk.lower().split())
        overlap = len(query_tokens.intersection(chunk_tokens))
        score = overlap + min(len(chunk), 1000) / 1000.0
        scored.append(
            {
                "id": f"mock-{index}",
                "text": chunk,
                "metadata": {"chunk_index": index, "source": "mock"},
                "score": score,
            }
        )
    scored.sort(key=lambda item: item["score"], reverse=True)
    return scored[:top_k]


def retrieve_evidence(query: str, document_name: str, extracted_text: str, structured_data: Dict, top_k: int = 5) -> List[Dict]:
    """Retrieve top-k relevant chunks based on query and structured context."""
    chunks = chunk_text(extracted_text)
    if not chunks:
        return []

    client = _get_client()
    if client is None:
        return _rank_chunks(query, chunks, min(top_k, 5))

    collection = client.get_or_create_collection(name="legal_documents")
    try:
        query_text = f"{query} {structured_data.get('document_type', '')} {' '.join(structured_data.get('key_facts', [])[:2])}"
        results = collection.query(
            query_texts=[query_text],
            n_results=min(top_k, len(chunks)),
            include=["documents", "metadatas", "distances"],
        )
    except Exception:
        return _rank_chunks(query, chunks, min(top_k, 5))

    documents = results.get("documents", [[]])[0] if results.get("documents") else []
    metadatas = results.get("metadatas", [[]])[0] if results.get("metadatas") else []
    distances = results.get("distances", [[]])[0] if results.get("distances") else []
    
    evidence = []
    for index, text in enumerate(documents):
        # Convert distance to relevance score (0-1, higher is better)
        raw_distance = distances[index] if index < len(distances) else 1.0
        relevance_score = max(0.0, 1.0 - raw_distance)  # Chroma returns distances, convert to similarity
        
        chunk_idx = metadatas[index].get("chunk_index", index) if index < len(metadatas) else index
        evidence.append(
            {
                "id": f"evidence-{index + 1}",
                "text": text,
                "metadata": metadatas[index] if index < len(metadatas) else {"chunk_index": index},
                "relevance_score": round(max(0.0, min(1.0, relevance_score)), 2),
                "chunk_number": chunk_idx + 1,
            }
        )
    
    return evidence[:min(top_k, 5)]