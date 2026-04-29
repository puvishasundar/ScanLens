"""
model.py — ScanLens Prediction Engine
======================================
Senior-level fake job / scam detection using:
  - TF-IDF vectorizer (trained on data.csv)
  - Logistic Regression classifier
  - Rule-based NLP signal layer
  - Calibrated confidence scoring
  - Explainable risk breakdown

Returns a dict consumed by app.py:
  { score, confidence, label, keywords, reasons }
"""

import re
import math
import pickle
import os
import numpy as np
from utils import (
    clean_text,
    extract_scam_keywords,
    detect_scam_patterns,
    compute_signal_scores,
    SCAM_KEYWORD_WEIGHTS,
)

# ------------------------------------------------------------------ #
#  MODEL LOADING (lazy — trains once if no saved model found)
# ------------------------------------------------------------------ #

_MODEL_PATH   = "scanlens_model.pkl"
_VECTORIZER_PATH = "scanlens_vectorizer.pkl"

_classifier  = None
_vectorizer  = None


def _load_or_train_model():
    """Load persisted model or train a fresh one from data.csv."""
    global _classifier, _vectorizer

    if _classifier is not None:
        return

    if os.path.exists(_MODEL_PATH) and os.path.exists(_VECTORIZER_PATH):
        with open(_MODEL_PATH, "rb") as f:
            _classifier = pickle.load(f)
        with open(_VECTORIZER_PATH, "rb") as f:
            _vectorizer = pickle.load(f)
        return

    # ---- train from scratch ----
    try:
        import pandas as pd
        from sklearn.linear_model import LogisticRegression
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.pipeline import Pipeline

        df = pd.read_csv("data.csv")
        # Expected columns: text, label  (label: 0=genuine, 1=fake)
        df = df.dropna(subset=["text", "label"])
        df["clean"] = df["text"].apply(clean_text)

        _vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),
            max_features=8000,
            sublinear_tf=True,
            min_df=2,
        )
        X = _vectorizer.fit_transform(df["clean"])
        y = df["label"].astype(int)

        _classifier = LogisticRegression(
            C=1.5,
            class_weight="balanced",
            max_iter=500,
            solver="lbfgs",
        )
        _classifier.fit(X, y)

        with open(_MODEL_PATH, "wb") as f:
            pickle.dump(_classifier, f)
        with open(_VECTORIZER_PATH, "wb") as f:
            pickle.dump(_vectorizer, f)

    except Exception:
        # Fallback: rule-only mode (no CSV available)
        _classifier = None
        _vectorizer = None


# ------------------------------------------------------------------ #
#  RISK SCORE CALCULATION
# ------------------------------------------------------------------ #

def _ml_score(text: str) -> float:
    """
    Returns ML-based probability of fake (0–1).
    Falls back to 0.5 (neutral) if model not available.
    """
    _load_or_train_model()
    if _classifier is None or _vectorizer is None:
        return 0.5

    clean = clean_text(text)
    X = _vectorizer.transform([clean])
    prob = _classifier.predict_proba(X)[0]
    fake_idx = list(_classifier.classes_).index(1)
    return float(prob[fake_idx])


def _rule_score(text: str) -> tuple[float, list[str], list[str]]:
    """
    Rule-based signal scoring. Returns (score 0–1, reasons, keywords).
    """
    signals     = compute_signal_scores(text)
    keywords    = extract_scam_keywords(text)
    patterns    = detect_scam_patterns(text)

    reasons: list[str] = []
    raw_score   = 0.0

    # --- keyword weight accumulation ---
    kw_score = 0.0
    for kw in keywords:
        weight = SCAM_KEYWORD_WEIGHTS.get(kw.lower(), 0.04)
        kw_score += weight
    kw_score = min(kw_score, 0.50)   # cap contribution

    # --- named signal penalties ---
    if signals["money_request"]:
        raw_score += 0.30
        reasons.append("Requests money or a registration fee — a major red flag in any job offer.")
    if signals["urgency"]:
        raw_score += 0.15
        reasons.append("Uses urgent language (e.g. 'apply immediately', 'limited seats') to pressure the reader.")
    if signals["unrealistic_pay"]:
        raw_score += 0.20
        reasons.append("Promises unrealistically high earnings with little or no experience required.")
    if signals["no_experience"]:
        raw_score += 0.10
        reasons.append("Claims no experience or qualifications needed — common in scam postings.")
    if signals["personal_info_request"]:
        raw_score += 0.20
        reasons.append("Asks for personal or financial details upfront (Aadhaar, bank account, etc.).")
    if signals["whatsapp_only"]:
        raw_score += 0.15
        reasons.append("Communication limited to WhatsApp — legitimate recruiters use official email/portals.")
    if signals["generic_greeting"]:
        raw_score += 0.08
        reasons.append("Generic impersonal greeting — no company name or job title specified.")
    if signals["spelling_errors"]:
        raw_score += 0.07
        reasons.append("Contains repeated spelling or grammar errors, common in scam messages.")
    if signals["gmail_yahoo_domain"]:
        raw_score += 0.12
        reasons.append("Recruiter uses a free email domain (Gmail/Yahoo) instead of a corporate address.")
    if signals["too_good"]:
        raw_score += 0.18
        reasons.append("Offer sounds too good to be true — extremely high pay for minimal work from home.")

    # --- pattern bonuses ---
    for p in patterns:
        if p not in reasons:
            reasons.append(p)
            raw_score += 0.06

    raw_score += kw_score
    return min(raw_score, 1.0), reasons, keywords


# ------------------------------------------------------------------ #
#  ENSEMBLE + CALIBRATION
# ------------------------------------------------------------------ #

def _blend(ml: float, rule: float, text: str) -> float:
    """
    Weighted blend: ML gets more weight on longer texts; rules dominate short ones.
    """
    word_count = len(text.split())
    if word_count < 15:
        ml_weight   = 0.20
        rule_weight = 0.80
    elif word_count < 50:
        ml_weight   = 0.40
        rule_weight = 0.60
    else:
        ml_weight   = 0.55
        rule_weight = 0.45

    return ml * ml_weight + rule * rule_weight


def _calibrate_confidence(blend_score: float, keyword_count: int) -> int:
    """
    Confidence = how certain the model is, regardless of direction.
    More keywords + extreme scores → higher confidence.
    """
    base = abs(blend_score - 0.5) * 2         # 0 = uncertain, 1 = very sure
    kw_bonus = min(keyword_count * 0.03, 0.20)
    raw = base + kw_bonus
    # squeeze to 55–98 range (never claim 100%)
    confidence = 55 + int(raw * 43)
    return min(confidence, 98)


def _to_label(score: int) -> str:
    if score < 40:
        return "Likely Genuine"
    elif score < 70:
        return "Suspicious"
    else:
        return "Likely Fake"


# ------------------------------------------------------------------ #
#  PUBLIC API — called by app.py
# ------------------------------------------------------------------ #

def predict_risk(text: str) -> dict:
    """
    Main entry point for app.py.

    Parameters
    ----------
    text : str
        Raw user-pasted message.

    Returns
    -------
    dict with keys:
        score       : int  0–100
        confidence  : int  0–100
        label       : str  "Likely Genuine" | "Suspicious" | "Likely Fake"
        keywords    : list[str]   flagged keywords found in text
        reasons     : list[str]   human-readable explanations
    """
    if not text or not text.strip():
        return {
            "score":      0,
            "confidence": 0,
            "label":      "No Input",
            "keywords":   [],
            "reasons":    [],
        }

    ml_prob                      = _ml_score(text)
    rule_prob, reasons, keywords = _rule_score(text)

    blend    = _blend(ml_prob, rule_prob, text)
    score    = min(int(round(blend * 100)), 100)
    conf     = _calibrate_confidence(blend, len(keywords))
    label    = _to_label(score)

    # keep reasons capped at 5 most impactful
    reasons = reasons[:5]

    return {
        "score":      score,
        "confidence": conf,
        "label":      label,
        "keywords":   keywords,
        "reasons":    reasons,
    }
