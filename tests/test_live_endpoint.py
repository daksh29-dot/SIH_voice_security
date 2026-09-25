import requests

url = 'http://127.0.0.1:5000/api/analyze-call'
p = r'C:\Users\DELL\Downloads\utsavoice.wav'
with open(p, 'rb') as f:
    files = {'audio': ('utsavoice.wav', f, 'audio/wav')}
    data = {'phone_number': 'Web Microphone', 'carrier': 'WebRTC'}
    res = requests.post(url, files=files, data=data, timeout=60)

print('HTTP Status:', res.status_code)
j = res.json()
print('Voice clone pillar:', j.get('pillars', {}).get('voice_clone'))
print('Composite risk score:', j.get('orchestration', {}).get('composite_risk_score'))
print('Policy action:', j.get('orchestration', {}).get('policy_action'))
