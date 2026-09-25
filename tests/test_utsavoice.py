import sys
sys.path.insert(0, '.')
sys.path.insert(0, 'src')
from inference import VoiceSpoofDetector

p = r'C:\Users\DELL\Downloads\utsavoice.wav'
d = VoiceSpoofDetector()
res = d.analyze(p)
print('Aggregated score:', res.aggregated_score)
print('Aggregated margin:', res.aggregated_margin)
print('Segment scores:', res.segment_scores)
print('Windows count:', len(res.windows))
for i, w in enumerate(res.windows):
    print(f'Win {i}: reasons={w["quality"]["reasons"]}, score={w.get("score")}, margin={w.get("margin")}')
