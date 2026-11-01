import requests
import glob
import os
import json
from pathlib import Path

files = sorted(glob.glob('datasets/recordings/*.wav'))
print(f"Running inference on {len(files)} files in datasets/recordings/:\n")

results = []
for fpath in files:
    fname = os.path.basename(fpath)
    with open(fpath, 'rb') as f:
        resp = requests.post(
            'http://127.0.0.1:8000/audio/analyze',
            files={'file': (fname, f, 'audio/wav')}
        )
    if resp.status_code == 200:
        data = resp.json()
        res = {
            'file': fname,
            'prediction': data.get('prediction'),
            'display_verdict': data.get('display_verdict'),
            'ai_probability': data.get('ai_probability'),
            'real_probability': data.get('real_probability'),
            'confidence': data.get('confidence'),
            'threat_level': data.get('threat_level'),
            'latency_ms': data.get('detection_latency_ms'),
            'orig_duration_s': data.get('original_duration_sec'),
            'speech_duration_s': data.get('speech_duration_sec'),
            'num_windows': data.get('num_windows'),
            'windows': [
                {
                    'window': w.get('window_index'),
                    'start_sec': w.get('start_sec'),
                    'end_sec': w.get('end_sec'),
                    'ai_prob': round(w.get('fake_probability', 0.0), 4),
                    'real_prob': round(w.get('real_probability', 0.0), 4),
                    'verdict': w.get('verdict')
                } for w in data.get('windows', [])
            ]
        }
        results.append(res)
        print(f"File: {fname}")
        print(f"  Verdict:        {res['prediction']} (Display: {res['display_verdict']})")
        print(f"  AI Probability: {res['ai_probability']:.4f} | Real Probability: {res['real_probability']:.4f}")
        print(f"  Confidence:     {res['confidence']:.4f}")
        print(f"  Threat Level:   {res['threat_level']} | Latency: {res['latency_ms']} ms")
        print(f"  Duration:       Total {res['orig_duration_s']}s | Speech {res['speech_duration_s']}s | Windows {res['num_windows']}")
        for w in res['windows'][:5]:  # print first 5 windows
            print(f"    window {w['window']} [{w['start_sec']:.1f}-{w['end_sec']:.1f}s]: AI={w['ai_prob']} -> {w['verdict']}")
        if len(res['windows']) > 5:
            print(f"    ... (+{len(res['windows']) - 5} more windows)")
        print("-" * 65)
    else:
        print(f"File {fname} failed: {resp.status_code} {resp.text}\n")

Path("reports").mkdir(exist_ok=True)
with open('reports/six_user_recordings.json', 'w') as out:
    json.dump(results, out, indent=2)
print("Saved full report to reports/six_user_recordings.json")

