# backend/classifiers/heuristics.py
import re
from typing import List, Tuple
import logging

# Try to import embeddings helper
try:
    from classifiers.embeddings import best_label_by_embedding
    _HAS_EMBEDDINGS = True
except Exception:
    _HAS_EMBEDDINGS = False
    logging.getLogger(__name__).warning("Embeddings helper not available; running heuristics-only.")

# Simple keyword signatures
DOC_SIGNATURES = {
    "W2": ["form w-2", "wage and tax statement", "w-2"],
    "Paystub": ["year-to-date", "gross pay", "net pay", "pay period", "paystub", "earnings"],
    "BankStatement": ["statement period", "ending balance", "available balance", "account number", "bank statement"],
    "ID": ["driver license", "date of birth", "identification", "id number", "id card"],
    "TWN": ["the work number", "work number", "theworknumber", "employment verification"],
    "URLA": ["1003", "urla", "uniform residential loan application", "mortgage application", "form 1003"],
    "CreditReport": ["credit score", "equifax", "transunion", "experian", "credit report"]
}

# small helper to build snippet
def make_snippet(text: str, max_len: int = 300):
    clean = " ".join(text.split())
    return clean[:max_len] + ("..." if len(clean) > max_len else "")

def heuristic_score(text: str, keywords: List[str]) -> float:
    txt = text.lower()
    hits = 0
    for k in keywords:
        if k in txt:
            hits += 1
    return hits / max(1, len(keywords))

def _embedding_label_and_score(text: str):
    """Return (label, score) from embedding fallback, or (None,0.0) if unavailable."""
    if not _HAS_EMBEDDINGS:
        return None, 0.0
    try:
        label, score = best_label_by_embedding(text)
        return label, float(score)
    except Exception as e:
        logging.getLogger(__name__).warning(f"Embedding classification failed: {e}")
        return None, 0.0

# blending weights (tuneable)
HEUR_WEIGHT = 0.55
EMBED_WEIGHT = 0.45

def classify_single_text(text: str) -> Tuple[str, float, list, str]:
    """
    Returns (best_label, blended_score, reasons[], snippet)
    - Uses heuristics and an embedding-based fallback; blends confidence.
    - If embedding model not present, returns heuristic result only.
    """
    scores = {}
    reasons = {}
    txt = text or ""
    for label, keys in DOC_SIGNATURES.items():
        sc = heuristic_score(txt, keys)
        scores[label] = sc
        matched = [k for k in keys if k in txt.lower()]
        reasons[label] = matched

    # heuristic best
    best_heur = max(scores, key=lambda k: scores[k])
    heur_score = float(scores[best_heur])

    # embedding best (may be None)
    emb_label, emb_score = _embedding_label_and_score(txt)

    # build blended scores: we will compute a blended score for each candidate label
    blended_scores = {}
    for label in DOC_SIGNATURES.keys():
        h = float(scores.get(label, 0.0))
        e = emb_score if (emb_label == label) else 0.0
        blended = HEUR_WEIGHT * h + EMBED_WEIGHT * e
        blended_scores[label] = blended

    # pick best blended
    best_label = max(blended_scores, key=lambda k: blended_scores[k])
    blended_score = float(blended_scores[best_label])

    # If embeddings are not available, fall back to heuristic-only label/score
    if not _HAS_EMBEDDINGS:
        best_label = best_heur
        blended_score = heur_score

    snippet = make_snippet(txt, 400)
    # Provide reasons primarily from heuristic (which are explainable)
    reason_list = reasons.get(best_label, [])
    # If embedding contributed and disagrees, append a note
    if _HAS_EMBEDDINGS and emb_label and emb_label != best_label and emb_score > 0.6:
        reason_list.append(f"embedding_prefers:{emb_label}({round(emb_score,3)})")
    return best_label, round(blended_score, 3), reason_list, snippet

def classify_texts(file_text_pairs):
    """
    file_text_pairs: list of (filename, text)
    returns summary dict
    """
    found = []
    for fname, txt in file_text_pairs:
        label, score, reasons, snippet = classify_single_text(txt)
        found.append({
            "file": fname,
            "type": label,
            "confidence": float(score),
            "reasons": reasons,
            "snippet": snippet
        })
    # simple summary: list types found and counts
    types = {}
    for f in found:
        types[f["type"]] = types.get(f["type"], 0) + 1
    return {"found_types": list(types.keys()), "file_count": len(found), "counts": types}
