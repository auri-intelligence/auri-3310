# Bench wiring: ESP32-S3-DevKitC-1 + Nokia 5110 breakout + 4x4 button matrix.
# Will change when the real Auri-3310 board exists.
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

TZ_OFFSET = 3600
