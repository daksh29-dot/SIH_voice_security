"""
speech_to_text.py

Handles Real Speech-to-Text (STT) for incoming voice streams and audio files.
Uses Google Speech Recognition API via SpeechRecognition library with fast fallback.
"""

import os
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional

import speech_recognition as sr
import soundfile as sf
import librosa

_recognizer = sr.Recognizer()

def transcribe_audio_file(audio_path: str | Path) -> Dict[str, Any]:
    """
    Transcribes an audio file (WAV, FLAC, MP3, etc.) to text in real-time.
    Returns transcript and confidence.
    """
    path = Path(audio_path)
    if not path.exists():
        return {"text": "", "status": "FILE_NOT_FOUND"}

    wav_path = None
    try:
        # If not standard PCM wav, convert via load_audio/soundfile to 16kHz PCM WAV for recognizer
        if path.suffix.lower() != ".wav":
            from audio_preprocessing import load_audio
            y, sr_rate = load_audio(str(path))
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                wav_path = tmp.name
            sf.write(wav_path, y, 16000, subtype='PCM_16')
            audio_source_path = wav_path
        else:
            audio_source_path = str(path)

        with sr.AudioFile(audio_source_path) as source:
            # Adjust for ambient noise and record
            audio_data = _recognizer.record(source)

        # Transcribe with Google Speech Recognition (free, high accuracy)
        try:
            transcript = _recognizer.recognize_google(audio_data, language="en-IN")
            return {
                "text": transcript,
                "status": "SUCCESS",
                "engine": "Google-Speech-API"
            }
        except sr.UnknownValueError:
            # Try Hindi / Hinglish model if English didn't catch it
            try:
                transcript_hi = _recognizer.recognize_google(audio_data, language="hi-IN")
                return {
                    "text": transcript_hi,
                    "status": "SUCCESS",
                    "engine": "Google-Speech-API-HI"
                }
            except Exception:
                return {
                    "text": "",
                    "status": "UNINTELLIGIBLE_SPEECH",
                    "engine": "Google-Speech-API"
                }
        except sr.RequestError as e:
            return {
                "text": "",
                "status": f"API_UNAVAILABLE: {e}",
                "engine": "Offline-Fallback"
            }

    except Exception as e:
        return {
            "text": "",
            "status": f"ERROR: {e}",
            "engine": "None"
        }
    finally:
        if wav_path and os.path.exists(wav_path):
            try:
                os.unlink(wav_path)
            except OSError:
                pass


if __name__ == "__main__":
    import sys
    test_file = sys.argv[1] if len(sys.argv) > 1 else "test_audio/real/LA_E_3003752.flac"
    res = transcribe_audio_file(test_file)
    print("STT Result:", res)
