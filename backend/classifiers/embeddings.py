# backend/classifiers/embeddings.py
"""
Lightweight embeddings helper using sentence-transformers.
Uses a small CPU-friendly model and caches prototype embeddings for doc types.
Returns cosine similarity score [0..1].
"""

import logging

_MODEL_NAME = "all-MiniLM-L6-v2"  # small and fast
_MODEL = None
_PROTOTYPES = {}
_PROTOTYPE_EMBS = {}

try:
    from sentence_transformers import SentenceTransformer, util
    import numpy as np
    _HAS_MODEL = True
except Exception:
    _HAS_MODEL = False
    logging.getLogger(__name__).warning(
        "sentence-transformers not available. Embedding fallback disabled. Install sentence-transformers to enable it."
    )

# Representative prototype texts per label (short, focused)
_PROTOTYPE_TEXTS = {
    "W2": [
        "Form W-2 Wage and Tax Statement", 
        "Employee's social security wages", 
        "Wage and Tax Statement Form W-2"
    ],
    "Paystub": [
        "Year-to-date earnings", 
        "Net pay", 
        "Gross pay", 
        "Pay period"
    ],
    "BankStatement": [
        "Statement period", 
        "Ending balance", 
        "Available balance", 
        "Account number"
    ],
    "ID": [
        "Driver license", 
        "Date of birth", 
        "identification number", 
        "ID card"
    ],
    "TWN": [
        "The Work Number", 
        "employment verification", 
        "employer id The Work Number"
    ],
    "URLA": [
        "Uniform Residential Loan Application", 
        "Form 1003", 
        "URLA mortgage application"
    ],
    "CreditReport": [
        "credit report", 
        "Equifax", 
        "TransUnion", 
        "Experian"
    ],
    # add more prototypes as needed
}

def _ensure_model():
    global _MODEL, _PROTOTYPE_EMBS
    if not _HAS_MODEL:
        return False
    if _MODEL is None:
        _MODEL = SentenceTransformer(_MODEL_NAME)
    if not _PROTOTYPE_EMBS:
        # compute prototype embeddings for each label by averaging
        for label, texts in _PROTOTYPE_TEXTS.items():
            embs = _MODEL.encode(texts, convert_to_tensor=True)
            # mean pooling
            avg = util.mean_pooling(embs, None) if hasattr(util, "mean_pooling") else embs.mean(axis=0)
            _PROTOTYPE_EMBS[label] = avg
    return True

def get_embedding(text: str):
    """
    Return embedding tensor/ndarray for a text. None if model missing.
    """
    if not _HAS_MODEL:
        return None
    _ensure_model()
    return _MODEL.encode(text, convert_to_tensor=True)

def best_label_by_embedding(text: str):
    """
    Returns (best_label, similarity_score) where score is in [0..1].
    If embeddings unavailable, returns (None, 0.0)
    """
    if not _HAS_MODEL:
        return None, 0.0
    _ensure_model()
    import torch
    emb = _MODEL.encode(text, convert_to_tensor=True)
    best_label = None
    best_score = -1.0
    for label, prot_emb in _PROTOTYPE_EMBS.items():
        # cosine similarity via util.pytorch_cos_sim or util.cos_sim
        try:
            score = util.cos_sim(emb, prot_emb).item()  # between -1 and 1
        except Exception:
            # fallback manual
            emb_np = emb.cpu().numpy()
            prot_np = prot_emb.cpu().numpy()
            denom = (np.linalg.norm(emb_np) * np.linalg.norm(prot_np))
            score = float(np.dot(emb_np, prot_np) / denom) if denom > 0 else 0.0
        # normalize from [-1,1] to [0,1]
        score_normal = (score + 1.0) / 2.0
        if score_normal > best_score:
            best_score = score_normal
            best_label = label
    # clamp to 0..1
    best_score = max(0.0, min(1.0, float(best_score)))
    return best_label, best_score
