# Interface strings. Only languages written in the Latin alphabet: the 5x8 LCD font has no other scripts yet.
LANGS = (
    ('it', 'Italiano'), ('en', 'English'), ('es', 'Espanol'),
    ('fr', 'Francais'), ('de', 'Deutsch'), ('pt', 'Portugues'),
)

DAYS = {
    'it': ('Lun', 'Mar', 'Mer', 'Gio', 'Ven', 'Sab', 'Dom'),
    'en': ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'),
    'es': ('Lun', 'Mar', 'Mie', 'Jue', 'Vie', 'Sab', 'Dom'),
    'fr': ('Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'),
    'de': ('Mo', 'Di', 'Mi', 'Do', 'Fr', 'Sa', 'So'),
    'pt': ('Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sab', 'Dom'),
}

# key: (it, en, es, fr, de, pt)
S = {
    'menu': ('Menu', 'Menu', 'Menu', 'Menu', 'Menu', 'Menu'),
    'select': ('Scegli', 'Select', 'Elegir', 'Choisir', 'Waehlen', 'Escolher'),
    'back': ('Indietro', 'Back', 'Atras', 'Retour', 'Zurueck', 'Voltar'),
    'confirm_q': ('Confermi?', 'Confirm?', 'Confirmar?', 'Confirmer?', 'Bestaetigen?', 'Confirmar?'),
    'no': ('No', 'No', 'No', 'Non', 'Nein', 'Nao'),
    'proceed_q': ('Procedo?', 'Go ahead?', 'Sigo?', 'Je continue?', 'Weiter?', 'Continuo?'),
    'claude': ('Claude', 'Claude', 'Claude', 'Claude', 'Claude', 'Claude'),
    'home': ('Casa', 'Home', 'Casa', 'Maison', 'Zuhause', 'Casa'),
    'snake': ('Serpente', 'Snake', 'Serpiente', 'Serpent', 'Schlange', 'Cobra'),
    'sensors': ('Sensori', 'Sensors', 'Sensores', 'Capteurs', 'Sensoren', 'Sensores'),
    'settings': ('Impostazioni', 'Settings', 'Ajustes', 'Reglages', 'Einstellung', 'Ajustes'),
    'info': ('Info', 'Info', 'Info', 'Info', 'Info', 'Info'),
    'language': ('Lingua', 'Language', 'Idioma', 'Langue', 'Sprache', 'Idioma'),
    'about': ('Un 3310 del 2000 con un cervello nuovo.', 'A 3310 from 2000 with a new brain.',
              'Un 3310 del 2000 con un cerebro nuevo.', 'Un 3310 de 2000 avec un nouveau cerveau.',
              'Ein 3310 von 2000 mit neuem Gehirn.', 'Um 3310 de 2000 com um cerebro novo.'),
    'bridge_down': ('Bridge non raggiungibile', 'Bridge unreachable', 'Bridge no disponible',
                    'Bridge injoignable', 'Bridge nicht erreichbar', 'Bridge indisponivel'),
    'bridge_err': ('Errore del bridge', 'Bridge error', 'Error del bridge', 'Erreur du bridge',
                   'Bridge-Fehler', 'Erro do bridge'),
    'error': ('Errore', 'Error', 'Error', 'Erreur', 'Fehler', 'Erro'),
    'done': ('Fatto', 'Done', 'Hecho', 'Fait', 'Erledigt', 'Feito'),
    'no_devices': ('Nessun dispositivo configurato nel bridge.', 'No devices configured on the bridge.',
                   'Ningun dispositivo en el bridge.', 'Aucun appareil sur le bridge.',
                   'Keine Geraete im Bridge.', 'Nenhum dispositivo no bridge.'),
    'no_sensors': ('Nessun sensore', 'No sensors', 'Sin sensores', 'Aucun capteur', 'Keine Sensoren', 'Sem sensores'),
    'temp': ('Temp', 'Temp', 'Temp', 'Temp', 'Temp', 'Temp'),
    'hum': ('Umid', 'Hum', 'Hum', 'Hum', 'Feucht', 'Umid'),
    'press': ('Press', 'Press', 'Pres', 'Pres', 'Druck', 'Pres'),
    'light': ('Luce', 'Light', 'Luz', 'Lum', 'Licht', 'Luz'),
    'game_over': ('Fine partita', 'Game over', 'Fin', 'Perdu', 'Verloren', 'Fim'),
    'points': ('Punti', 'Score', 'Puntos', 'Points', 'Punkte', 'Pontos'),
    'record': ('Record', 'Best', 'Record', 'Record', 'Rekord', 'Recorde'),
    'again': ('OK = ancora', 'OK = again', 'OK = otra', 'OK = encore', 'OK = nochmal', 'OK = de novo'),
    'options': ('Opzioni', 'Options', 'Opciones', 'Options', 'Optionen', 'Opcoes'),
    'model': ('Modello', 'Model', 'Modelo', 'Modele', 'Modell', 'Modelo'),
    'effort': ('Effort', 'Effort', 'Esfuerzo', 'Effort', 'Aufwand', 'Esforco'),
    'perms': ('Permessi', 'Permissions', 'Permisos', 'Permissions', 'Rechte', 'Permissoes'),
    'perm_ask': ('Chiedi sempre', 'Always ask', 'Preguntar', 'Toujours demander', 'Immer fragen', 'Perguntar'),
    'perm_edits': ('Accetta modifiche', 'Accept edits', 'Aceptar cambios', 'Accepter modifs', 'Aend. erlauben', 'Aceitar edicoes'),
    'perm_plan': ('Solo piano', 'Plan only', 'Solo plan', 'Plan seul', 'Nur Plan', 'So plano'),
    'new_session': ('Nuova sessione', 'New session', 'Nueva sesion', 'Nouvelle session', 'Neue Sitzung', 'Nova sessao'),
    'status': ('Stato', 'Status', 'Estado', 'Etat', 'Status', 'Estado'),
    'session': ('Sessione', 'Session', 'Sesion', 'Session', 'Sitzung', 'Sessao'),
    'new': ('nuova', 'new', 'nueva', 'nouvelle', 'neu', 'nova'),
    'with': ('with', 'with', 'with', 'with', 'with', 'with'),
    'effort_word': ('effort', 'effort', 'effort', 'effort', 'effort', 'effort'),
    'write': ('Scrivi...', 'Type...', 'Escribe...', 'Ecris...', 'Schreib...', 'Escreva...'),
    'send': ('Invia', 'Send', 'Enviar', 'Envoyer', 'Senden', 'Enviar'),
    'thinking': ('Sto pensando', 'Thinking', 'Pensando', 'Je reflechis', 'Denke nach', 'Pensando'),
    'listening': ('ti ascolto', 'listening', 'te escucho', 'j\'ecoute', 'ich hoere', 'ouvindo'),
    'no_voice': ('Voce non disponibile qui', 'Voice not available here', 'Voz no disponible',
                 'Voix indisponible ici', 'Sprache hier nicht da', 'Voz indisponivel'),
    'assistant': ('assistente', 'assistant', 'asistente', 'assistant', 'Assistent', 'assistente'),
    'offline': ('offline', 'offline', 'sin red', 'hors ligne', 'offline', 'offline'),
}

lang = 'it'
_idx = 0


def set_lang(code):
    global lang, _idx
    codes = [c for c, _n in LANGS]
    lang = code if code in codes else 'it'
    _idx = codes.index(lang)


def t(key):
    v = S.get(key)
    return v[_idx] if v else key


def days():
    return DAYS[lang]
