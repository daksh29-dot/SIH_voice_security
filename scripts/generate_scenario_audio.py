"""
generate_scenario_audio.py

Generates realistic audio files for the 5 SIH presentation scenarios
and saves them to static/audio/ or frontend/audio/ for instant playback.
"""

import asyncio
import os
import sys
from pathlib import Path
import edge_tts
import soundfile as sf

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from audio_preprocessing import load_audio

OUT_DIR = Path(__file__).resolve().parent.parent / "frontend" / "audio"
OUT_DIR.mkdir(parents=True, exist_ok=True)

SCENARIOS = {
    "cbi_digital_arrest": {
        "text": "Hello, this is Inspector Rathore from Central Bureau of Investigation CBI Cyber Crime Branch New Delhi. An arrest warrant has been issued against your name in money laundering and narcotics trafficking. You are under digital arrest. Do not disconnect Skype call, immediately transfer funds to government verification account.",
        "voice": "en-IN-PrabhatNeural",
        "rate": "+0%"
    },
    "sbi_kyc_otp_theft": {
        "text": "Dear customer, your State Bank of India Net Banking KYC has expired today. Your bank account will be frozen within two hours. Please share the six digit OTP received on your mobile to update your Aadhaar card and PAN card immediately.",
        "voice": "en-IN-PrabhatNeural",
        "rate": "+0%"
    },
    "fedex_customs_drugs": {
        "text": "This is FedEx Customs Clearance at Mumbai Airport. A courier parcel sent under your PAN card to Taiwan contains five illegal passports and contraband drugs. Customs officers have seized the parcel. Transfer penalty fee now or police will arrest.",
        "voice": "en-IN-PrabhatNeural",
        "rate": "+0%"
    },
    "cloned_relative_emergency": {
        "text": "Papa, police ne pakad liya hai mujhe. Accident ho gaya car se. Hospital me hu, bail money chahiye fifty thousand rupees emergency. Please kisi ko mat batana, jaldi transfer karo.",
        "voice": "hi-IN-MadhurNeural",
        "rate": "+5%"
    },
    "legitimate_colleague_call": {
        "text": "Hey, good afternoon! Just checking if we are still on for the project presentation and team sync at 4 PM today? Let me know once you review the slides.",
        "voice": "en-IN-PrabhatNeural",
        "rate": "+0%"
    }
}

async def generate_all():
    print("[*] Generating realistic human MALE scenario audio files with edge-tts...")
    for key, data in SCENARIOS.items():
        mp3_path = OUT_DIR / f"{key}.mp3"
        wav_path = OUT_DIR / f"{key}.wav"
        
        print(f" -> Generating {key} using {data['voice']}...")
        communicate = edge_tts.Communicate(text=data["text"], voice=data["voice"], rate=data["rate"])
        await communicate.save(str(mp3_path))
        
        y, sr = load_audio(str(mp3_path))
        sf.write(str(wav_path), y, 16000, subtype='PCM_16')
        print(f"    Saved: {mp3_path} ({mp3_path.stat().st_size} bytes)")
        print(f"    Saved: {wav_path} ({wav_path.stat().st_size} bytes)")

    print("[*] All human MALE scenario audio files generated successfully!")

if __name__ == "__main__":
    asyncio.run(generate_all())

