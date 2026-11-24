"""Extracts the real-footage clips used by monta.py as 1080x1920 JPG frames, already sped up.

  ../.venv/Scripts/python clips.py [name ...]
"""
import os
import subprocess
import sys

import imageio_ffmpeg

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, 'out', 'clip')
FPS = 30

# name: (file in girato/, source start s, source end s, output duration s)
CLIPS = {
    'pcb_hook': ('smontaggio.mp4', 135.6, 138.4, 0.80),
    'front_hook': ('smontaggio.mp4', 16.5, 19.5, 0.75),
    'cover': ('smontaggio.mp4', 1.2, 4.2, 0.95),
    'tavolo': ('smontaggio.mp4', 141.0, 146.6, 1.60),
    'batteria': ('smontaggio.mp4', 9.6, 12.6, 1.00),
    'viti': ('smontaggio.mp4', 30.0, 126.0, 1.30),
    'scheda': ('smontaggio.mp4', 134.0, 142.0, 2.80),
    'scanner': ('scansione.mp4', 1.5, 6.5, 1.45),
    'coperchio': ('scansione.mp4', 8.6, 11.6, 1.20),
}


def extract(name):
    src, a, b, dur = CLIPS[name]
    speed = (b - a) / dur
    dst = os.path.join(OUT, name)
    os.makedirs(dst, exist_ok=True)
    for f in os.listdir(dst):
        os.remove(os.path.join(dst, f))
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run([ff, '-v', 'error', '-y', '-ss', str(a), '-t', str(b - a), '-i', os.path.join(HERE, 'girato', src),
                    '-vf', 'setpts=PTS/%f,fps=%d,scale=1080:1920:flags=lanczos' % (speed, FPS),
                    '-q:v', '2', '-frames:v', str(int(round(dur * FPS))), os.path.join(dst, '%04d.jpg')], check=True)
    print(name, len(os.listdir(dst)), 'frames, x%.1f' % speed)


if __name__ == '__main__':
    for n in sys.argv[1:] or CLIPS:
        extract(n)
