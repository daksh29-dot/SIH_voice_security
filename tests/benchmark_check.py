import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, '.')
sys.path.insert(0, 'src')
from audio_preprocessing import load_audio, resample, normalize
from segment_audio import windows
from model import W2V2AASISTSpoofDetector

m = W2V2AASISTSpoofDetector()

files = [
    ('Real Utsav', r'C:\Users\DELL\Downloads\utsavoice.wav'),
    ('Yashveer AI Clone', r'yashveer-clone-1788962405365.mp3'),
    ('Test Synthetic', r'uploads\test_synthetic.wav')
]

for sub, label in [('test_audio/real', 'ASV Real'), ('test_audio/spoof', 'ASV Spoof')]:
    flist = list(Path(sub).glob('*.flac'))[:3]
    for f in flist:
        files.append((f'{label} {f.name}', str(f)))

for label, p in files:
    try:
        x, sr = load_audio(p)
        x = resample(x, sr, 16000)
        wins = windows(x)
        if not wins:
            print(f'=== {label} ({len(x)/16000:.2f}s) ===: NO WINDOWS')
            continue
        margins = [float(m.predict_margin(normalize(w.waveform, 'none'))) for w in wins]
        scores = [1.0 / (1.0 + np.exp(-mg)) for mg in margins]
        print(f'=== {label} ({len(x)/16000:.2f}s, {len(wins)} wins) ===')
        print(f'  Margins: {[round(mg, 3) for mg in margins]}')
        print(f'  Scores:  {[round(sc*100, 2) for sc in scores]}')
        print(f'  Mean Margin: {np.mean(margins):.3f} -> Sigmoid: {100.0 / (1.0 + np.exp(-np.mean(margins))):.2f}%')
        print(f'  Min Margin:  {np.min(margins):.3f} -> Sigmoid: {100.0 / (1.0 + np.exp(-np.min(margins))):.2f}%')
        print(f'  Onset (Win 0) Margin: {margins[0]:.3f} -> Sigmoid: {scores[0]*100:.2f}%')
    except Exception as e:
        print(f'=== {label} === ERROR: {e}')
