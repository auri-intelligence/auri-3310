# Mini proiettore per AurI

La domanda è se AurI può proiettare il suo schermo (84x48) sul muro con un pezzo che poi entri davvero nella cover del 3310, che è grande circa 113 x 48 x 22 mm.

## Cosa conta davvero

- Lo schermo di AurI ha **84x48 pixel**, quindi non serve alta risoluzione: serve un'immagine nitida e abbastanza luminosa a 30-50 cm dal muro.
- L'ESP32-S3 ha la periferica **LCD_CAM**, che sa pilotare un'uscita **RGB parallela** (fino a 16 bit, con il framebuffer in PSRAM) e una **i80** a 8/16 bit ([ESP-IDF, LCD](https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-reference/peripherals/lcd/index.html)). Non ha **né MIPI-DSI né HDMI**.
- Come pin, la parallela RGB565 occupa 16 dati più PCLK, HSYNC, VSYNC e DE, cioè **20 GPIO**. Con 29 già usati su circa 30 disponibili (vedi [lista-spesa.md](lista-spesa.md)) servono per forza un'espansione I2C per i tasti e la rinuncia alla fotocamera DVP. Si può scendere a **8 bit** (RGB332 o RGB565 in due cicli) se il controller lo accetta.

## Le opzioni

| Tecnologia | Esempio | Misure | Consumo | Luminosità | Ingresso video | L'ESP32-S3 la pilota? | Prezzo / disponibilità | Entra nel 3310? |
|---|---|---|---|---|---|---|---|---|
| Pico DLP | **TI DLPDLCR2000EVM**: DMD DLP2000 0,2" nHD 640x360, controller DLPC2607, driver LED DLPA1000 | scheda 54 x 76 mm ([TI](https://www.ti.com/tool/DLPDLCR2000EVM)); motore ottico più piccolo (da verificare) | 5 V, ~320 mA a luminosità tipica, alimentatore consigliato 5 V 3 A ([TI E2E](https://e2e.ti.com/support/dlp-products-group/dlp/f/dlp-products-forum/847558/dlpdlcr2000evm-power-consumption-and-weight)) | fino a 30 lumen | RGB parallelo 8/16/24 bit + I2C; formati RGB565/666/888, da QVGA a WVGA, PCLK fino a 33,5 MHz ([datasheet DLPC2607](https://www.ti.com/lit/pdf/dlps030)) | **Sì, in teoria**: RGB565 a 16 bit con PCLK di 10-15 MHz. Il DLPC2607 vuole VSYNC sempre attivo, altrimenti spegne i LED, quindi l'uscita va fatta girare di continuo | ~119-129 $ ([DigiKey](https://www.digikey.com/en/products/detail/texas-instruments/DLPDLCR2000EVM/7598640), Mouser), disponibile | La scheda EVM no (54 mm contro 48 di larghezza). Solo il motore ottico con un PCB nostro, forse |
| Pico DLP più nuovo | **DLP230NP** 0,23" + DLPC3432 | motore ottico ~30 x 20 x 10 mm (da verificare) | 1-2 W | 30-100 lumen | ingresso parallelo 24 bit o sub-LVDS / DSI a seconda del controller ([TI DLP Pico](https://www.ti.com/dlp-chip/display-and-projection/overview.html)) | Possibile con la variante parallela, ma i moduli si comprano solo da produttori di motori ottici, in quantità | motori ottici di terzi (Young Optics, Anhua) da 60-150 € su richiesta | Il più compatto, ma per un singolo pezzo è difficile da reperire |
| Laser MEMS (LBS) | MicroVision PicoP, moduli "laser projector" cinesi | ~6-7 mm di spessore, ~40 x 30 mm (da verificare) | 1-2 W | 15-30 lumen, sempre a fuoco | di solito HDMI o MIPI tramite una scheda di conversione | **No** in pratica: servirebbe una scheda di conversione con il suo processore | MicroVision non vende più ai privati; moduli usati su AliExpress a 80-200 €, documentazione scarsa | Il motore sì, la scheda video no |
| LCOS | moduli Himax/Omnivision da smart glasses o pico projector | piccoli (~20 x 15 mm il pannello) | 0,5-1,5 W con il LED | 10-50 lumen | MIPI, LVDS o RGB a seconda del driver | Solo con i driver RGB, che sono rari e senza documentazione pubblica | pezzi da ricambio; disponibilità incerta | Possibile ma è un progetto di ricerca |
| Gadget smontato | pico projector economici (YG300 e simili), "projector phone" cinesi | motore ottico 40-60 mm | 3-5 W | 5-20 lumen reali | HDMI, AV o USB (hanno il loro processore) | **No** direttamente; si potrebbe solo mandare un segnale analogico AV | 30-60 € | Troppo grandi e consumano troppo |
| Proiettore ottico fai da te | LED bianco 1 W + piccolo LCD trasmissivo (LCD monocromatico trasparente o il PCD8544 senza retro) + lente asferica | ~30 x 30 x 40 mm | 0,3-1 W (solo il LED) | pochi lumen: si vede al buio a 20-40 cm | **Nessuna**: l'LCD si pilota come quello attuale via SPI | **Sì, subito** | 10-15 € | Sì, se la lente sta nella parte alta della cover |

## Autonomia con la batteria

Con una LiPo da 1000 mAh (3,7 Wh) e un boost 5 V con rendimento ~85%:

- DLP2000 a luminosità tipica: 5 V x 0,32 A ≈ 1,6 W, più l'ESP32 (~0,4 W) ≈ 2 W → circa **1 ora e mezza** di proiezione.
- DLP alla massima luminosità (oltre 1 A a 5 V): sotto i 40 minuti, e il boost deve reggere 1,5-2 A.
- LED da 1 W: circa **3 ore**.

## Raccomandazione

1. **Da provare subito sul banco (economico, ~15 €):** il proiettore ottico a LED. Si toglie la retroilluminazione a un PCD8544 di scorta (il vetro è trasmissivo se si stacca il riflettore), lo si illumina da dietro con un LED bianco da 1 W e si mette davanti una lente asferica da 20-30 mm. Il firmware resta identico, cambia solo un MOSFET che accende il LED (un GPIO, o lo stesso di BACKLIGHT). Si vedono 84x48 pixel grossi sul muro al buio. È il modo più rapido per capire se l'idea piace.
2. **Soluzione migliore "vera":** il chipset **DLP2000 + DLPC2607** tramite l'EVM TI sul banco, pilotato dalla periferica RGB dell'ESP32-S3 a 640x360 RGB565 (AurI scalato 7x = 588x336, centrato; framebuffer da 460 KB in PSRAM). Nel telefono va poi messo solo il motore ottico su un PCB nostro, perché la scheda EVM da 54 x 76 mm non entra. L'integrazione è possibile ma è il lavoro più grosso del progetto, e prima va controllata la misura del motore ottico.
3. **Da scartare:** laser MEMS, LCOS e gadget smontati, perché vogliono HDMI o MIPI, che l'ESP32-S3 non ha, oppure perché non si trovano.

## Cosa cambia su pin e alimentazione

- **LED fai da te:** +1 GPIO (PWM verso un MOSFET AO3400A) e circa 300 mA dalla batteria, presi prima dell'LDO.
- **DLP2000:** +20 GPIO per RGB565 (oppure 12 in modalità a 8 bit, se il DLPC2607 si configura così), PROJ_ON più l'I2C condiviso. Bisogna: spostare la tastiera sul **TCA8418** (−8 GPIO), rinunciare alla fotocamera DVP, togliere il piezo. Per l'alimentazione serve un **boost 5 V da almeno 2 A** (TPS61023 o simile) con un interruttore di carico, perché a riposo il proiettore deve restare spento del tutto. Il TP4056 a 580 mA non basta per caricare e proiettare insieme: servirebbe un caricatore con power path (es. BQ24074).

Le voci da comprare sono in [lista-spesa.md](lista-spesa.md), Fase 3.

## Fonti

- [TI DLPDLCR2000EVM](https://www.ti.com/tool/DLPDLCR2000EVM)
- [Datasheet DLPC2607](https://www.ti.com/lit/pdf/dlps030)
- [TI E2E, consumo del DLPDLCR2000EVM](https://e2e.ti.com/support/dlp-products-group/dlp/f/dlp-products-forum/847558/dlpdlcr2000evm-power-consumption-and-weight)
- [DigiKey DLPDLCR2000EVM](https://www.digikey.com/en/products/detail/texas-instruments/DLPDLCR2000EVM/7598640)
- [Progetto di riferimento TI TIDA-01473](https://ti.com/tool/tida-01473)
- [ESP-IDF, periferica LCD dell'ESP32-S3](https://docs.espressif.com/projects/esp-idf/en/latest/esp32s3/api-reference/peripherals/lcd/index.html)
- [Panoramica TI DLP Pico](https://www.ti.com/dlp-chip/display-and-projection/overview.html)
