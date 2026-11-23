const fs = require('fs');
const path = require('path');
const D = require('docx');
const { Document, Packer, Paragraph, TextRun, HeadingLevel, Table, TableRow, TableCell, WidthType, ShadingType, ImageRun, AlignmentType, LevelFormat, PageBreak, BorderStyle, Footer, PageNumber } = D;

const ROOT = process.argv[2];
const PH = path.join(ROOT, 'docs', 'photos');
const W = 9638; // A4 content width with 2 cm margins

const P = (t, o = {}) => new Paragraph({ spacing: { after: 120 }, ...o, children: [].concat(t).map(x => typeof x === 'string' ? new TextRun(x) : x) });
const B = t => new TextRun({ text: t, bold: true });
const H1 = t => new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun(t)] });
const H2 = t => new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun(t)] });
const LI = (t, lvl = 0) => new Paragraph({ numbering: { reference: 'b', level: lvl }, spacing: { after: 60 }, children: [].concat(t).map(x => typeof x === 'string' ? new TextRun(x) : x) });
const NUM = (t, ref) => new Paragraph({ numbering: { reference: ref, level: 0 }, spacing: { after: 60 }, children: [].concat(t).map(x => typeof x === 'string' ? new TextRun(x) : x) });

function box(title, text, color = 'E8F0E0') {
  return new Table({
    width: { size: W, type: WidthType.DXA }, columnWidths: [W],
    rows: [new TableRow({ children: [new TableCell({
      width: { size: W, type: WidthType.DXA },
      shading: { type: ShadingType.CLEAR, fill: color, color: 'auto' },
      margins: { top: 120, bottom: 120, left: 180, right: 180 },
      children: [new Paragraph({ children: [new TextRun({ text: title + '  ', bold: true }), new TextRun(text)] })],
    })] })],
  });
}

function table(head, rows, widths) {
  const sum = widths.reduce((a, b) => a + b, 0);
  widths = widths.map(w => Math.round(w * W / sum));
  widths[widths.length - 1] += W - widths.reduce((a, b) => a + b, 0);
  const cell = (t, i, h) => new TableCell({
    width: { size: widths[i], type: WidthType.DXA },
    shading: h ? { type: ShadingType.CLEAR, fill: '2F4F2F', color: 'auto' } : undefined,
    margins: { top: 60, bottom: 60, left: 100, right: 100 },
    children: [new Paragraph({ children: [new TextRun({ text: t, bold: h, color: h ? 'FFFFFF' : undefined, size: 19 })] })],
  });
  return new Table({
    width: { size: W, type: WidthType.DXA }, columnWidths: widths,
    rows: [new TableRow({ tableHeader: true, children: head.map((t, i) => cell(t, i, true)) }),
      ...rows.map(r => new TableRow({ children: r.map((t, i) => cell(t, i, false)) }))],
  });
}

let fig = 0;
function img(file, caption, maxW = 380, maxH = 520) {
  const buf = fs.readFileSync(path.join(PH, file));
  const w = buf.readUInt16BE ? null : null;
  const dim = jpegSize(buf);
  const r = Math.min(maxW / dim.w, maxH / dim.h);
  fig++;
  return [
    new Paragraph({ alignment: AlignmentType.CENTER, keepNext: true, spacing: { before: 120 }, children: [new ImageRun({ type: 'jpg', data: buf, transformation: { width: Math.round(dim.w * r), height: Math.round(dim.h * r) } })] }),
    new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 }, children: [new TextRun({ text: `Figura ${fig}: ${caption}`, italics: true, size: 18 })] }),
  ];
}
function jpegSize(b) {
  let i = 2;
  while (i < b.length) {
    const m = b[i + 1], len = b.readUInt16BE(i + 2);
    if (m >= 0xC0 && m <= 0xC3) return { h: b.readUInt16BE(i + 5), w: b.readUInt16BE(i + 7) };
    i += 2 + len;
  }
  throw new Error('no SOF');
}
const sp = () => new Paragraph({ children: [] });

const body = [
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { before: 600 }, children: [new TextRun({ text: 'PROGETTO OPEN HARDWARE', size: 20, color: '556B2F', bold: true })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: 'AurI-3310', size: 64, bold: true })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 240 }, children: [new TextRun({ text: 'Un Nokia 3310 originale con cervello ESP32-S3, Wi-Fi, Home Assistant e una shell Claude in tasca', size: 26, italics: true })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: 'Piano Maestro v2.0  |  23 novembre 2026  |  Autore: Luigi Califano', size: 20 })] }),
  new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 240 }, children: [new TextRun({ text: 'Sostituisce "3310OS Piano Maestro v1.1". Le parti valide sono state mantenute, le decisioni aperte sono state chiuse.', size: 18, color: '666666' })] }),
  ...img('13_panoramica_smontaggio.jpg', 'il telefono smontato: scheda madre (lato tasti), telaio UI con altoparlante e connettore LCD, fondello.', 360, 560),
  box('OBIETTIVO', 'Sostituire la scheda madre di un Nokia 3310 originale (NHM-5NX) con una scheda nuova basata su ESP32-S3, riusando scocca, display, tastiera, altoparlante e vibrazione. Il telefono diventa un terminale smart: sistema operativo AurI, giochi, orologio, controllo Home Assistant e una shell conversazionale verso Claude. La scheda originale resta intatta e conservata.'),
  new Paragraph({ children: [new PageBreak()] }),

  H1('1. Cosa cambia rispetto alla v1.1'),
  P('La v1.1 era un ottimo lavoro di inventario, ma trattava come incognite cose già note e lasciava aperte decisioni che si possono chiudere subito. La v2.0 parte dalle foto e dalla documentazione esistente e fissa una direzione.'),
  table(['Tema', 'v1.1', 'v2.0'], [
    ['MCU', 'C3 candidato, S3 per la camera', 'ESP32-S3 deciso. Chip nudo QFN56 (7x7x0,9 mm) se il modulo da 2,4 mm non entra'],
    ['Tastiera', 'Mappare elettricamente ROW/COL della scheda originale', 'Inutile: gli anelli sono sulla scheda madre. La nuova PCB li ridisegna e li cabla dove vuole'],
    ['Display', 'Pinout e tensioni sconosciuti', 'PCD8544 84x48, 8 contatti a molla, pinout documentato dalla community. Si verifica con un solo test a 3,3 V'],
    ['Batteria', 'BLC-1 da ispezionare', 'BLC-1 conservata come reperto. Si usa una cella Li-ion nuova compatibile'],
    ['Fotocamera', 'Requisito della prima release', 'Spostata alla v2 hardware: ingombro 5,85 mm e rischio alto'],
    ['Software', 'Solo firmware ESP-IDF in C', 'MicroPython su telefono e PC + AurI Bridge (shell Claude) su Raspberry Pi'],
    ['Metodo', '10 fasi con gate', 'Si sviluppa in parallelo: software subito sul simulatore, hardware al banco, PCB dopo la scansione 1:1'],
  ], [2, 4, 5]),

  H1('2. Identificazione dell\'esemplare'),
  table(['Elemento', 'Dato', 'Fonte'], [
    ['Scansione PCB', '600 dpi: 47,2 x 112,1 mm (fronte), 47,3 x 113,0 mm (retro)', 'docs/scans'],
    ['Telefono', 'Nokia 3310, Type NHM-5NX, Code 0504299, made in Finland', 'Etichetta (fig. 2)'],
    ['PCB', 'Serigrafia UB4_12, codice 9854424, MOD +1-3, lato tasti B433133', 'Macro (fig. 3, 7)'],
    ['Telaio UI', 'C02600 / A3426 / PET 1, lotto 01152P06431DN', 'Fig. 8'],
    ['Fondello', 'H3C4342J06', 'Fig. 13'],
    ['LCD', 'LPH-7779 (famiglia "Beetle"), controller PCD8544, 84x48 px', 'Manuale PAMS + community'],
    ['Batteria', 'Nokia BLC-1, Li-ion 3,6 V nominali', 'Etichetta (fig. 11)'],
  ], [2, 5, 2]),
  ...img('12_panoramica_etichetta.jpg', 'panoramica con etichetta NHM-5NX / Model 3310.', 340, 520),

  H1('3. Lettura tecnica delle foto'),
  P('Questa è la parte più importante del documento: dalle foto si ricava quasi tutta l\'architettura meccanica ed elettrica che serve alla nuova scheda.'),
  H2('3.1 Tastiera: gli anelli sono sulla scheda madre'),
  P('Il lato inferiore della PCB porta 23 piazzole a doppio anello dorato (anello esterno e centro separati da un gap). Il foglio bianco del telaio UI porta le cupolette metalliche: premendo un tasto, la cupoletta chiude anello e centro. Non c\'è alcun connettore tra tastiera e scheda madre.'),
  P([B('Conseguenza: '), 'la nuova PCB deve solo riprodurre la geometria degli anelli nella stessa posizione. Il cablaggio (matrice o GPIO diretti) lo scegliamo noi. La mappatura ROW/COL della scheda originale proposta nella v1.1 non serve.']),
  P('Le 8 piccole finestre quadrate tra gli anelli (4 in alto, 4 in mezzo) ospitano i LED di retroilluminazione tastiera, montati sul lato tasti e visibili attraverso i fori del foglio bianco. I 2 LED alti del display sono nella fila superiore.'),
  ...img('11_pcb_lato_tasti_completo.jpg', 'lato tasti completo: area LCD in alto, 23 anelli, 8 LED tastiera, 9 piazzole del connettore inferiore.', 330, 560),
  ...img('14_pcb_e_telaio_ui.jpg', 'PCB e telaio UI affiancati: ogni cupoletta corrisponde a un anello, ogni foro tondo a un LED.', 360, 560),
  H2('3.2 Display: connettore a molla a 8 contatti'),
  P('Il modulo LCD è fissato al telaio UI e si collega alla scheda tramite un connettore a 8 molle (visibile sotto l\'altoparlante, fig. 8). Sulla PCB corrisponde la "land" rettangolare con 8 piazzole affiancate e un foro di centraggio (fig. 7). Sotto ci sono due piazzole tonde per l\'altoparlante, che si connette anch\'esso a pressione.'),
  table(['Pin (community)', 'Segnale', 'Note'], [
    ['1', 'VDD', '2,7 - 3,3 V'], ['2', 'SCLK', 'clock SPI'], ['3', 'SDIN', 'dati SPI (MOSI)'], ['4', 'D/C', 'dato/comando'],
    ['5', 'SCE', 'chip select, attivo basso'], ['6', 'GND', ''], ['7', 'VOUT', 'condensatore 1-10 uF verso GND (pompa di carica interna)'], ['8', 'RES', 'reset, attivo basso'],
  ], [2, 2, 5]),
  box('DA VERIFICARE', 'L\'ordine dei pin va confermato sul nostro esemplare, contando dalla parte del foro di centraggio. Il test è semplice e non rischioso: display su breakout stampata, 3,3 V da alimentatore limitato a 20 mA, sequenza di init PCD8544.', 'FFF4D6'),
  ...img('10_telaio_ui_lcd_connettore.jpg', 'telaio UI: altoparlante (in alto) e connettore LCD a 8 molle.', 330, 520),
  ...img('08_pcb_retro_lcd_land.jpg', 'land LCD a 8 piazzole, piazzole altoparlante e zona tasti superiore.', 330, 520),
  H2('3.3 Fondello: batteria, SIM, vibrazione, microfono'),
  P('Nel fondello (fig. 4) si vedono: contatti batteria a lamella (3 poli: +, BSI, -), lettore SIM a 6 contatti, motore di vibrazione con contatti a molla, capsula microfono con due contatti dorati, lamelle verso il connettore inferiore e la presa jack di ricarica. Sul bordo inferiore (fig. 5): jack DC, due contatti dorati di ricarica rapida, presa auricolare e foro microfono.'),
  P([B('Riuso previsto: '), 'motore vibrazione (driver MOSFET), microfono (preamplificatore + ADC, oppure sostituito da un MEMS I2S), contatti batteria. La SIM non serve: non c\'è modem cellulare. La presa DC si può riusare come ingresso 5 V oppure si aggiunge una USB-C nascosta sotto la batteria.']),
  ...img('02_fondello_interno.jpg', 'interno fondello: contatti batteria, SIM, vibrazione, microfono, lamelle del connettore inferiore.', 460, 320),
  ...img('03_fondello_bordo_connettori.jpg', 'bordo inferiore: foro microfono, presa auricolare, contatti di ricarica, jack DC.', 460, 300),
  H2('3.4 Lato componenti e spazio in altezza'),
  P('Il lato componenti è quasi tutto coperto da schermature RF saldate. La nuova scheda non ne ha bisogno: libera tutta quell\'altezza (circa 1,5-2 mm sopra la PCB) per MCU, regolatori e caricatore. È il dato che rende credibile un ESP32-S3 interno anche con il modulo da 2,4 mm, da confermare con il calibro.'),
  ...img('05_pcb_componenti_alto.jpg', 'parte alta lato componenti: schermature RF, piazzole antenna.', 300, 480),
  ...img('06_pcb_componenti_basso.jpg', 'parte bassa lato componenti: alimentazione e ricarica originali.', 300, 480),
  ...img('04_pcb_macro_ub4_12.jpg', 'macro: UB4_12, 9854424, MOD +1-3.', 300, 480),
  ...img('01_batteria_blc1.jpg', 'batteria BLC-1 Li-ion 3,6 V: reperto da conservare, non da riusare.', 260, 420),
  ...img('09_frontale_display.jpg', 'frontale con display e guida luce tastiera.', 280, 460),
  H2('3.5 I pezzi originali che restano'),
  P('Scansione a 600 dpi di tutti i componenti affiancati. Cover, display, tappetino tasti, altoparlante, vibrazione e microfono tornano nel telefono; scheda madre e batteria BLC-1 restano reperti.'),
  ...img('15_componenti_fronte.jpg', 'tutti i componenti, lato esterno: cover, guscio frontale, tappetino, batteria, scheda madre, telaio UI, fondello.', 480, 320),
  ...img('16_componenti_retro.jpg', 'tutti i componenti, lato interno: stessi pezzi girati, con display e altoparlante sul telaio UI.', 480, 320),

  H1('4. Architettura hardware'),
  table(['Blocco', 'Scelta', 'Motivo'], [
    ['MCU', 'ESP32-S3 (modulo MINI-1 o chip nudo QFN56 + flash/PSRAM)', '45 GPIO, PSRAM, USB nativo, Wi-Fi + BLE, DVP per una futura camera'],
    ['Antenna', 'Chip antenna 2,4 GHz nella zona dell\'antenna GSM originale (in alto)', 'È la zona pensata da Nokia per irradiare, lontana dalla batteria'],
    ['Display', 'LCD originale via SPI, VOUT con 4,7 uF', 'Driver PCD8544 standard'],
    ['Tastiera', '23 anelli ridisegnati, matrice 5x5 su GPIO diretti', 'Niente expander, scansione con interrupt per il risveglio'],
    ['Retroilluminazione', '10 LED SMD 0603 verdi, driver a corrente costante PWM', 'Effetto originale'],
    ['Audio', 'Altoparlante originale + amplificatore I2S MAX98357A o PWM + MOSFET', 'Suonerie, bip, eventuale TTS'],
    ['Microfono', 'Capsula originale del 2000 con preamplificatore e ADC; MEMS I2S (ICS-43434) solo come piano B', 'Push-to-talk verso la shell Claude'],
    ['Vibrazione', 'Motore originale, MOSFET + diodo di ricircolo', ''],
    ['Batteria', 'Cella Li-ion nuova nel guscio BLC-1 o compatibile', 'La BLC-1 originale resta reperto'],
    ['Ricarica', 'BQ24072/TP4056-class + protezione + fuel gauge MAX17048', 'Percentuale batteria reale sul display'],
    ['USB', 'USB-C 5 V nascosto o jack DC originale; programmazione via pad USB nativi', 'Nessun taglio della scocca originale'],
  ], [2, 4, 4]),
  H2('4.1 Budget GPIO (ESP32-S3)'),
  table(['Funzione', 'GPIO'], [
    ['LCD (SCLK, SDIN, D/C, SCE, RES)', '5'], ['Tastiera 5x5 + power', '11'], ['Backlight PWM', '1'], ['Vibrazione', '1'],
    ['Audio I2S out (BCLK, WS, DOUT)', '3'], ['Microfono I2S in (DIN, condivide BCLK/WS)', '1'], ['I2C (fuel gauge)', '2'], ['Stato carica, USB D+/D-', '3'],
    ['Totale', '27 su 45: margine ampio, nessun expander'],
  ], [5, 3]),

  H1('5. Architettura software'),
  P('Il software si divide in tre parti, tutte nello stesso repository:'),
  LI([B('firmware/'), ': AurI OS in MicroPython (v1.29+). Livello HAL (display, tastiera, audio, power) separato dalla UI, così lo stesso codice gira sul telefono e sul PC.']),
  LI([B('firmware/sim/'), ': simulatore PC in Python con tkinter, nessuna dipendenza. Esegue lo stesso codice del telefono e salva screenshot.']),
  LI([B('bridge/'), ': AurI Bridge in Python, gira sul Raspberry Pi accanto a Home Assistant. Riceve richieste dal telefono e parla con Claude e con HA.']),
  H2('5.1 AurI OS: funzioni'),
  table(['App', 'Descrizione'], [
    ['Boot e home', 'Logo AurI, orologio NTP, icone Wi-Fi e batteria'],
    ['Claude', 'Shell conversazionale: input T9 o vocale, risposta a scorrimento, conferma azioni con il tasto Navi'],
    ['Casa', 'Stanze, luci, prese, scene, sensori da Home Assistant'],
    ['Giochi', 'Serpente e altri giochi originali in pixel art 84x48'],
    ['Strumenti', 'Sveglia, timer, calcolatrice, torcia (backlight)'],
    ['Impostazioni', 'Wi-Fi, bridge, suoni, contrasto, aggiornamento OTA'],
  ], [2, 6]),
  H2('5.2 Shell Claude: come funziona'),
  NUM('L\'utente scrive in T9 o tiene premuto il tasto Navi (quello grande sotto lo schermo) e parla.', 'n1'),
  NUM('Il telefono invia testo o audio al Bridge via HTTPS sulla LAN (o VPN WireGuard/Tailscale fuori casa), autenticandosi con un token di dispositivo.', 'n1'),
  NUM('Il Bridge trascrive l\'audio, chiama Claude tramite API Anthropic con un set di strumenti dichiarati (Home Assistant, stato server, comandi whitelisted).', 'n1'),
  NUM('Ogni azione che modifica qualcosa viene proposta al telefono come richiesta di conferma: testo breve sul display, Navi conferma, C annulla (il 3310 non ha tasti verde e rosso).', 'n1'),
  NUM('La risposta torna come testo impaginato a 14 colonne, con scorrimento.', 'n1'),
  box('SICUREZZA', 'La chiave API resta solo sul Bridge. Il telefono ha un token revocabile. Gli strumenti sono una whitelist esplicita: nessuna shell libera esposta. Niente esposizione del Bridge su Internet senza VPN.', 'FBE3E3'),
  H2('5.3 Protocollo'),
  table(['Endpoint Bridge', 'Uso'], [
    ['POST /v1/chat', 'Messaggio testo, risposta in streaming a righe'],
    ['POST /v1/voice', 'Audio PCM 16 kHz, trascrizione + risposta'],
    ['POST /v1/confirm', 'Conferma o rifiuto di un\'azione proposta'],
    ['GET /v1/home', 'Stato entità Home Assistant selezionate'],
    ['MQTT auri/<id>/...', 'Eventi e telemetria (batteria, RSSI, tasti)'],
  ], [3, 5]),

  H1('5bis. Sensori e voce'),
  P("L'ESP32-S3 non misura l'ambiente: servono sensori I2C minuscoli, tutti sullo stesso bus (2 pin), circa 10 euro in tutto."),
  table(['Funzione', 'Componente', 'Uso'], [
    ['Temperatura e umidità', 'Sensirion SHT40 (1,5 x 1,5 mm)', 'Home, Home Assistant, avvisi. Vicino al foro del microfono, isolato da una fessura nella PCB'],
    ['Pressione', 'Bosch BMP390', 'Meteo locale, altitudine'],
    ['Movimento', 'LIS2DH12', 'Scuoti per sbloccare, capovolgi per silenziare, contapassi'],
    ['Luce ambiente', 'VEML7700', 'Retroilluminazione automatica'],
    ['Batteria', 'MAX17048', 'Percentuale reale'],
  ], [3, 3, 5]),
  P('I valori vengono inviati al bridge ogni 5 minuti e compaiono in Home Assistant come sensor.auri_3310_*.'),
  H2('Voce'),
  P("Tenendo premuto Navi nella console Claude si parla; al rilascio l'audio va al bridge, che lo trascrive con faster-whisper, lo passa a Claude Code e legge la risposta con Piper (voce italiana Paola). Tutto gira in locale tranne Claude. Il microfono previsto è la capsula originale del 3310 con un preamplificatore; un MEMS I2S resta come piano B."),
  P('Il bridge e i modelli vocali stanno interamente nella cartella bridge/ (.venv e models): per rimuoverli basta cancellarle, per spostarli su un altro computer basta lanciare setup.sh o setup.ps1.'),
  H1('6. Roadmap'),
  table(['Fase', 'Contenuto', 'Hardware necessario', 'Uscita'], [
    ['S0', 'Repo, simulatore, UI base, giochi, T9', 'Nessuno', 'AurI OS gira sul PC'],
    ['S1', 'AurI Bridge + shell Claude nel simulatore', 'Raspberry Pi esistente', 'Conversazione dal simulatore'],
    ['H0', 'DevKit ESP32-S3 + display 5110 + tastierino', 'DevKit, display, pulsanti', 'Firmware reale al banco'],
    ['H1', 'Test LCD originale e altoparlante su breakout', 'Breakout stampata o pogo pin', 'Pinout LCD confermato'],
    ['M0', 'Scansione 600 dpi, outline DXF, misure Z', 'Scanner, calibro', 'Outline e mappa altezze'],
    ['P0', 'Schema e PCB KiCad R0, spessore 1,0 mm', 'Nessuno', 'Gerber + stampa 1:1 per fit check'],
    ['P1', 'PCB R1 assemblata, bring-up', 'PCB, componenti', 'Telefono chiuso che si accende'],
    ['V1', 'Release pubblica', '', 'Video, BOM, guida montaggio'],
    ['V2', 'Fotocamera OV2640 su fondello accessorio', 'Sensore + fondello stampato', 'Foto JPEG verso HA'],
  ], [1, 4, 3, 3]),

  H1('7. Lista acquisti per il banco'),
  table(['Oggetto', 'Qtà', 'Note'], [
    ['ESP32-S3-DevKitC-1 N8R8', '1', 'Sviluppo firmware'],
    ['Display Nokia 5110 su breakout', '2', 'Stesso controller, costa pochi euro'],
    ['Pulsanti tattili 6x6 o tastierino 4x4', '1 set', 'Simulare la tastiera'],
    ['MAX98357A breakout + altoparlantino 8 ohm', '1', 'Audio'],
    ['ICS-43434 o INMP441 breakout', '1', 'Microfono I2S'],
    ['Alimentatore da banco limitato, multimetro, calibro', '1', 'Se non già presenti'],
    ['Pogo pin 1 mm', '20', 'Contatto non distruttivo con LCD originale'],
  ], [4, 1, 4]),

  H1('8. Regole del progetto'),
  LI('La scheda madre originale e la batteria BLC-1 non vengono modificate, alimentate o ricaricate.'),
  LI('Nessun taglio o foro sulla scocca originale. Eventuali modifiche vanno su parti stampate sostitutive.'),
  LI('Tutto open source: firmware e bridge con licenza MIT, hardware con CERN-OHL-S.'),
  LI('Nessun materiale protetto da copyright Nokia nel repository (manuali, firmware, loghi): solo link.'),

  H1('9. Riferimenti'),
  LI('Nokia PAMS NHM-5NX, Schematics and Layouts UB4-12 (link nel README, non ridistribuito).'),
  LI('hoani/3310_pico: outline DXF e footprint della scheda 3310.'),
  LI('M17-Project/M17_3310: mainboard sostitutiva, spessore PCB 1,0 mm.'),
  LI('PCD8544 datasheet (Philips) e guida Adafruit Nokia 5110/3310 LCD.'),
  LI('Espressif ESP32-S3 datasheet e documentazione ESP-IDF.'),
  LI('Home Assistant: integrazione MQTT e API REST.'),
  LI('Anthropic: documentazione Messages API e tool use.'),
];

const doc = new Document({
  creator: 'Luigi Califano', title: 'AurI-3310 Piano Maestro v2.0',
  styles: {
    default: { document: { run: { font: 'Calibri', size: 22 } } },
    paragraphStyles: [
      { id: 'Heading1', name: 'Heading 1', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: { font: 'Calibri', size: 32, bold: true, color: '2F4F2F' }, paragraph: { spacing: { before: 360, after: 160 }, keepNext: true, outlineLevel: 0 } },
      { id: 'Heading2', name: 'Heading 2', basedOn: 'Normal', next: 'Normal', quickFormat: true, run: { font: 'Calibri', size: 26, bold: true, color: '556B2F' }, paragraph: { spacing: { before: 240, after: 120 }, keepNext: true, outlineLevel: 1 } },
    ],
  },
  numbering: { config: [
    { reference: 'b', levels: [{ level: 0, format: LevelFormat.BULLET, text: '•', alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 270 } } } }] },
    { reference: 'n1', levels: [{ level: 0, format: LevelFormat.DECIMAL, text: '%1.', alignment: AlignmentType.LEFT, style: { paragraph: { indent: { left: 540, hanging: 270 } } } }] },
  ] },
  sections: [{
    properties: { page: { margin: { top: 1134, bottom: 1134, left: 1134, right: 1134 } } },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: 'AurI-3310  |  Piano Maestro v2.0  |  pagina ', size: 16, color: '888888' }), new TextRun({ children: [PageNumber.CURRENT], size: 16, color: '888888' })] })] }) },
    children: body,
  }],
});
Packer.toBuffer(doc).then(b => { fs.writeFileSync(path.join(ROOT, 'docs', 'AurI-3310_Piano_Maestro_v2_0.docx'), b); console.log('ok'); });
