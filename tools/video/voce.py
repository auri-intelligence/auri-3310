"""Generates the voice-over from copione.txt with Gemini TTS.

  .venv/Scripts/python voce.py parte2 [--voice Fenrir]

The key is read from the GEMINI_API_KEY environment variable, never from a file.
"""
import argparse
import base64
import json
import os
import urllib.request
import wave

HERE = os.path.dirname(os.path.abspath(__file__))
MODELS = ('gemini-3.1-flash-tts-preview', 'gemini-2.5-flash-preview-tts')
STYLE = ("Leggi in italiano come un creator di TikTok carichissimo, che non riesce a contenere l'entusiasmo: "
         "voce piena di energia ed enfasi, ritmo veloce e incalzante senza pause morte, "
         "esclamazioni con stupore, domande con tono provocatorio e complice, "
         "parole chiave scandite con forza, pause brevissime solo sui puntini, chiusura con suspense:\n\n")


def tts(text, voice, key):
    body = {'contents': [{'parts': [{'text': STYLE + text}]}],
            'generationConfig': {'responseModalities': ['AUDIO'],
                                 'speechConfig': {'voiceConfig': {'prebuiltVoiceConfig': {'voiceName': voice}}}}}
    last = None
    for model in MODELS * 3:
        url = 'https://generativelanguage.googleapis.com/v1beta/models/%s:generateContent' % model
        req = urllib.request.Request(url, data=json.dumps(body).encode(), method='POST')
        req.add_header('x-goog-api-key', key)
        req.add_header('Content-Type', 'application/json')
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                res = json.loads(r.read())
            part = res['candidates'][0]['content']['parts'][0]['inlineData']
            return base64.b64decode(part['data']), model
        except urllib.error.HTTPError as e:
            last = e
        except (KeyError, IndexError):
            # the TTS sometimes answers without audio (finishReason OTHER): retry
            last = RuntimeError('%s: %s' % (model, res.get('candidates', [{}])[0].get('finishReason')))
            print(last)
    raise last


def main():
    p = argparse.ArgumentParser()
    p.add_argument('parte', help='part folder, e.g. parte2')
    p.add_argument('--voice', default='Fenrir')
    a = p.parse_args()
    key = os.environ.get('GEMINI_API_KEY')
    if not key:
        raise SystemExit('Imposta GEMINI_API_KEY')
    base = os.path.join(HERE, a.parte)
    text = open(os.path.join(base, 'copione.txt'), encoding='utf-8').read()
    pcm, model = tts(text, a.voice, key)
    os.makedirs(os.path.join(base, 'out'), exist_ok=True)
    out = os.path.join(base, 'out', 'voce_%s.wav' % a.voice)
    with wave.open(out, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(24000)
        w.writeframes(pcm)
    print('%s (%s, %.1f s)' % (out, model, len(pcm) / 48000))


if __name__ == '__main__':
    main()
