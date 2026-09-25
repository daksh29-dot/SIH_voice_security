import requests

url = 'http://127.0.0.1:5000/api/analyze'
p = r'C:\Users\DELL\Downloads\utsavoice.wav'
with open(p, 'rb') as f:
    files = {'audio': ('utsavoice.wav', f, 'audio/wav')}
    res = requests.post(url, files=files, timeout=60)

print('Status:', res.status_code)
print('Response:', res.json())
