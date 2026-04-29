"""
utils.py — ScanLens NLP Helpers
=================================
Provides:
  - clean_text()                 : normalise raw input
  - extract_scam_keywords()      : match against weighted keyword lexicon
  - detect_scam_patterns()       : regex-based structural pattern detection
  - compute_signal_scores()      : named boolean signal flags
  - SCAM_KEYWORD_WEIGHTS         : keyword → risk weight mapping
"""

import re
import string
from typing import List, Dict

# ------------------------------------------------------------------ #
#  SCAM KEYWORD LEXICON  (keyword → risk contribution weight)
# ------------------------------------------------------------------ #

SCAM_KEYWORD_WEIGHTS: Dict[str, float] = {
    # --- money / fee ---
    "registration fee":    0.35,
    "reg fee":             0.30,
    "processing fee":      0.30,
    "security deposit":    0.25,
    "refundable deposit":  0.20,
    "pay to join":         0.35,
    "send money":          0.35,
    "transfer amount":     0.28,
    "payment required":    0.30,
    "joining fee":         0.32,
    "training fee":        0.28,

    # --- unrealistic pay ---
    "earn rs":             0.20,
    "earn ₹":              0.20,
    "earn $":              0.18,
    "weekly salary":       0.15,
    "daily income":        0.15,
    "work from home":      0.12,
    "part time":           0.10,
    "passive income":      0.18,
    "unlimited earning":   0.22,
    "lakh per month":      0.20,
    "50000 per week":      0.28,

    # --- urgency ---
    "limited seats":       0.18,
    "apply immediately":   0.16,
    "urgent hiring":       0.18,
    "last date today":     0.20,
    "hurry":               0.12,
    "only today":          0.18,
    "act now":             0.16,
    "immediate joining":   0.14,
    "few slots left":      0.16,

    # --- no qualification ---
    "no experience":       0.14,
    "no qualification":    0.14,
    "fresher welcome":     0.08,
    "anyone can apply":    0.16,
    "housewife":           0.10,
    "students welcome":    0.08,
    "no skills required":  0.16,

    # --- communication red flags ---
    "whatsapp only":       0.20,
    "contact on whatsapp": 0.18,
    "message on whatsapp": 0.16,
    "call or whatsapp":    0.14,
    "gmail.com":           0.12,
    "yahoo.com":           0.12,
    "hotmail.com":         0.10,

    # --- personal info ---
    "aadhaar":             0.22,
    "pan card":            0.20,
    "bank account":        0.22,
    "account number":      0.20,
    "otp":                 0.18,
    "send your details":   0.20,
    "share your details":  0.18,

    # --- scam phrases ---
    "100% genuine":        0.22,
    "guaranteed job":      0.22,
    "trusted company":     0.12,
    "no interview":        0.20,
    "direct selection":    0.18,
    "work at home":        0.12,
    "data entry":          0.10,
    "typing job":          0.14,
    "online earning":      0.16,
    "mlm":                 0.24,
    "network marketing":   0.20,
    "referral bonus":      0.14,
}

# ------------------------------------------------------------------ #
#  TEXT CLEANING
# ------------------------------------------------------------------ #

def clean_text(text: str) -> str:
    """
    Normalise text for model input.
    - Lowercase
    - Remove URLs, emails, phone numbers
    - Collapse whitespace
    - Strip excess punctuation
    """
    text = text.lower()
    text = re.sub(r"http\S+|www\.\S+", " url ", text)
    text = re.sub(r"\S+@\S+\.\S+", " email ", text)
    text = re.sub(r"\b\d{10}\b", " phone ", text)
    text = re.sub(r"[^\w\s₹$%@.]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


# ------------------------------------------------------------------ #
#  KEYWORD EXTRACTION
# ------------------------------------------------------------------ #

def extract_scam_keywords(text: str) -> List[str]:
    """
    Find scam keywords present in the raw text.
    Returns list of matched keyword strings (original casing from text where possible).
    """
    lower = text.lower()
    found = []
    for kw in SCAM_KEYWORD_WEIGHTS:
        if kw in lower:
            # return keyword as-is for display in UI pills
            found.append(kw)
    # Deduplicate while preserving order
    seen = set()
    unique = []
    for kw in found:
        if kw not in seen:
            seen.add(kw)
            unique.append(kw)
    return unique


# ------------------------------------------------------------------ #
#  REGEX PATTERN DETECTION
# ------------------------------------------------------------------ #

def detect_scam_patterns(text: str) -> List[str]:
    """
    Regex-based structural scam pattern detection.
    Returns list of human-readable reason strings.
    """
    reasons = []
    lower   = text.lower()

    # Phone number prominently placed
    if re.search(r"\b[6-9]\d{9}\b", text):
        reasons.append("Contains a mobile number — scammers often use personal numbers instead of HR lines.")

    # Rupee amounts with large numbers
    if re.search(r"[₹rs\.]\s?[\d,]{4,}", lower):
        reasons.append("Mentions a specific large money amount — typical in fake salary or fee claims.")

    # All-caps words (shouting / pressure)
    caps_words = re.findall(r"\b[A-Z]{4,}\b", text)
    if len(caps_words) >= 3:
        reasons.append("Overuse of ALL-CAPS words — a pressure tactic common in spam messages.")

    # Excessive exclamation marks
    if text.count("!") >= 3:
        reasons.append("Multiple exclamation marks create artificial excitement — a common spam pattern.")

    # Free email domain in text
    if re.search(r"\b[\w.+-]+@(gmail|yahoo|hotmail|outlook)\.(com|in)\b", lower):
        reasons.append("Contains a free personal email address — genuine companies use corporate domains.")

    # WhatsApp link or mention
    if re.search(r"wa\.me|whatsapp\.com|whatsapp\s+me|msg\s+on\s+whatsapp", lower):
        reasons.append("Redirects to WhatsApp for communication — professional recruiters use official channels.")

    # Asking for OTP or sensitive data
    if re.search(r"\botp\b|\bone[\s-]?time[\s-]?password\b", lower):
        reasons.append("Asks for OTP — never share this; it can lead to account takeover.")

    return reasons


# ------------------------------------------------------------------ #
#  SIGNAL FLAGS
# ------------------------------------------------------------------ #

def compute_signal_scores(text: str) -> Dict[str, bool]:
    """
    Returns a dict of named boolean signals used by model.py for scoring.
    """
    lower = text.lower()

    return {
        "money_request": bool(re.search(
            r"(registration fee|reg fee|processing fee|pay|send money|deposit|joining fee|training fee|transfer)",
            lower
        )),
        "urgency": bool(re.search(
            r"(urgent|immediately|limited|hurry|last date|act now|today only|few slots|deadline)",
            lower
        )),
        "unrealistic_pay": bool(re.search(
            r"(earn\s?(rs|₹|\$)\s?\d|lakh|weekly salary|\d{4,}\s?per\s?(week|day|month)|unlimited earning|passive income)",
            lower
        )),
        "no_experience": bool(re.search(
            r"(no experience|no qualification|no degree|anyone can apply|no skills|fresher|housewife|student)",
            lower
        )),
        "personal_info_request": bool(re.search(
            r"(aadhaar|pan card|bank account|account number|otp|send your details|share your details|ifsc)",
            lower
        )),
        "whatsapp_only": bool(re.search(
            r"(whatsapp only|contact on whatsapp|message on whatsapp|call or whatsapp|wa\.me)",
            lower
        )),
        "generic_greeting": bool(re.search(
            r"^(dear candidate|dear applicant|hello candidate|hi friend|dear sir/madam)",
            lower.strip()
        )),
        "spelling_errors": _has_spelling_errors(text),
        "gmail_yahoo_domain": bool(re.search(
            r"@(gmail|yahoo|hotmail|rediffmail|outlook)\.(com|in)",
            lower
        )),
        "too_good": bool(re.search(
            r"(work from home|part[\s-]?time|easy money|earn daily|no target|flexible hours|be your own boss)",
            lower
        ) and re.search(
            r"(high salary|good salary|attractive package|\d{4,}|lakh|unlimited)",
            lower
        )),
    }


def _has_spelling_errors(text: str) -> bool:
    """
    Heuristic: flag texts with unusually high ratio of very short tokens
    or obvious repeated letter patterns (e.g. 'jobbbb', 'earnnnnn').
    """
    # Repeated letters (≥3 of the same char in a row)
    if re.search(r"(.)\1{2,}", text.lower()):
        return True
    # Very short words dominate (avg word len < 3 in a sentence with 10+ words)
    words = text.split()
    if len(words) >= 10:
        avg_len = sum(len(w) for w in words) / len(words)
        if avg_len < 3.2:
            return True
    return False


# ------------------------------------------------------------------ #
#  CONFIDENCE HELPER (used externally if needed)
# ------------------------------------------------------------------ #

def confidence_label(confidence: int) -> str:
    """Convert numeric confidence to human label."""
    if confidence >= 85:
        return "High"
    elif confidence >= 65:
        return "Medium"
    else:
        return "Low"
