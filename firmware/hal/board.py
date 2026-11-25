# Bench wiring: ESP32-S3-DevKitC-1 + Nokia 5110 breakout + 4x4 button matrix.
# Will change when the real AurI-3310 board exists.
LCD_SCLK = 12
LCD_SDIN = 11
LCD_DC = 9
LCD_SCE = 10
LCD_RES = 8
LCD_VOP = 0x38

BACKLIGHT = 7
VIBRA = 6

KEY_ROWS = (15, 16, 17, 18)
KEY_COLS = (4, 5, 13, 14)
KEYMAP = (
    ('1', '2', '3', 'up'),
    ('4', '5', '6', 'down'),
    ('7', '8', '9', 'c'),
    ('*', '0', '#', 'navi'),
)

I2C_SDA = 1
I2C_SCL = 2

# Bench placeholders until the H0 prototype: to be checked on the real wiring.
POWER_KEY = 0        # BOOT button of the DevKitC, active low; also the deep-sleep wake pin
BAT_ADC = 3          # battery through a 1:2 divider
BAT_DIVIDER = 2.0
BAT_EMPTY_MV = 3300
BAT_FULL_MV = 4150
CHG_DET = 21         # charger status (e.g. TP4056 CHRG), low while charging
SPEAKER = 47         # piezo for tones on the bench; the MAX98357A (I2S) comes later

# microSD (SPI): ci stanno il cervello locale e, volendo, tutto AurI OS.
# Pin di banco, da confermare sul prototipo H0.
SD_SCK = 36
SD_MOSI = 35
SD_MISO = 37
SD_CS = 34
SD_DIR = '/sd/auri/cervello'     # dove stanno modello.bin e tokenizer.bin

TZ_OFFSET = 3600
