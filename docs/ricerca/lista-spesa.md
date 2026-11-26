# Lista della spesa AurI-3310

Prezzi indicativi a novembre 2026, IVA inclusa quando si compra da Amazon.it o AliExpress. Su Mouser, DigiKey e LCSC i prezzi cambiano spesso: controllali prima di ordinare.
Le misure segnate **(da verificare)** vengono da venditori e non dal datasheet: vanno misurate col calibro appena arriva il pezzo.
Fasi: **F1** = banco di prova, **F2** = prototipo dentro la cover, **F3** = extra (fotocamera, proiettore).

Foto reali: dove non c'è un'immagine su Wikimedia Commons uso la pagina del produttore, che ha foto ufficiali con copyright del produttore. Si possono guardare, ma non vanno copiate nel repo.

## Conteggio dei GPIO (da leggere prima di comprare la fotocamera)

L'ESP32-S3 ha 45 GPIO. Sul modulo N8R8 i GPIO 26-32 servono alla flash e i 33-37 alla PSRAM ottale; 19 e 20 sono l'USB; 0, 3, 45 e 46 sono pin di strapping ([datasheet ESP32-S3-WROOM-1](https://www.espressif.com/sites/default/files/documentation/esp32-s3-wroom-1_wroom-1u_datasheet_en.pdf)). Restano circa **30 GPIO usabili**.

| Uso (da `firmware/hal/board.py`) | GPIO |
|---|---|
| Display PCD8544 (SCLK, SDIN, DC, SCE, RES) | 5 |
| Retroilluminazione, vibrazione | 2 |
| Tastiera a matrice 4x4 | 8 |
| I2C (SDA, SCL) | 2 |
| Tasto accensione, ADC batteria, stato carica, piezo | 4 |
| microSD SPI | 4 |
| I2S: BCLK e WS in comune, DIN microfono, DOUT amplificatore | 4 |
| **Totale senza fotocamera** | **29** |
| OV2640 DVP (8 dati + VSYNC, HREF, PCLK, XCLK; il bus SCCB va sull'I2C) | +12 |

**La fotocamera non ci sta così com'è.** Per liberare 8 pin si sposta la tastiera su un controller I2C **TCA8418** (scansiona da solo fino a 8x10 tasti, [datasheet TI](https://www.ti.com/lit/ds/symlink/tca8418.pdf)); in più il piezo può sparire, perché i toni li fa il MAX98357A. Con queste due modifiche: 29 − 8 − 1 = 20, più 12 della fotocamera, fa 32. È ancora al limite e servono i pin di strapping. In alternativa si usa un ESP32-S3 con la fotocamera già montata (vedi la riga 8b).

## Componenti

| # | Componente / modello esatto | Q.tà (con scorte) | Misure, peso | Tensione / corrente | Datasheet | Foto reale (licenza) | Prezzo, dove | Fase |
|---|---|---|---|---|---|---|---|---|
| 1 | Espressif **ESP32-S3-DevKitC-1-N8R8** | 2 | 69 x 25,4 mm circa, ~8 g (da verificare) | 5 V USB o 3,3 V; picchi Wi-Fi ~350 mA | [guida utente](https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32s3/esp32-s3-devkitc-1/user_guide.html) | [foto Espressif](https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32s3/esp32-s3-devkitc-1/user_guide.html) (© Espressif) | 15-18 € Mouser/DigiKey; 8-12 € AliExpress | F1 |
| 2 | **ESP32-S3-WROOM-1-N8R8** (modulo per la scheda finale) | 3 | 18 x 25,5 x 3,1 mm | 3,0-3,6 V, picchi ~350 mA | [datasheet](https://www.espressif.com/sites/default/files/documentation/esp32-s3-wroom-1_wroom-1u_datasheet_en.pdf) | pagina del produttore (© Espressif) | 4-6 € LCSC/Mouser | F2 |
| 3 | Display **PCD8544** (breakout "5110" 84x48) | 2 | ~45 x 45 mm, ~10 g; area attiva 35 x 25 mm circa (da verificare) | 2,7-3,3 V, < 1 mA senza retroilluminazione | [datasheet PCD8544](https://www.sparkfun.com/datasheets/LCD/Monochrome/Nokia5110.pdf) | [SparkFun LCD-10168](https://www.sparkfun.com/products/10168) (CC BY 2.0) | 3-5 € AliExpress, 8 € Amazon | F1 |
| 4 | Modulo **microSD SPI** senza level shifter (3,3 V) + scheda microSD 16 GB classe 10 | 2 + 2 | ~18 x 20 mm | 3,3 V, picchi ~100 mA in scrittura | [specifica SD semplificata](https://www.sdcard.org/downloads/pls/) | [Adafruit 4682](https://www.adafruit.com/product/4682) (© Adafruit) | 2 € + 6 € Amazon/AliExpress | F1 |
| 5 | Microfono I2S **INMP441** (breakout) | 3 | breakout ~14 mm Ø; MEMS 4,72 x 3,76 x 1 mm | 1,8-3,3 V, 1,4 mA | [datasheet TDK](https://invensense.tdk.com/wp-content/uploads/2015/02/INMP441.pdf) | pagina del produttore (© TDK) | 2-3 € AliExpress | F1 |
| 6 | Amplificatore I2S **MAX98357A** (Adafruit 3006 o clone) | 2 | 17,8 x 19,3 mm | 2,5-5,5 V, fino a 3,2 W su 4 Ω | [datasheet ADI](https://www.analog.com/media/en/technical-documentation/data-sheets/MAX98357A-MAX98357B.pdf) | [Adafruit 3006](https://www.adafruit.com/product/3006) (© Adafruit) | 2-3 € AliExpress, 7 € Adafruit | F1 |
| 7 | Altoparlante 8 Ω 1 W da 20 mm Ø (per il banco; nel telefono resta quello originale) | 2 | 20 x 4 mm circa | — | scheda del venditore | — | 2 € | F1 |
| 8 | Fotocamera **OV2640** DVP, 2 MP, cavo flat 24 pin | 2 | modulo ~8,5 x 8,5 mm | 1,2/2,8/3,3 V, ~40 mA | [datasheet OV2640](https://www.uctronics.com/download/cam_module/OV2640DS.pdf) | — | 4-6 € AliExpress | F3 |
| 8b | in alternativa: **Freenove ESP32-S3-WROOM CAM** (fotocamera già cablata) | 1 | 63 x 27 mm (da verificare) | 5 V USB | [GitHub Freenove](https://github.com/Freenove/Freenove_ESP32_S3_WROOM_Board) | stesso link (© Freenove) | 15-20 € Amazon | F3 |
| 9 | Controller tastiera I2C **TCA8418** (breakout Adafruit 4918) | 2 | QFN 3 x 3 mm; breakout 25 x 18 mm | 1,65-3,6 V, ~50 µA | [datasheet TI](https://www.ti.com/lit/ds/symlink/tca8418.pdf) | [Adafruit 4918](https://www.adafruit.com/product/4918) (© Adafruit) | 6 € | F2 |
| 10 | Batteria **LiPo 603450** 3,7 V ~1000 mAh con PCM (protezione) | 2 | 50 x 34 x 6 mm, ~20 g | 3,0-4,2 V | scheda del venditore | — | 6-8 € Amazon/AliExpress | F2 |
| 10b | in alternativa, se c'è spazio in spessore: **LiPo 103040** ~1200 mAh | 1 | 40 x 30 x 10 mm, ~22 g | 3,0-4,2 V | scheda del venditore | — | 6-9 € | F2 |
| 11 | Caricatore **TP4056 con DW01A + FS8205A** (USB-C) | 4 | 26 x 17 mm | 5 V in, 1 A (cambiare la RPROG a 2 kΩ per circa 580 mA) | [datasheet TP4056](https://dlnmh9ip6v2uc.cloudfront.net/datasheets/Prototyping/TP4056.pdf) | — | 1 € l'uno, AliExpress | F1 |
| 12 | LDO 3,3 V **TI TLV75733PDBV** (1 A, dropout ~0,4 V a 1 A) oppure **AP2112K-3.3** (600 mA) | 5 | SOT-23-5, 2,9 x 1,6 mm | 1,45-5,5 V in | [TLV757P](https://www.ti.com/lit/ds/symlink/tlv757p.pdf), [AP2112](https://www.diodes.com/assets/Datasheets/AP2112.pdf) | — | 0,3-0,6 € LCSC/Mouser | F2 |
| 13 | Motorino vibrazione a moneta **10 x 2,7 mm** 3 V (per il banco; nel telefono resta quello originale) | 3 | 10 mm Ø x 2,7 mm, ~1 g | 3 V, 60-80 mA | scheda del venditore | — | 0,5 € | F1 |
| 14 | Driver vibrazione: MOSFET **AO3400A** + diodo **1N5819** + resistenza 1 kΩ (oppure driver aptico **DRV2605L**) | 5 set | SOT-23 | gate a 3,3 V va bene | [AO3400A](https://www.aosmd.com/res/datasheets/AO3400A.pdf), [DRV2605L](https://www.ti.com/lit/ds/symlink/drv2605l.pdf) | — | 0,2 € a set; 7 € DRV2605L Adafruit | F1 |
| 15 | Piezo passivo 12 mm | 2 | 12 x 9 mm | 3-5 V, < 10 mA | scheda del venditore | — | 0,5 € | F1 |
| 16 | Cupole metalliche (snap dome) 5 mm, 4 gambe | 30 | 5 mm Ø | — | scheda del venditore | — | 3 € AliExpress | F2 |
| 17 | Tastiera 4x4 a membrana (banco) e pulsanti tattili 6x6 mm | 1 + 20 | 6 x 6 x 5 mm | — | — | — | 2 € + 2 € | F1 |
| 18 | Passivi: kit di resistenze e condensatori ceramici 0603 e THT, condensatori 10 µF e 100 µF, partitore per la batteria 2 x 100 kΩ | 1 kit | — | — | — | — | 12 € Amazon | F1 |
| 19 | Connettori: JST-PH 2 pin (batteria), header 2,54 mm, connettore FPC 0,5 mm, USB-C femmina 16 pin | 1 set | — | — | — | — | 8 € | F1/F2 |
| 20 | Fili: cavetti Dupont M-M/M-F, filo smaltato 0,1 mm, filo siliconico 26-30 AWG, 2 breadboard da 830 punti | 1 set | — | — | — | — | 15 € | F1 |
| 21 | Nastro Kapton, biadesivo spesso, termorestringente | 1 set | — | — | — | — | 8 € | F2 |
| 22 | PCB prototipo (JLCPCB/PCBWay, 5 pezzi, 2 strati) | 5 | da disegnare | — | — | — | 5-15 € + spedizione | F2 |

### Lo spazio per la batteria

La BLC-2 originale misura circa **53 x 39 x 8 mm** secondo i ricambi ([Subtel/Cellonic](https://www.subtel.de/en/battery-for-nokia-3310-3330-3410-3510-3510i-5510-6650-6800-6810-blc-2-blc-1-bmc-101045.html)); un altro ricambio dichiara 52,8 x 38 x 7,6 mm. Nokia non pubblica una misura ufficiale, quindi il vano reale va misurato col calibro sulla nostra scocca. La LiPo 603450 (50 x 34 x 6 mm) entra con margine ed è quella consigliata. La 103040 è più spessa (10 mm): conviene solo se dietro c'è posto.

## Strumentazione

| Strumento | Modello consigliato | Prezzo indicativo | Dove | Fase |
|---|---|---|---|---|
| Saldatore | **Pinecil V2** (USB-C PD) oppure stazione **Hakko FX-888D** | 30 € / 110 € | [Pine64](https://pine64.com/product/pinecil-smart-mini-portable-soldering-iron/), Amazon | F1 |
| Punte e consumabili | punta fine, stagno 0,5 mm, flussante in pasta, treccia dissaldante, pompetta | 20 € | Amazon | F1 |
| Multimetro | **UNI-T UT61E+** oppure **Aneng AN8008** (economico) | 60 € / 25 € | Amazon/AliExpress | F1 |
| Misuratore di corrente USB | **FNIRSI FNB58** | 30 € | Amazon/AliExpress | F1 |
| Consumi in sleep (µA) | **Nordic Power Profiler Kit II** | 100 € | [Nordic](https://www.nordicsemi.com/Products/Development-hardware/Power-Profiler-Kit-2), Mouser | F2 |
| Analizzatore logico | clone **24 MHz a 8 canali** (sigrok/PulseView) oppure **Saleae Logic 8** | 12 € / 500 € | AliExpress / Saleae | F1 |
| Alimentatore da banco | **Riden RD6006** oppure **Korad KA3005D** | 70 € / 90 € | AliExpress / Amazon | F1 |
| Oscilloscopio (utile per I2S, PWM e per il proiettore) | **FNIRSI DPOX180H** portatile oppure **Rigol DHO804** | 120 € / 400 € | AliExpress / Amazon | F2 |
| Microscopio | microscopio digitale 7" tipo **Andonstar AD207** | 100 € | Amazon | F2 |
| Aria calda | clone 858D economico oppure **Quick 861DW** | 40 € / 250 € | Amazon/AliExpress | F2 |
| Calibro digitale | calibro 150 mm | 15 € | Amazon | F1 |
| Varie | tappetino in silicone, terza mano, pinzette ESD, aspiratore fumi, cacciaviti Torx T6 per il 3310 | 40 € | Amazon | F1 |

## Fase 3: mini proiettore (dettagli in [mini-proiettore.md](mini-proiettore.md))

| # | Componente | Q.tà | Misure | Alimentazione | Datasheet | Prezzo, dove |
|---|---|---|---|---|---|---|
| P1 | **TI DLPDLCR2000EVM** (DLP2000 + DLPC2607 + DLPA1000) | 1 | 54 x 76 mm | 5 V, ~320 mA a luminosità tipica (TI consiglia un alimentatore da 3 A) | [TI](https://www.ti.com/tool/DLPDLCR2000EVM), [DLPC2607](https://www.ti.com/lit/pdf/dlps030) | ~120-130 € [DigiKey](https://www.digikey.com/en/products/detail/texas-instruments/DLPDLCR2000EVM/7598640)/Mouser |
| P2 | Alimentatore 5 V 3 A con jack 2,1 mm | 1 | — | — | — | 10 € |
| P3 | Boost 5 V da LiPo **TPS61023** o modulo **MT3608** | 2 | 20 x 10 mm | 3-4,2 V in → 5 V, 1-2 A | [TPS61023](https://www.ti.com/lit/ds/symlink/tps61023.pdf) | 2-5 € |
| P4 | Proiettore di prova economico: LED bianco 1 W + lente asferica 20-30 mm + LCD trasparente | 1 set | — | 3,3 V | — | 10-15 € AliExpress |

## Totale per fase (indicativo)

| Fase | Componenti | Strumenti | Totale |
|---|---|---|---|
| F1 banco | ~110 € | ~320 € in versione economica (Pinecil, Aneng, FNB58, analizzatore clone, Riden, calibro, varie) | **~430 €** |
| F2 prototipo | ~75 € (moduli WROOM, LiPo, LDO, TCA8418, cupole, PCB) | ~360 € (PPK2, oscilloscopio portatile, microscopio, aria calda economica) | **~435 €** |
| F3 extra | fotocamera ~25 €, proiettore ~150 € | — | **~175 €** |

Chi ha già saldatore e multimetro risparmia circa 90 € in F1. Il minimo indispensabile per partire (DevKit, display, microSD, audio, tasti, fili, saldatore, multimetro) costa circa 150 €.
