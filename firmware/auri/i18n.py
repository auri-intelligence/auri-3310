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
    'snake': ('Snake', 'Snake', 'Snake', 'Snake', 'Snake', 'Snake'),
    'pet': ('AurIpet', 'AurIpet', 'AurIpet', 'AurIpet', 'AurIpet', 'AurIpet'),
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
    'press_key': ('premi un tasto', 'press a key', 'pulsa una tecla', 'appuie', 'Taste druecken', 'prima tecla'),
    'new_record': ('NUOVO RECORD!', 'NEW BEST!', 'NUEVO RECORD!', 'NOUVEAU RECORD', 'NEUER REKORD!', 'NOVO RECORDE!'),
    # AurIpet
    'pet_feed': ('Cibo', 'Food', 'Comida', 'Manger', 'Essen', 'Comida'),
    'pet_play': ('Gioca', 'Play', 'Jugar', 'Jouer', 'Spielen', 'Brincar'),
    'pet_sleep': ('Dormi', 'Sleep', 'Dormir', 'Dormir', 'Schlafen', 'Dormir'),
    'pet_clean': ('Pulisci', 'Clean', 'Limpiar', 'Nettoyer', 'Putzen', 'Limpar'),
    'pet_hungry': ('Ho fame!', 'Hungry!', 'Hambre!', 'J ai faim!', 'Hunger!', 'Fome!'),
    'pet_bored': ('Giochiamo?', 'Play?', 'Jugamos?', 'On joue?', 'Spielen?', 'Brincamos?'),
    'pet_tired': ('Sonno...', 'Sleepy...', 'Sueno...', 'Sommeil...', 'Muede...', 'Sono...'),
    'pet_dirty': ('Che puzza!', 'Stinky!', 'Que olor!', 'Ca pue!', 'Stinkt!', 'Cheira mal!'),
    'pet_happy': ('Felice!', 'Happy!', 'Feliz!', 'Content!', 'Gluecklich!', 'Feliz!'),
    'pet_egg': ('Si schiude...', 'Hatching...', 'Va a nacer', 'Va eclore', 'Schluepft...', 'Vai nascer'),
    'pet_gone': ('Se n e andato... OK per un uovo nuovo', 'It left... OK for a new egg', 'Se fue... OK nuevo huevo', 'Parti... OK nouvel oeuf', 'Weg... OK neues Ei', 'Foi embora... OK ovo novo'),
    'pet_age': ('eta', 'age', 'edad', 'age', 'Alter', 'idade'),
    'need_bridge': ('Serve il bridge AurI: impostalo in config.json.', 'Needs the AurI bridge: set it in config.json.',
                    'Necesita el bridge AurI: configuralo en config.json.', 'Il faut le bridge AurI: voir config.json.',
                    'Braucht die AurI-Bridge: siehe config.json.', 'Precisa do bridge AurI: ver config.json.'),
    'need_bridge_web': ('Nel simulatore online non c e: questa funzione usa il bridge AurI sul PC di casa (AI, voce, domotica). Prova Snake, AurIpet e le impostazioni!',
                        'Not in the online simulator: this feature uses the AurI bridge on a home PC (AI, voice, smart home). Try Snake, AurIpet and the settings!',
                        'No esta en el simulador online: usa el bridge AurI en un PC de casa (IA, voz, domotica). Prueba Snake, AurIpet y los ajustes!',
                        'Pas dans le simulateur en ligne: il faut le bridge AurI sur un PC (IA, voix, domotique). Essaie Snake, AurIpet et les reglages!',
                        'Nicht im Online-Simulator: braucht die AurI-Bridge auf einem PC (KI, Sprache, Smart Home). Probier Snake, AurIpet und die Einstellungen!',
                        'Nao esta no simulador online: usa o bridge AurI num PC (IA, voz, casa). Experimenta Snake, AurIpet e os ajustes!'),
    # power, settings, battery
    'memory': ('Memoria', 'Memory', 'Memoria', 'Memoire', 'Speicher', 'Memoria'),
    'battery': ('Batteria', 'Battery', 'Bateria', 'Batterie', 'Akku', 'Bateria'),
    'network': ('Rete', 'Network', 'Red', 'Reseau', 'Netz', 'Rede'),
    'clock': ('Orologio', 'Clock', 'Reloj', 'Horloge', 'Uhr', 'Relogio'),
    'new': ('nuova', 'new', 'nueva', 'neuve', 'neu', 'nova'),
    'welcome': ('Ciao!', 'Hello!', 'Hola!', 'Salut!', 'Hallo!', 'Ola!'),
    'goodbye': ('Arrivederci', 'Goodbye', 'Adios', 'Au revoir', 'Tschuess', 'Adeus'),
    'charger_on': ('In carica', 'Charging', 'Cargando', 'En charge', 'Laedt', 'A carregar'),
    'charger_off': ('Caricatore scollegato', 'Charger removed', 'Cargador desconectado', 'Chargeur retire', 'Ladegeraet getrennt', 'Carregador removido'),
    'battery_full': ('Batteria carica', 'Battery full', 'Bateria llena', 'Batterie pleine', 'Akku voll', 'Bateria cheia'),
    'battery_low': ('Batteria scarica', 'Battery low', 'Bateria baja', 'Batterie faible', 'Akku schwach', 'Bateria fraca'),
    'charging': ('In carica', 'Charging', 'Cargando', 'En charge', 'Laedt', 'A carregar'),
    'on_battery': ('A batteria', 'On battery', 'Con bateria', 'Sur batterie', 'Akkubetrieb', 'Na bateria'),
    'profiles': ('Profili', 'Profiles', 'Perfiles', 'Profils', 'Profile', 'Perfis'),
    'prof_normal': ('Normale', 'Normal', 'Normal', 'Normal', 'Normal', 'Normal'),
    'prof_silent': ('Silenzioso', 'Silent', 'Silencio', 'Silencieux', 'Lautlos', 'Silencio'),
    'prof_meeting': ('Riunione', 'Meeting', 'Reunion', 'Reunion', 'Besprechung', 'Reuniao'),
    'prof_outdoor': ('All aperto', 'Outdoor', 'Exterior', 'Exterieur', 'Draussen', 'Exterior'),
    'prof_custom': ('Personale', 'Custom', 'Personal', 'Perso', 'Eigenes', 'Pessoal'),
    'power_off': ('Spegni', 'Switch off', 'Apagar', 'Eteindre', 'Ausschalten', 'Desligar'),
    'tones': ('Toni', 'Tones', 'Tonos', 'Sonneries', 'Toene', 'Toques'),
    'ringtone': ('Suoneria', 'Ringtone', 'Tono', 'Sonnerie', 'Klingelton', 'Toque'),
    'volume': ('Volume', 'Volume', 'Volumen', 'Volume', 'Lautst.', 'Volume'),
    'vibration': ('Vibra', 'Vibra', 'Vibrar', 'Vibreur', 'Vibra', 'Vibrar'),
    'keytones': ('Toni tasti', 'Key tones', 'Tonos tecl', 'Bips touch', 'Tastentoene', 'Tons tecla'),
    'display': ('Display', 'Display', 'Pantalla', 'Ecran', 'Display', 'Ecra'),
    'backlight': ('Luce', 'Light', 'Luz', 'Lumiere', 'Licht', 'Luz'),
    'always': ('sempre', 'always', 'siempre', 'toujours', 'immer', 'sempre'),
    'boot_anim': ('Avvio', 'Start-up', 'Inicio', 'Demarrage', 'Start', 'Arranque'),
    'clock_fmt': ('Formato', 'Format', 'Formato', 'Format', 'Format', 'Formato'),
    'on': ('si', 'on', 'si', 'oui', 'an', 'sim'),
    'off': ('no', 'off', 'no', 'non', 'aus', 'nao'),
    'reset': ('Ripristina', 'Reset', 'Restablecer', 'Reinitialiser', 'Zuruecksetzen', 'Repor'),
    'reset_q': ('Ripristino le impostazioni di fabbrica?', 'Restore factory settings?', 'Restablecer ajustes de fabrica?', 'Retablir les reglages d usine?', 'Werkseinstellungen wiederherstellen?', 'Repor definicoes de fabrica?'),
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
