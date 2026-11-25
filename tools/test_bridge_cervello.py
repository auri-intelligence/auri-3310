"""Test del cervello locale del bridge (llama.cpp): py tools/test_bridge_cervello.py

Non serve ne' il modello ne' il Claude Agent SDK: il server llama.cpp e' finto e risponde come il vero
(formato OpenAI). Si controllano le tre cose che possono rompersi davvero: la scelta del motore, la
conversazione con llama-server e i comandi della casa scritti dal modello dentro la frase.
"""
import io
import json
import os
import sys
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'bridge'))

# Il bridge importa il Claude Agent SDK all'avvio: qui non serve, basta un finto.
finto = types.ModuleType('claude_agent_sdk')
for nome in ('AssistantMessage', 'ClaudeAgentOptions', 'PermissionResultAllow', 'PermissionResultDeny',
             'ResultMessage', 'TextBlock'):
    setattr(finto, nome, type(nome, (), {}))
finto.query = lambda *a, **k: None
sys.modules.setdefault('claude_agent_sdk', finto)

import auri_bridge as b


class FintaRisposta:
    def __init__(self, obj):
        self.dati = json.dumps(obj).encode()
        self.status = 200

    def read(self):
        return self.dati

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def finto_server(risposta, chiamate):
    def urlopen(req, timeout=None):
        url = req if isinstance(req, str) else req.full_url
        corpo = json.loads(req.data) if not isinstance(req, str) and req.data else None
        chiamate.append((url, corpo))
        if url.endswith('/v1/models'):
            return FintaRisposta({'data': [{'id': 'auri'}]})
        return FintaRisposta({'choices': [{'message': {'content': risposta}}]})
    return urlopen


def prepara(risposta, entities=()):
    b.cfg = {'llm_url': 'http://127.0.0.1:8080', 'assist_engine': 'local', 'language': 'it',
             'entities': list(entities), 'llm_autostart': False}
    b.llm_sessions.clear()
    chiamate = []
    b.urllib.request.urlopen = finto_server(risposta, chiamate)
    return chiamate


def test_risposta():
    chiamate = prepara('Ciao, sono AurI e vivo in un 3310.')
    out = b.llm_assist({'text': 'chi sei?', 'language': 'it'})
    assert out['reply'] == 'Ciao, sono AurI e vivo in un 3310.', out
    assert out['session'].startswith('l-')
    url, corpo = chiamate[-1]
    assert url.endswith('/v1/chat/completions'), url
    assert corpo['messages'][0]['role'] == 'system' and 'AurI' in corpo['messages'][0]['content']
    assert corpo['messages'][-1]['content'] == 'chi sei?'
    assert corpo['chat_template_kwargs'] == {'enable_thinking': False}
    print('ok  domanda e risposta con llama-server')


def test_storia():
    prepara('Va bene.')
    s = b.llm_assist({'text': 'uno', 'language': 'it'})['session']
    chiamate = prepara('Va bene.')
    b.cfg['entities'] = []
    b.llm_sessions[s] = [{'role': 'user', 'content': 'uno'}, {'role': 'assistant', 'content': 'Va bene.'}]
    b.llm_assist({'text': 'due', 'session': s, 'language': 'it'})
    _url, corpo = chiamate[-1]
    contenuti = [m['content'] for m in corpo['messages']]
    assert 'uno' in contenuti and 'due' in contenuti, contenuti
    assert len(b.llm_sessions[s]) <= b.LLM_HISTORY
    print('ok  si ricorda le battute precedenti')


def test_ragionamento_tolto():
    prepara('<think>mmm, chissa</think>Sono le sei.')
    out = b.llm_assist({'text': 'che ore sono?', 'language': 'it'})
    assert out['reply'] == 'Sono le sei.', out
    print('ok  il ragionamento del modello non finisce sul display')


def test_casa():
    fatti = []

    def finto_toggle(req):
        fatti.append(req['id'])
        return {'message': 'Fatto'}
    vero, b.home_toggle = b.home_toggle, finto_toggle
    try:
        prepara('Accendo la luce. [CASA on light.soggiorno]', entities=['light.soggiorno'])
        out = b.llm_assist({'text': 'accendi la luce', 'language': 'it'})
        assert out['reply'] == 'Accendo la luce.', out
        assert fatti == ['light.soggiorno'], fatti
        # solo il comando, senza frase: resta il messaggio del bridge
        prepara('[CASA off light.soggiorno]', entities=['light.soggiorno'])
        out = b.llm_assist({'text': 'spegni', 'language': 'it'})
        assert out['reply'] == 'Fatto', out
        # parentesi aperta e mai chiusa: non deve far saltare niente
        prepara('Ecco [CASA on light', entities=['light.soggiorno'])
        out = b.llm_assist({'text': 'accendi', 'language': 'it'})
        assert out['reply'] == 'Ecco', out
    finally:
        b.home_toggle = vero
    print('ok  comandi della casa dentro la frase')


def test_motore():
    b.cfg = {'assist_engine': 'local'}
    assert b.assist_engine() == 'local'
    b.cfg = {'assist_engine': 'gemini'}
    assert b.assist_engine() == 'gemini'
    b.cfg = {'assist_engine': 'auto', 'llm_model': 'models/llm/x.gguf', 'llm_autostart': True}
    b.llm_up = lambda timeout=2: False
    assert b.assist_engine() == 'local', 'con un modello configurato deve preferire il cervello locale'
    b.cfg = {'assist_engine': 'auto'}
    os.environ.pop('GEMINI_API_KEY', None)
    assert b.assist_engine() == 'local', 'senza niente resta locale e lo dice sul telefono'
    os.environ['GEMINI_API_KEY'] = 'prova'
    assert b.assist_engine() == 'gemini'
    os.environ.pop('GEMINI_API_KEY')
    print('ok  scelta del motore (auto, local, gemini)')


def test_spento():
    b.cfg = {'assist_engine': 'local', 'llm_autostart': False, 'language': 'it'}
    b.llm_up = lambda timeout=2: False
    out = b.llm_assist({'text': 'ciao', 'language': 'it'})
    assert 'llama-server' in out['reply'], out
    print('ok  se il cervello e spento lo dice invece di sembrare rotto')


if __name__ == '__main__':
    vero_up = b.llm_up
    test_risposta()
    test_storia()
    test_ragionamento_tolto()
    test_casa()
    test_motore()
    test_spento()
    b.llm_up = vero_up
    print('\ntutti i test passati.')
