"""
multi_modal_engine.py

Core 4-Pillar Multi-Modal Defense & Dynamic Risk Orchestrator
for SIH Voice Security System.

Pillars:
1. Voice Clone Check (Audio Deepfake / Acoustic Forensics)
2. Caller Check (Telecom CLI, TRAI DND, STIR/SHAKEN, Virtual SIM / VoIP)
3. Scam Words Check (NLP Code-Mixed Intent: CBI, Digital Arrest, KYC, OTP, Customs)
4. Match Check (Zero-Enrollment Voice Biometric & Acoustic Consistency)
"""

import re
import time
import math
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional

# ─────────────────────────────────────────────────────────────────────────────
# 1. SCAM PATTERNS & CODE-MIXED NLP INTENT ENGINE (Ultra-Fast <5ms)
# ─────────────────────────────────────────────────────────────────────────────

SCAM_CATEGORIES = {
    "DIGITAL_ARREST_CBI": {
        "title": "CBI / Police Digital Arrest Extortion",
        "severity": "CRITICAL",
        "weight": 1.0,
        "keywords": [
            r"digital\s*arrest", r"cbi", r"central\s*bureau", r"police", r"cyber\s*crime",
            r"arrest\s*warrant", r"money\s*laundering", r"supreme\s*court", r"enforcement\s*directorate",
            r"ed\s*office", r"skype\s*call", r"video\s*call\s*pe\s*raho", r"don't\s*disconnect",
            r"station\s*aana\s*padega", r"jail", r"fir\s*number", r"narcotics", r"illegal\s*drugs"
        ],
        "description": "Scammer poses as Police/CBI claiming fake digital arrest and demanding immediate fund transfer."
    },
    "CUSTOMS_PARCEL_FEDEX": {
        "title": "Customs / FedEx Illegal Parcel Scam",
        "severity": "CRITICAL",
        "weight": 0.95,
        "keywords": [
            r"customs", r"parcel", r"fedex", r"dhl", r"courier", r"mumbai\s*airport",
            r"taiwan", r"illegal\s*passport", r"contraband", r"drugs\s*found", r"customs\s*clearance",
            r"parcel\s*seize", r"customs\s*officer"
        ],
        "description": "Scammer claims an intercepted illegal parcel in victim's name to extort penalty payments."
    },
    "BANK_KYC_OTP_THEFT": {
        "title": "Bank Account KYC & OTP Theft",
        "severity": "HIGH",
        "weight": 0.90,
        "keywords": [
            r"otp", r"one\s*time\s*password", r"kyc\s*expire", r"kyc\s*update", r"aadhaar\s*link",
            r"pan\s*card\s*block", r"account\s*freeze", r"account\s*block", r"debit\s*card\s*expire",
            r"credit\s*card\s*limit", r"sbi\s*manager", r"hdfc\s*security", r"cvv", r"net\s*banking\s*password",
            r"anydesk", r"teamviewer", r"rustdesk", r"apk\s*install", r"share\s*otp", r"otp\s*batao"
        ],
        "description": "Fraudster impersonates bank official claiming KYC expiry to steal OTP or banking credentials."
    },
    "URGENT_FAMILY_SOS": {
        "title": "Voice Cloned Relative SOS Emergency",
        "severity": "CRITICAL",
        "weight": 0.95,
        "keywords": [
            r"accident\s*ho\s*gaya", r"hospital\s*me\s*hu", r"bail\s*money", r"police\s*ne\s*pakad\s*liya",
            r"emergency\s*paisa", r"urgent\s*send\s*money", r"don't\s*tell\s*mom", r"urgent\s*transfer",
            r"hostage", r"kidnap"
        ],
        "description": "AI-cloned voice of a family member claiming urgent emergency/hospitalization requiring immediate money."
    },
    "LOTTERY_KBC_FRAUD": {
        "title": "Lottery / KBC / Investment Fraud",
        "severity": "MEDIUM",
        "weight": 0.75,
        "keywords": [
            r"kbc", r"lottery", r"25\s*lakh", r"prize\s*money", r"guaranteed\s*return",
            r"processing\s*fee", r"claim\s*amount", r"tax\s*deposit\s*karo"
        ],
        "description": "Fake prize/lottery notification requiring upfront tax or processing fee payment."
    }
}


def analyze_scam_intent(transcript: str) -> Dict[str, Any]:
    """
    Lightweight, ultra-fast Code-Mixed NLP Scam Intent Detector.
    Runs in < 5ms.
    """
    if not transcript or not transcript.strip():
        return {
            "risk_score": 0.05,
            "detected_intent": "NORMAL_CONVERSATION",
            "matched_keywords": [],
            "category_details": None,
            "highlighted_transcript": transcript or "",
            "is_threat": False
        }

    text_lower = transcript.lower()
    matched_categories = []
    all_matched_words = []
    total_weighted_score = 0.0

    for cat_id, cat_info in SCAM_CATEGORIES.items():
        cat_matches = []
        for pat in cat_info["keywords"]:
            found = re.findall(pat, text_lower)
            if found:
                cat_matches.extend(found)
        
        if cat_matches:
            unique_matches = list(set(cat_matches))
            all_matched_words.extend(unique_matches)
            # Calculate category confidence based on matches and weight
            match_intensity = min(1.0, 0.4 + (len(unique_matches) * 0.2))
            cat_score = match_intensity * cat_info["weight"]
            matched_categories.append({
                "id": cat_id,
                "title": cat_info["title"],
                "severity": cat_info["severity"],
                "score": round(cat_score, 3),
                "matches": unique_matches,
                "description": cat_info["description"]
            })
            total_weighted_score = max(total_weighted_score, cat_score)

    # Sort categories by score descending
    matched_categories.sort(key=lambda x: x["score"], reverse=True)

    # Boost score if multiple trigger words found
    if len(all_matched_words) >= 3:
        total_weighted_score = min(0.99, total_weighted_score + 0.15)
    elif len(all_matched_words) >= 1:
        total_weighted_score = max(0.55, total_weighted_score)

    primary_category = matched_categories[0] if matched_categories else None

    return {
        "risk_score": round(total_weighted_score, 3),
        "detected_intent": primary_category["title"] if primary_category else "BENIGN_CALL",
        "category_id": primary_category["id"] if primary_category else "CLEAN",
        "severity": primary_category["severity"] if primary_category else "LOW",
        "matched_keywords": list(set(all_matched_words)),
        "all_categories": matched_categories,
        "is_threat": total_weighted_score >= 0.50
    }


# ─────────────────────────────────────────────────────────────────────────────
# 2. CALLER ID & TELECOM SIGNALING CHECKER (TRAI / DND / STIR/SHAKEN)
# ─────────────────────────────────────────────────────────────────────────────

KNOWN_SCAM_PREFIXES = ["+1876", "+234", "+92", "+371", "+882", "+4470"]
KNOWN_HIGH_RISK_VOIP_CARRIERS = ["Twilio-VoIP-Proxy", "VirtualPBX-Cloud", "Unknown-SIP-Gateway", "Spoofed-CLI-Tunnel"]

def check_caller_telecom(
    phone_number: str,
    carrier: str = "Jio-Telecom",
    stir_shaken_attestation: str = "A",
    voip_flag: bool = False,
    trai_dnd_registered: bool = True
) -> Dict[str, Any]:
    """
    Simulates TRAI DND, STIR/SHAKEN CLI verification, and Telecom Signaling checks.
    Runs in < 2ms.
    """
    risk_points = 0.0
    anomalies = []

    clean_num = phone_number.strip().replace(" ", "").replace("-", "")

    # 1. STIR / SHAKEN Attestation Check (A = Full, B = Partial, C = Gateway/No Auth)
    if stir_shaken_attestation.upper() == "C":
        risk_points += 0.45
        anomalies.append("STIR/SHAKEN Level-C: Caller ID cannot be cryptographically verified by originating carrier.")
    elif stir_shaken_attestation.upper() == "B":
        risk_points += 0.20
        anomalies.append("STIR/SHAKEN Level-B: Partial verification. Possible call-forwarding or virtual PBX.")

    # 2. VoIP / Virtual SIM / Proxy Check
    if voip_flag or any(c.lower() in carrier.lower() for c in ["voip", "sip", "proxy", "virtual"]):
        risk_points += 0.35
        anomalies.append(f"Carrier flagged as Virtual VoIP/SIP Tunnel ({carrier}) commonly used in spoofing.")

    # 3. Known Scam Country Codes / International CLI spoofing
    for prefix in KNOWN_SCAM_PREFIXES:
        if clean_num.startswith(prefix):
            risk_points += 0.40
            anomalies.append(f"High-risk International Calling Code ({prefix}) associated with robocalls.")
            break

    # 4. TRAI DND Blacklist / Commercial Bulk Line check
    if not trai_dnd_registered:
        risk_points += 0.15
        anomalies.append("Number not registered in TRAI Enterprise Telemarketer Registry.")

    # 5. Suspicious Government / Bank Impersonation numbers (e.g. 100, 1930, 112 spoofed via VoIP)
    if clean_num in ["100", "112", "1930", "+91100", "+911930", "1800112211"]:
        if voip_flag or stir_shaken_attestation.upper() != "A":
            risk_points += 0.60
            anomalies.append("CRITICAL: Government/Emergency Police CLI spoofed from unauthenticated gateway!")

    final_score = min(0.99, max(0.02, risk_points))

    return {
        "risk_score": round(final_score, 3),
        "phone_number": phone_number,
        "carrier": carrier,
        "stir_shaken_level": stir_shaken_attestation.upper(),
        "is_voip": voip_flag,
        "trai_verified": trai_dnd_registered and (stir_shaken_attestation.upper() == "A"),
        "anomalies": anomalies,
        "is_spoofed_cli": final_score >= 0.50
    }


# ─────────────────────────────────────────────────────────────────────────────
# 3. VOICE MATCH / ACOUSTIC BIOMETRICS CHECK
# ─────────────────────────────────────────────────────────────────────────────

def check_voice_biometrics(
    voice_clone_score: float,
    acoustic_consistency_score: Optional[float] = None
) -> Dict[str, Any]:
    """
    Evaluates Zero-Enrollment Acoustic Consistency & Biometric match probability.
    """
    if acoustic_consistency_score is None:
        # Synthesize consistency based on naturalness
        if voice_clone_score > 0.8:
            acoustic_consistency_score = round(0.15 + (1.0 - voice_clone_score) * 0.2, 3)
        elif voice_clone_score < 0.2:
            acoustic_consistency_score = round(0.85 + (0.2 - voice_clone_score) * 0.5, 3)
        else:
            acoustic_consistency_score = 0.50

    # Risk is inverse of biometric match trust
    risk_score = round(max(0.01, min(0.99, 1.0 - acoustic_consistency_score)), 3)

    return {
        "risk_score": risk_score,
        "biometric_trust": acoustic_consistency_score,
        "is_enrolled_match": acoustic_consistency_score >= 0.70,
        "acoustic_stability": "STABLE" if acoustic_consistency_score >= 0.6 else "SYNTHETIC_JITTER"
    }


# ─────────────────────────────────────────────────────────────────────────────
# 4. DYNAMIC RISK ORCHESTRATOR & POLICY ENGINE
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class MultiModalAssessment:
    composite_risk_score: float
    composite_trust_score: float
    policy_action: str
    action_color: str
    pillar_breakdown: Dict[str, Any]
    threat_summary: str
    execution_time_ms: float
    timestamp: str


def orchestrate_dynamic_risk(
    voice_clone_risk: float,
    caller_cli_risk: float,
    scam_words_risk: float,
    biometric_mismatch_risk: float,
    pillar_weights: Optional[Dict[str, float]] = None
) -> Dict[str, Any]:
    """
    Combines the 4 pillars into a single composite dynamic risk score (0.0 - 1.0).
    Executes Policy Thresholds:
    - Low Risk  (<0.25 Risk / >0.75 Trust) -> PROCEED_NORMALLY (Green)
    - Med Risk  (0.25 - 0.60 Risk)         -> STEP_UP_MFA (Amber)
    - High Risk (>0.60 Risk / <0.40 Trust) -> BLOCK_AND_HOLD (Red)
    """
    weights = pillar_weights or {
        "voice": 0.35,
        "scam_words": 0.30,
        "caller": 0.20,
        "biometrics": 0.15
    }

    # Normalize weights
    w_sum = sum(weights.values())
    w_voice = weights["voice"] / w_sum
    w_scam = weights["scam_words"] / w_sum
    w_caller = weights["caller"] / w_sum
    w_bio = weights["biometrics"] / w_sum

    # Base weighted sum
    composite_risk = (
        (voice_clone_risk * w_voice) +
        (scam_words_risk * w_scam) +
        (caller_cli_risk * w_caller) +
        (biometric_mismatch_risk * w_bio)
    )

    # Nonlinear Risk Escalation: If Voice Clone + Scam Intent are BOTH severe, escalate risk to critical
    if voice_clone_risk >= 0.85 and scam_words_risk >= 0.75:
        composite_risk = max(composite_risk, 0.94)
    elif scam_words_risk >= 0.90 and caller_cli_risk >= 0.60:
        composite_risk = max(composite_risk, 0.88)

    composite_risk = round(min(0.99, max(0.01, composite_risk)), 3)
    composite_trust = round(1.0 - composite_risk, 3)

    # Check Policy Thresholds
    if composite_risk >= 0.60:
        policy_action = "BLOCK_AND_HOLD"
        action_label = "Auto-Terminate Call & Freeze Banking API"
        action_color = "red"
        action_recommendation = "HIGH THREAT DETECTED: Cloned voice / Extortion scam in progress. Terminate connection immediately and alert cyber cell."
    elif composite_risk >= 0.25:
        policy_action = "STEP_UP_MFA"
        action_label = "Prompt Out-of-Band Step-Up MFA Challenge"
        action_color = "amber"
        action_recommendation = "MEDIUM RISK: Suspicious conversation patterns or unverified caller. Require biometric / OTP confirmation before approving transaction."
    else:
        policy_action = "PROCEED_NORMALLY"
        action_label = "Verified Safe • Proceed Normally"
        action_color = "green"
        action_recommendation = "LOW RISK: Voice acoustics natural, caller authenticated, no malicious patterns detected."

    return {
        "composite_risk_score": composite_risk,
        "composite_trust_score": composite_trust,
        "risk_percentage": round(composite_risk * 100, 1),
        "trust_percentage": round(composite_trust * 100, 1),
        "policy_action": policy_action,
        "action_label": action_label,
        "action_color": action_color,
        "recommendation": action_recommendation,
        "pillar_scores": {
            "voice_clone_risk": round(voice_clone_risk, 3),
            "caller_cli_risk": round(caller_cli_risk, 3),
            "scam_words_risk": round(scam_words_risk, 3),
            "biometric_mismatch_risk": round(biometric_mismatch_risk, 3)
        }
    }
