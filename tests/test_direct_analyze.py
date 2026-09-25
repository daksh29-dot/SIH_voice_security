import sys
from pathlib import Path
sys.path.insert(0, '.')
sys.path.insert(0, 'src')
from inference import VoiceSpoofDetector

d = VoiceSpoofDetector()
res = d.analyze(r'C:\Users\DELL\Downloads\utsavoice.wav')
print('aggregated_score:', res.aggregated_score)
print('aggregated_margin:', res.aggregated_margin)
print('decision:', res.decision)
print('status:', res.status)
print('reasons:', res.reasons)
print('segment_scores:', res.segment_scores)
