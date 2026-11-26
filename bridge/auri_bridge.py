"""AurI Bridge: the server on the Raspberry Pi that the AurI-3310 talks to.

  python auri_bridge.py [--config config.json]

Claude runs through the Claude Agent SDK, which is the Claude Code engine itself:
same login, CLAUDE.md, MCP servers, skills and permission modes.
"""
import argparse
import atexit
import asyncio
import base64
import io
import json
import os
import subprocess
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
import wave
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from claude_agent_sdk import (AssistantMessage, ClaudeAgentOptions, PermissionResultAllow,
                              PermissionResultDeny, ResultMessage, TextBlock, query)

HERE = os.path.dirname(os.path.abspath(__file__))
# Speech models live inside the project, so removing bridge/models removes them.
os.environ.setdefault('HF_HOME', os.path.join(HERE, 'models', 'hf'))
LANG_NAMES = {'it': 'Italian', 'en': 'English', 'es': 'Spanish', 'fr': 'French', 'de': 'German', 'pt': 'Portuguese'}

# Messages the bridge itself shows on the phone, in the phone's language (Italian by default).
MSG = {
    'denied': ('Rifiutato dal telefono', 'Denied on the phone', 'Rechazado en el telefono',
               'Refuse sur le telephone', 'Am Telefon abgelehnt', 'Recusado no telefone'),
    'expired': ('Richiesta scaduta', 'Request expired', 'Solicitud caducada', 'Demande expiree',
                'Anfrage abgelaufen', 'Pedido expirado'),
    'working': ('(ancora al lavoro...)', '(still working...)', '(sigo trabajando...)', '(je travaille encore...)',
                '(arbeite noch...)', '(ainda trabalhando...)'),
    'error': ('Errore', 'Error', 'Error', 'Erreur', 'Fehler', 'Erro'),
    'no_voice': ('Voce non attiva sul bridge.', 'Voice is not active on the bridge.', 'Voz no activa en el bridge.',
                 'Voix non active sur le bridge.', 'Sprache am Bridge nicht aktiv.', 'Voz nao ativa no bridge.'),
    'not_heard': ('Non ho sentito niente.', "I didn't hear anything.", 'No he oido nada.', "Je n'ai rien entendu.",
                  'Ich habe nichts gehoert.', 'Nao ouvi nada.'),
    'done': ('Fatto', 'Done', 'Hecho', 'Fait', 'Erledigt', 'Feito'),
    'not_allowed': ('Dispositivo non consentito', 'Device not allowed', 'Dispositivo no permitido',
                    'Appareil non autorise', 'Geraet nicht erlaubt', 'Dispositivo nao permitido'),
    'unauthorized': ('Token non valido', 'Invalid token', 'Token no valido', 'Jeton invalide',
                     'Ungueltiges Token', 'Token invalido'),
    'not_found': ('Indirizzo sconosciuto', 'Unknown address', 'Direccion desconocida', 'Adresse inconnue',
                  'Unbekannte Adresse', 'Endereco desconhecido'),
    'server': ('Errore interno del bridge', 'Internal bridge error', 'Error interno del bridge',
               'Erreur interne du bridge', 'Interner Bridge-Fehler', 'Erro interno do bridge'),
}
LANG_ORDER = ('it', 'en', 'es', 'fr', 'de', 'pt')


def lang_of(req):
    code = (req or {}).get('language') or cfg.get('language', 'it')
    return code if code in LANG_ORDER else 'it'


def msg(req, key):
    return MSG[key][LANG_ORDER.index(lang_of(req))]



def phone_prompt(req):
    if (req or {}).get('mode') == 'assist':
        return ("You are AurI, the voice assistant of this phone, like a phone's built-in assistant. "
                "The user spoke to you; your answer is read aloud and shown on a 14-column display. "
                "Reply in %s with one or two short spoken sentences, plain text only, no markdown or emoji. "
                "Use your tools when needed (home, web, files) and keep the final answer brief." % LANG_NAMES[lang_of(req)])
    return ("You are answering on a Nokia 3310 with a 14-column display that shows 3 lines at a time. "
            "Reply in %s, short and direct, plain text only: no markdown, lists, tables or emoji." % LANG_NAMES[lang_of(req)])

SAFE_TOOLS = {'Read', 'Glob', 'Grep', 'WebSearch', 'WebFetch', 'TodoWrite'}
WAIT_S = 120

cfg = {}
loop = asyncio.new_event_loop()
runs = {}
lock = threading.Lock()


def load_config(path):
    with open(path, encoding='utf-8') as f:
        c = json.load(f)
    c.setdefault('port', 8310)
    c['cwd'] = os.path.expanduser(c.get('cwd', '~'))
    return c


class Run:
    """One Claude turn. Pauses whenever Claude asks for a permission, until the phone answers."""

    def __init__(self, req):
        self.id = uuid.uuid4().hex[:8]
        self.req = req
        self.text = []
        self.session = req.get('session')
        self.pending = None
        self.answer = None
        self.done = False
        self.error = None
        self.changed = threading.Event()

    async def can_use_tool(self, name, data, ctx):
        if name in SAFE_TOOLS:
            return PermissionResultAllow()
        desc = describe_tool(name, data)
        self.answer = loop.create_future()
        self.pending = {'id': self.id, 'text': desc}
        self.changed.set()
        ok = await self.answer
        self.answer = None              # una seconda conferma sullo stesso id non deve rompere il loop
        self.pending = None
        if ok:
            return PermissionResultAllow()
        return PermissionResultDeny(message=msg(self.req, 'denied'))

    async def go(self):
        r = self.req
        opts = ClaudeAgentOptions(
            model=r.get('model') or None,
            effort=r.get('effort') or None,
            permission_mode=modo_permessi(r.get('permission_mode')),
            resume=r.get('session') or None,
            cwd=cfg['cwd'],
            setting_sources=['user', 'project', 'local'],
            system_prompt={'type': 'preset', 'preset': 'claude_code', 'append': phone_prompt(r)},
            can_use_tool=self.can_use_tool,
        )
        try:
            async for m in query(prompt=stream_prompt(r['text']), options=opts):
                if isinstance(m, AssistantMessage):
                    for b in m.content:
                        if isinstance(b, TextBlock) and b.text.strip():
                            self.text.append(b.text.strip())
                elif isinstance(m, ResultMessage):
                    self.session = m.session_id
                    if m.is_error and not self.text:
                        self.error = m.result or msg(self.req, 'error')
        except Exception as e:
            # 11. il dettaglio (percorsi, URL, SDK) resta nel log del bridge, al telefono un messaggio chiaro
            print('claude:', e, flush=True)
            self.error = msg(self.req, 'error')
        self.done = True
        self.changed.set()

    def wait(self):
        deadline = time.time() + WAIT_S
        while time.time() < deadline:
            if self.done or self.pending:
                break
            self.changed.wait(1)
            self.changed.clear()
        out = {'session': self.session, 'reply': '\n'.join(self.text) or (self.error or '')}
        self.text = []
        if self.pending:
            out['confirm'] = self.pending
        elif not self.done:
            out['reply'] = (out['reply'] + '\n' + msg(self.req, 'working')).strip()
            out['confirm'] = None
        return out


async def stream_prompt(text):
    # can_use_tool needs the streaming input form of query().
    yield {'type': 'user', 'message': {'role': 'user', 'content': text}}


def describe_tool(name, data):
    if name == 'Bash':
        return 'Eseguo: ' + str(data.get('command', ''))[:80]
    if name in ('Write', 'Edit', 'MultiEdit', 'NotebookEdit'):
        return 'Modifico ' + os.path.basename(str(data.get('file_path', '')))
    return 'Uso ' + name


def start_chat(req):
    run = Run(req)
    with lock:
        runs[run.id] = run
    asyncio.run_coroutine_threadsafe(run.go(), loop)
    return run.wait()


def confirm(req):
    run = runs.get(req.get('id'))
    if not run or not run.answer or run.answer.done():
        return {'reply': msg(req, 'expired'), 'session': req.get('session')}
    run.pending = None
    run.changed.clear()
    loop.call_soon_threadsafe(run.answer.set_result, bool(req.get('ok')))
    return run.wait()


def claude_version():
    try:
        import claude_agent_sdk
        exe = os.path.join(os.path.dirname(claude_agent_sdk.__file__), '_bundled',
                           'claude.exe' if os.name == 'nt' else 'claude')
        out = subprocess.run([exe, '--version'], capture_output=True, text=True, timeout=20).stdout
        return out.split()[0] if out else '?'
    except Exception:
        return '?'


# Home Assistant ----------------------------------------------------------

def ha(method, path, body=None):
    token = os.environ.get(cfg.get('ha_token_env', 'HA_TOKEN'), '')
    req = urllib.request.Request(cfg['ha_url'].rstrip('/') + path, method=method,
                                 data=json.dumps(body).encode() if body is not None else None)
    req.add_header('Authorization', 'Bearer ' + token)
    req.add_header('Content-Type', 'application/json')
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read() or b'null')


def home_list():
    out = []
    for eid in cfg.get('entities', []):
        s = ha('GET', '/api/states/' + eid)
        out.append({'id': eid, 'name': s['attributes'].get('friendly_name', eid), 'state': s['state']})
    return {'entities': out}


def home_toggle(req, action='toggle'):
    """action: toggle, turn_on o turn_off (il cervello locale dice esplicitamente on/off)."""
    eid = req['id']
    if eid not in cfg.get('entities', []):
        raise PermissionError(msg(req, 'not_allowed'))
    if action not in ('toggle', 'turn_on', 'turn_off'):
        action = 'toggle'
    ha('POST', '/api/services/homeassistant/' + action, {'entity_id': eid})
    return {'message': msg(req, 'done')}


SENSORS = {
    'temperature': ('°C', 'temperature'), 'humidity': ('%', 'humidity'),
    'pressure': ('hPa', 'atmospheric_pressure'), 'battery': ('%', 'battery'),
}


def sensors_push(req):
    if not cfg.get('ha_url'):
        return {'ok': False}
    for key, (unit, dev) in SENSORS.items():
        if key in req:
            try:
                valore = round(float(req[key]), 2)      # solo numeri: niente testo arbitrario in Home Assistant
            except (TypeError, ValueError):
                continue
            ha('POST', '/api/states/sensor.auri_3310_' + key, {
                'state': valore,
                'attributes': {'unit_of_measurement': unit, 'device_class': dev,
                               'friendly_name': 'AurI-3310 ' + key}})
    return {'ok': True}


# Cervello locale: llama.cpp sul PC o sul Raspberry (gratis, nessuna chiave) --

MSG['no_llm'] = ('Cervello locale spento: avvia llama-server o usa setup_llm.',
                 'Local brain is off: start llama-server or run setup_llm.',
                 'Cerebro local apagado: arranca llama-server o usa setup_llm.',
                 'Cerveau local eteint: lance llama-server ou setup_llm.',
                 'Lokales Gehirn aus: llama-server starten oder setup_llm.',
                 'Cerebro local desligado: inicia llama-server ou setup_llm.')

LLM_HISTORY = 8
llm_sessions = {}
llm_proc = None


def llm_url(path=''):
    return (cfg.get('llm_url') or 'http://127.0.0.1:8080').rstrip('/') + path


def llm_up(timeout=2):
    try:
        with urllib.request.urlopen(llm_url('/v1/models'), timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False


def llm_files():
    """Percorsi di llama-server e del modello, o None se mancano (setup_llm non ancora fatto)."""
    exe = cfg.get('llm_bin') or os.path.join('models', 'llm', 'bin',
                                             'llama-server.exe' if os.name == 'nt' else 'llama-server')
    model = cfg.get('llm_model') or ''
    if not model:
        return None
    exe = exe if os.path.isabs(exe) else os.path.join(HERE, exe)
    model = model if os.path.isabs(model) else os.path.join(HERE, model)
    return (exe, model) if os.path.exists(exe) and os.path.exists(model) else None


def llm_local_host():
    return (urllib.parse.urlparse(llm_url()).hostname or '') in ('127.0.0.1', 'localhost', '::1')


llm_lock = threading.Lock()
llm_failed_at = 0


def llm_stop():
    """Spegne llama-server quando il bridge si chiude: niente processi orfani che tengono porta e RAM."""
    if llm_proc and llm_proc.poll() is None:
        llm_proc.terminate()
        try:
            llm_proc.wait(5)
        except Exception:
            llm_proc.kill()


atexit.register(llm_stop)


def llm_spawn():
    """Avvia llama-server da bridge/models/llm (scaricato da setup_llm), una volta sola.
    Il lock fa aspettare le altre richieste invece di avviare un secondo server sulla stessa porta."""
    global llm_failed_at
    with llm_lock:
        if llm_up(1):
            return
        if not (llm_proc and llm_proc.poll() is None):
            files = llm_files()
            if not files or not llm_local_host() or time.time() - llm_failed_at < 30:
                return
            _spawn(*files)
        for _ in range(90):              # il modello ci mette qualche secondo a salire
            if llm_up(1):
                return
            if llm_proc.poll() is not None:   # morto all'avvio: niente attese inutili
                llm_failed_at = time.time()
                print('llama-server terminato (codice %s): vedi models/llm/llama-server.log'
                      % llm_proc.returncode, flush=True)
                return
            time.sleep(1)


def _spawn(exe, model):
    global llm_proc
    port = str(urllib.parse.urlparse(llm_url()).port or 8080)
    # --jinja: usa il template della chat del modello, se no 'enable_thinking' non viene ascoltato
    cmd = [exe, '-m', model, '--host', '127.0.0.1', '--port', port,
           '-c', str(cfg.get('llm_ctx', 4096)), '--alias', 'auri', '--jinja']
    print('avvio llama-server:', ' '.join(cmd), flush=True)
    log = open(os.path.join(os.path.dirname(model), 'llama-server.log'), 'ab')
    llm_proc = subprocess.Popen(cmd, cwd=os.path.dirname(exe), stdout=log, stderr=subprocess.STDOUT)


def llm_ready():
    if llm_up():
        return True
    if cfg.get('llm_autostart', True):
        llm_spawn()
        return llm_up()
    return False


def llm_prompt(req):
    p = assist_prompt(req, tools=False)
    if cfg.get('entities') and cfg.get('ha_url'):
        # I modelli piccoli sbagliano le chiamate a funzione: qui basta una parola in fondo alla frase.
        p += (' Only when the user explicitly asks to switch a home device on or off, end your answer with '
              '[CASA on <id>] or [CASA off <id>] using one of these ids: %s. Never write it otherwise.'
              % ', '.join(cfg['entities']))
    return p


def llm_house(req, text):
    """Esegue e toglie dal testo i comandi [CASA on|off <id>] scritti dal modello."""
    out, note = text, ''
    while '[CASA' in out:
        i = out.index('[CASA')
        j = out.find(']', i)
        if j < 0:
            out = out[:i].strip()
            break
        cmd = out[i + 5:j].split()
        out = (out[:i] + out[j + 1:]).strip()
        eid = cmd[-1] if cmd else ''
        verbo = cmd[0].lower() if len(cmd) > 1 else ''
        action = {'on': 'turn_on', 'off': 'turn_off'}.get(verbo, 'toggle')
        if eid not in cfg.get('entities', []) or not cfg.get('ha_url'):
            # i modelli piccoli a volte inventano un comando anche a un semplice "ciao":
            # un dispositivo che non esiste si toglie in silenzio, non e' un errore da dire
            print('llm: comando casa ignorato:', cmd, flush=True)
            continue
        try:
            done = home_toggle(dict(req, id=eid), action)['message']
            if not out:
                note = done
        except Exception as e:
            # se il comando fallisce lo si dice sempre, anche se il modello ha gia' detto "fatto"
            note = str(e) if isinstance(e, PermissionError) else msg(req, 'error')
    return (out + ' ' + note).strip() if note else out


def llm_assist(req):
    sid = req.get('session') or 'l-' + uuid.uuid4().hex[:8]
    if not llm_ready():
        return {'reply': msg(req, 'no_llm'), 'error': 'no_llm', 'session': sid}
    hist = llm_sessions.setdefault(sid, [])
    msgs = ([{'role': 'system', 'content': llm_prompt(req)}] + hist
            + [{'role': 'user', 'content': req.get('text', '')}])
    body = {'model': 'auri', 'messages': msgs, 'temperature': 0.5, 'top_p': 0.9,
            'max_tokens': int(cfg.get('llm_max_tokens', 160)), 'stream': False,
            'chat_template_kwargs': {'enable_thinking': False}}
    r = urllib.request.Request(llm_url('/v1/chat/completions'), data=json.dumps(body).encode(), method='POST')
    r.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(r, timeout=cfg.get('llm_timeout', 120)) as resp:
            data = json.loads(resp.read())
    except Exception as e:
        print('llm:', e, flush=True)
        return {'reply': msg(req, 'error'), 'error': 'server', 'session': sid}
    reply = ((data.get('choices') or [{}])[0].get('message') or {}).get('content') or ''
    if '</think>' in reply:
        reply = reply.split('</think>')[-1]
    reply = llm_house(req, reply.strip())
    hist = hist + [{'role': 'user', 'content': req.get('text', '')}, {'role': 'assistant', 'content': reply}]
    llm_sessions[sid] = hist[-LLM_HISTORY:]
    return {'reply': reply or msg(req, 'error'), 'session': sid}


def assist_engine(up=None):
    """auto = il cervello locale se c'e', altrimenti Gemini; local o gemini per sceglierlo a mano."""
    want = cfg.get('assist_engine', 'auto')
    if want in ('local', 'llama', 'llm'):
        return 'local'
    if want == 'gemini':
        return 'gemini'
    return 'local' if llm_available(up) else (
        'gemini' if os.environ.get(cfg.get('gemini_key_env', 'GEMINI_API_KEY'), '') else 'local')


def llm_available(up=None):
    """Il cervello locale c'e' davvero: o risponde, o si puo' avviare (file presenti, host locale)."""
    if up is None:
        up = llm_up(0.5)
    return up or bool(cfg.get('llm_autostart', True) and llm_local_host() and llm_files())


# Gemini: the central AurI assistant (Claude stays in the Claude console) ----

GEMINI_URL = 'https://generativelanguage.googleapis.com/v1beta/interactions'
GEMINI_HISTORY = 12
gemini_sessions = {}
MSG['no_gemini'] = ('Gemini non configurato: imposta la chiave sul bridge.',
                    'Gemini not configured: set the key on the bridge.',
                    'Gemini no configurado: pon la clave en el bridge.',
                    'Gemini non configure: definis la cle sur le bridge.',
                    'Gemini nicht eingerichtet: Schluessel am Bridge setzen.',
                    'Gemini nao configurado: defina a chave no bridge.')


def assist_prompt(req, tools=True):
    p = ("Your name is AurI and you have no other name: you are the voice assistant built into this phone, "
         "not any brand's assistant. Your answer is read aloud and shown on a 14-column display. Reply in "
         "%s with one or two very short spoken sentences, plain text only, no markdown, lists or emoji."
         % LANG_NAMES[lang_of(req)])
    if tools and cfg.get('entities'):
        p += (" To switch a home device on or off call home_toggle with one of these ids: %s."
              % ', '.join(cfg['entities']))
    return p


def gemini_tools():
    if not cfg.get('entities'):
        return None
    return [{'type': 'function', 'name': 'home_toggle',
             'description': 'Toggles a Home Assistant device on or off.',
             'parameters': {'type': 'object', 'required': ['id'], 'properties': {
                 'id': {'type': 'string', 'enum': list(cfg['entities'])}}}}]


def gemini_call(key, req, steps):
    # Free-tier models are often overloaded (503/429): try the next one in the list.
    models = cfg.get('gemini_models') or [cfg.get('gemini_model', 'gemini-4-hydrogen'),
                                          'gemini-3.5-flash', 'gemini-flash-lite-latest']
    last = None
    for model in models:
        body = {'model': model, 'store': False, 'system_instruction': assist_prompt(req), 'input': steps}
        tools = gemini_tools()
        if tools:
            body['tools'] = tools
        r = urllib.request.Request(GEMINI_URL, data=json.dumps(body).encode(), method='POST')
        r.add_header('x-goog-api-key', key)
        r.add_header('Content-Type', 'application/json')
        try:
            with urllib.request.urlopen(r, timeout=60) as resp:
                return json.loads(resp.read()).get('steps', [])
        except urllib.error.HTTPError as e:
            last = e
            if e.code not in (429, 500, 503):
                raise
    raise last or RuntimeError('nessun modello Gemini configurato')


def step_text(step):
    return ' '.join(c.get('text', '') for c in step.get('content') or [] if c.get('type') == 'text').strip()


def gemini_assist(req):
    sid = req.get('session') or 'g-' + uuid.uuid4().hex[:8]
    key = os.environ.get(cfg.get('gemini_key_env', 'GEMINI_API_KEY'), '')
    if not key:
        return {'reply': msg(req, 'no_gemini'), 'session': sid}
    hist = gemini_sessions.setdefault(sid, [])
    steps = hist + [{'type': 'user_input', 'content': [{'type': 'text', 'text': req.get('text', '')}]}]
    reply = ''
    try:
        for _ in range(3):
            out = gemini_call(key, req, steps)
            steps += out
            calls = [s for s in out if s.get('type') == 'function_call']
            if not calls:
                reply = next((step_text(s) for s in reversed(out) if step_text(s)), '')
                break
            for c in calls:
                try:
                    res = home_toggle(dict(req, id=(c.get('arguments') or {}).get('id', '')))['message']
                except Exception as e:
                    res = str(e) if isinstance(e, PermissionError) else msg(req, 'error')
                steps.append({'type': 'function_result', 'name': c.get('name'), 'call_id': c.get('id'),
                              'result': [{'type': 'text', 'text': res}]})
    except Exception as e:
        print('gemini:', e, flush=True)
        return {'reply': msg(req, 'error'), 'error': 'server', 'session': sid}
    # Model steps are resent verbatim, as the Interactions API asks in stateless mode.
    kept = steps[-GEMINI_HISTORY:]
    while kept and kept[0].get('type') != 'user_input':
        kept.pop(0)
    gemini_sessions[sid] = kept
    return {'reply': reply or msg(req, 'error'), 'session': sid}


def chat(req):
    if req.get('mode') != 'assist':
        return start_chat(req)                      # la console Claude resta Claude
    return llm_assist(req) if assist_engine() == 'local' else gemini_assist(req)


# Voice: local speech-to-text (faster-whisper) and text-to-speech (Piper) -----

_stt = None


def transcribe(pcm16, rate, lang='it'):
    global _stt
    from faster_whisper import WhisperModel
    import numpy as np
    if _stt is None:
        _stt = WhisperModel(cfg.get('stt_model', 'small'), compute_type='int8')
    audio = np.frombuffer(pcm16, dtype=np.int16).astype(np.float32) / 32768
    if rate != 16000:
        idx = np.arange(0, len(audio), rate / 16000).astype(int)
        audio = audio[idx[idx < len(audio)]]
    segs, _ = _stt.transcribe(audio, language=lang)
    return ' '.join(s.text.strip() for s in segs).strip()


def speak(text):
    voice = cfg.get('piper_voice')
    if not voice or not text:
        return None
    from piper import PiperVoice
    v = PiperVoice.load(os.path.join(HERE, voice))
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as w:
        v.synthesize_wav(text, w)
    return base64.b64encode(buf.getvalue()).decode()


def voice(req):
    pcm = base64.b64decode(req['audio'])
    rate = int(req.get('rate', 16000))
    secs = len(pcm) / 2 / rate
    peak = max(abs(int.from_bytes(pcm[i:i + 2], 'little', signed=True)) for i in range(0, len(pcm) - 1, 64)) if pcm else 0
    print('voce: %.1f s, picco %d' % (secs, peak), flush=True)
    if secs < 0.3 or peak < 200:
        return {'reply': msg(req, 'not_heard'), 'error': 'Audio vuoto o muto (%.1f s)' % secs, 'session': req.get('session')}
    try:
        text = transcribe(pcm, int(req.get('rate', 16000)), lang_of(req))
    except ImportError:
        return {'reply': msg(req, 'no_voice')}
    if not text:
        return {'reply': msg(req, 'not_heard'), 'session': req.get('session')}
    req = dict(req, text=text)
    out = chat(req)
    out['transcript'] = text
    try:
        out['audio'] = speak(out.get('reply', ''))
    except ImportError:
        out['audio'] = None
    return out


def modo_permessi(chiesto):
    """La modalita' di Claude la sceglie il telefono, ma solo tra quelle permesse: 'bypassPermissions'
    (comandi senza conferma) solo se il config lo dice esplicitamente con allow_bypass: true."""
    sicuri = ('default', 'acceptEdits', 'plan')
    if chiesto in sicuri:
        return chiesto
    if chiesto == 'bypassPermissions' and cfg.get('allow_bypass') is True:
        return chiesto
    return 'default'


def origine_ok(origin):
    """CORS solo per il simulatore servito in locale o nella rete di casa, non per un sito qualsiasi."""
    if not origin:
        return False
    host = urllib.parse.urlparse(origin).hostname or ''
    return (host in ('localhost', '127.0.0.1', '::1') or host.startswith('192.168.') or host.startswith('10.')
            or any(host.startswith('172.%d.' % i) for i in range(16, 32)))


MAX_CORPO = 8 * 1024 * 1024        # la voce arriva come audio: 8 MB bastano, oltre e' un abuso


# HTTP ---------------------------------------------------------------------

class Handler(BaseHTTPRequestHandler):
    def _send(self, code, obj):
        data = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        origin = self.headers.get('Origin')
        if origine_ok(origin):
            self.send_header('Access-Control-Allow-Origin', origin)
            self.send_header('Vary', 'Origin')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        self._send(204, {})

    def _authorized(self):
        tok = cfg.get('token')
        return not tok or self.headers.get('Authorization') == 'Bearer ' + tok

    def do_GET(self):
        if not self._authorized():
            return self._send(401, {'error': msg(None, 'unauthorized')})
        try:
            if self.path == '/v1/info':
                up = llm_up(0.5)
                return self._send(200, {'version': claude_version(), 'plan': cfg.get('plan', 'Claude'),
                                        'cwd': os.path.basename(cfg['cwd'].rstrip('/\\')) or '~',
                                        'assist': assist_engine(up), 'llm': up})
            if self.path == '/v1/home':
                return self._send(200, home_list())
            self._send(404, {'error': msg(None, 'not_found')})
        except Exception as e:
            self._send(500, {'error': str(e) if isinstance(e, PermissionError) else msg(None, 'server')})

    def do_POST(self):
        if not self._authorized():
            return self._send(401, {'error': msg(None, 'unauthorized')})
        try:
            n = int(self.headers.get('Content-Length', 0))
        except ValueError:
            n = -1
        if n < 0 or n > MAX_CORPO:
            return self._send(413, {'error': msg(None, 'server')})
        try:
            req = json.loads(self.rfile.read(n) or b'{}')
        except ValueError:
            return self._send(400, {'error': msg(None, 'server')})
        if not isinstance(req, dict):
            return self._send(400, {'error': msg(None, 'server')})
        routes = {'/v1/chat': chat, '/v1/confirm': confirm, '/v1/voice': voice,
                  '/v1/home/toggle': home_toggle, '/v1/sensors': sensors_push}
        fn = routes.get(self.path)
        if not fn:
            return self._send(404, {'error': msg(None, 'not_found')})
        try:
            self._send(200, fn(req))
        except Exception as e:
            self._send(500, {'error': str(e) if isinstance(e, PermissionError) else msg(None, 'server')})

    def log_message(self, fmt, *args):
        print('%s %s' % (self.address_string(), fmt % args))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--config', default=os.path.join(HERE, 'config.json'))
    a = p.parse_args()
    global cfg
    path = a.config if os.path.exists(a.config) else os.path.join(HERE, 'config.example.json')
    cfg = load_config(path)
    threading.Thread(target=loop.run_forever, daemon=True).start()
    host = cfg.get('host', '0.0.0.0')
    if host not in ('127.0.0.1', 'localhost', '::1') and not cfg.get('token'):
        # aperto alla rete di casa senza token = chiunque nella rete puo' usare Claude e la casa
        print('Bridge NON avviato: con host %s serve un "token" nel config (o host 127.0.0.1).' % host)
        return 1
    srv = ThreadingHTTPServer((host, cfg['port']), Handler)
    print('AurI Bridge su porta %d, cartella %s' % (cfg['port'], cfg['cwd']))
    srv.serve_forever()


if __name__ == '__main__':
    main()
