"""
backend/nlp/scam_intent.py

Rule-boosted Social Engineering & Telecom Fraud Intent Classifier for Project VISOR.
Detects critical telecom fraud patterns in real-time dialog transcripts:
  1. Urgent Financial Transfers ("wire the money", "urgent transfer", "account frozen")
  2. Credential & OTP Harvesting ("read back the OTP", "confirm your passcode", "SSN/PIN")
  3. Authority & Executive Impersonation Pressure ("I am the director", "do not verify with anyone else")
"""

import re
from typing import Dict, Any, List, Tuple, Optional


TELECOM_FRAUD_PATTERNS = {
    "URGENT_FINANCIAL_TRANSFER": {
        "title": "Urgent Financial Transfer Pressure",
        "severity": "HIGH",
        "weight": 0.90,
        "patterns": [
            r"\bwire\s*(?:the)?\s*money\b",
            r"\burgent\s*(?:bank)?\s*transfer\b",
            r"\baccount\s*(?:is)?\s*frozen\b",
            r"\baccount\s*(?:will\s*be)?\s*blocked\b",
            r"\btransfer\s*(?:the)?\s*funds?\b",
            r"\bsend\s*(?:the)?\s*money\s*immediately\b",
            r"\bimmediate\s*payment\b",
            r"\bprocessing\s*fee\b",
            r"\bbail\s*money\b",
            r"\bpenalty\s*(?:payment|charges?)\b",
            r"\bdemand\s*draft\b",
            r"\bemergency\s*(?:funds?|money)\b",
        ],
    },
    "CREDENTIAL_OTP_HARVESTING": {
        "title": "Credential & OTP Harvesting",
        "severity": "CRITICAL",
        "weight": 0.95,
        "patterns": [
            r"\b(?:read|tell|give|share)\s*(?:back)?\s*(?:the|your)?\s*otp\b",
            r"\bconfirm\s*(?:your)?\s*passcode\b",
            r"\b(?:ssn|social\s*security|pin|cvv)\b",
            r"\bone\s*time\s*password\b",
            r"\bpassword\s*(?:verification|reset)\b",
            r"\bsecurity\s*code\b",
            r"\bdebit\s*card\s*(?:number|details|expire)\b",
            r"\bnet\s*banking\s*(?:password|credentials)\b",
            r"\b(?:anydesk|teamviewer|rustdesk|quicksupport)\b",
            r"\botp\s*(?:batao|share\s*karo)\b",
            r"\bapk\s*install\b",
        ],
    },
    "AUTHORITY_IMPERSONATION_PRESSURE": {
        "title": "Authority & Executive Impersonation",
        "severity": "CRITICAL",
        "weight": 0.95,
        "patterns": [
            r"\bi\s*am\s*(?:the)?\s*(?:director|officer|inspector|commissioner|manager|superintendent)\b",
            r"\bdo\s*not\s*(?:verify|tell|speak|consult)\s*(?:with)?\s*(?:anyone|anybody)\b",
            r"\bdigital\s*arrest\b",
            r"\b(?:cbi|central\s*bureau|police\s*department|cyber\s*crime)\b",
            r"\barrest\s*warrant\b",
            r"\bsupreme\s*court\b",
            r"\benforcement\s*directorate\b",
            r"\bstay\s*on\s*(?:the)?\s*(?:line|call|video)\b",
            r"\bdo\s*not\s*(?:hang\s*up|disconnect)\b",
            r"\bconfidential\s*investigation\b",
            r"\bmoney\s*laundering\b",
            r"\bfir\s*(?:number|registered)\b",
        ],
    },
}


class ScamIntentClassifier:
    """
    Ultra-fast rule-boosted NLP intent and fraud indicator classifier (<2ms latency).
    Flags malicious social engineering dialog and computes a calibrated semantic threat score.
    """

    def __init__(self, patterns: Dict[str, Dict[str, Any]] = TELECOM_FRAUD_PATTERNS):
        self.patterns = patterns
        # Compile all regular expressions for rapid execution
        self._compiled_patterns = {}
        for cat_key, cat_data in self.patterns.items():
            compiled_list = [re.compile(p, re.IGNORECASE) for p in cat_data["patterns"]]
            self._compiled_patterns[cat_key] = (cat_data, compiled_list)

    def classify(self, text: str) -> Dict[str, Any]:
        """
        Scan dialog transcript for social engineering and scam intent indicators.

        Args:
            text: Raw transcript text string

        Returns:
            Dict[str, Any]:
                - "semantic_threat_score": float in [0.0, 1.0]
                - "triggered_intents": list of triggered category titles
                - "flagged_phrases": list of matched suspicious phrases
                - "is_threat": bool
                - "severity": "CLEAN" | "MEDIUM" | "HIGH" | "CRITICAL"
        """
        if not text or not text.strip():
            return {
                "semantic_threat_score": 0.0,
                "triggered_intents": [],
                "flagged_phrases": [],
                "is_threat": False,
                "severity": "CLEAN",
            }

        text_clean = text.strip()
        triggered_intents = []
        flagged_phrases = []
        highest_weight = 0.0
        match_count = 0
        severities = []

        for cat_key, (cat_data, regexes) in self._compiled_patterns.items():
            cat_matches = []
            for rx in regexes:
                found = rx.findall(text_clean)
                if found:
                    cat_matches.extend(found)

            if cat_matches:
                unique_cat_matches = list(set(cat_matches))
                flagged_phrases.extend(unique_cat_matches)
                triggered_intents.append(cat_data["title"])
                match_count += len(unique_cat_matches)
                severities.append(cat_data["severity"])
                if cat_data["weight"] > highest_weight:
                    highest_weight = cat_data["weight"]

        if not triggered_intents:
            return {
                "semantic_threat_score": 0.05,
                "triggered_intents": [],
                "flagged_phrases": [],
                "is_threat": False,
                "severity": "CLEAN",
            }

        # Deduplicate phrases
        unique_flagged = list(dict.fromkeys(flagged_phrases))

        # Compounding threat score:
        # Base threat starts at highest category weight (0.90 to 0.95)
        # Additional categories or multiple phrases compound toward 1.0
        base_threat = highest_weight * 0.70
        category_boost = (len(triggered_intents) - 1) * 0.12
        phrase_boost = min(0.15, (len(unique_flagged) - 1) * 0.05)

        raw_score = base_threat + category_boost + phrase_boost
        semantic_threat = float(min(0.99, max(0.50, raw_score)))

        severity = "CRITICAL" if "CRITICAL" in severities else "HIGH"

        return {
            "semantic_threat_score": round(semantic_threat, 4),
            "triggered_intents": triggered_intents,
            "flagged_phrases": unique_flagged,
            "is_threat": semantic_threat >= 0.50,
            "severity": severity,
        }


# Global shared singleton
_global_scam_classifier: Optional[ScamIntentClassifier] = None


def get_scam_classifier() -> ScamIntentClassifier:
    """Retrieve or initialize the global shared ScamIntentClassifier singleton."""
    global _global_scam_classifier
    if _global_scam_classifier is None:
        _global_scam_classifier = ScamIntentClassifier()
    return _global_scam_classifier
