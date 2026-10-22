#!/usr/bin/env python3
"""4x4 contact sheet of evenly spaced frames (QA + judge view).
usage: contact_sheet.py VIDEO OUT.jpg [--cols 4 --rows 4 --w 270]
"""
import argparse, json, os, subprocess
import numpy as np

FFMPEG = os.environ.get('FFMPEG', 'ffmpeg')    # e.g. FFMPEG=~/bin/ffmpeg44 to force a specific build
FFPROBE = os.environ.get('FFPROBE', 'ffprobe')
from PIL import Image, ImageDraw

ap = argparse.ArgumentParser()
ap.add_argument('video'); ap.add_argument('out')
ap.add_argument('--cols', type=int, default=4); ap.add_argument('--rows', type=int, default=4); ap.add_argument('--w', type=int, default=270)
a = ap.parse_args()
d = float(json.loads(subprocess.run([FFPROBE, '-v', 'error', '-show_entries', 'format=duration', '-of', 'json', a.video],
                                    capture_output=True, text=True).stdout)['format']['duration'])
n = a.cols * a.rows
w, h = a.w, int(a.w * 16 / 9)
sheet = Image.new('RGB', (w * a.cols, h * a.rows), (0, 0, 0))
for k in range(n):
    t = d * (k + 0.5) / n
    raw = subprocess.run([FFMPEG, '-v', 'error', '-ss', f'{t:.3f}', '-i', a.video, '-frames:v', '1', '-vf', f'scale={w}:{h}',
                          '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True).stdout
    if len(raw) == w * h * 3:
        im = Image.fromarray(np.frombuffer(raw, np.uint8).reshape(h, w, 3))
        ImageDraw.Draw(im).text((6, h - 18), f'{t:5.1f}s', fill=(255, 255, 0))
        sheet.paste(im, ((k % a.cols) * w, (k // a.cols) * h))
sheet.save(a.out, quality=90)
print('wrote', a.out)
