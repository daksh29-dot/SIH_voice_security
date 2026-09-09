"""
generate_scenario_audio.py

Generates realistic audio files for the 5 SIH presentation scenarios
and saves them to static/audio/ or frontend/audio/ for instant playback.
"""

import os
from pathlib import Path
from gtts import gTTS
import soundfile as sf
import librosa

OUT_DIR = Path(__file__).resolve().parent.parent / "frontend" / "audio"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SCENARIOS = {
    "cbi_digital_arrest": {
        "text": "Hello, this is Inspector Rathore from Central Bureau of Investigation CBI Cyber Crime Branch New Delhi. An arrest warrant has been issued against your name in money laundering and narcotics trafficking. You are under digital arrest. Do not disconnect Skype call, immediately transfer funds to government verification account.",
        "lang": "en",
        "tld": "co.in"
    },
    "sbi_kyc_otp_theft": {
        "text": "Dear customer, your State Bank of India Net Banking KYC has expired today. Your bank account will be frozen within two hours. Please share the six digit OTP received on your mobile to update your Aadhaar card and PAN card immediately.",
        "lang": "en",
        "tld": "co.in"
    },
    "fedex_customs_drugs": {
        "text": "This is FedEx Customs Clearance at Mumbai Airport. A courier parcel sent under your PAN card to Taiwan contains five illegal passports and contraband drugs. Customs officers have seized the parcel. Transfer penalty fee now or police will arrest.",
        "lang": "en",
        "tld": "co.in"
    },
    "cloned_relative_emergency": {
        "text": "Papa, police ne pakad liya hai mujhe. Accident ho gaya car se. Hospital me hu, bail money chahiye fifty thousand rupees emergency. Please kisi ko mat batana, jaldi transfer karo.",
        "lang": "hi",
        "tld": "co.in"
    },
    "legitimate_colleague_call": {
        "text": "Hey, good afternoon! Just checking if we are still on for the project presentation and team sync at 4 PM today? Let me know once you review the slides.",
        "lang": "en",
        "tld": "co.in"
    }
}

def generate_all():
    print("[*] Generating realistic scenario audio files...")
    for key, data in SCENARIOS.items():
        mp3_path = OUT_DIR / f"{key}.mp3"
        wav_path = OUT_DIR / f"{key}.wav"
        
        print(f" -> Generating {key}...")
        tts = gTTS(text=data["text"], lang=data["lang"], tld=data["tld"], slow=False)
        tts.save(str(mp3_path))
        
        # Also convert to 16kHz WAV for backend processing
        y, sr = librosa.load(str(mp3_path), sr=16000, mono=True)
        sf.write(str(wav_path), y, 16000, subtype='PCM_16')
        print(f"    Saved: {wav_path}")

    print("[*] All scenario audio files generated successfully in frontend/audio/")

if __name__ == "__main__":
    generate_all()
