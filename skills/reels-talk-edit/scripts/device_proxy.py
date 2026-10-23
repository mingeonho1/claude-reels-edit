#!/usr/bin/env python3
"""[DEVICE] Make the 720x1280 analysis/preview proxy + 48 kHz wav from a raw iPhone MOV, in resumable chunks
(device_bash calls die after 180 s; keep each call <= --budget 140 s). python3.10 + ffmpeg 4.4, no numpy needed.

usage (repeat until it prints PROXY_DONE):
  python3 device_proxy.py ~/mnt/capcut/me/10_x/소스/IMG_1234.MOV ~/mnt/capcut/me/10_x/_reels_work/prx --budget 140
outputs: OUT/src_720.mp4 (H.264 8-bit, colour tags of the source kept -> HLG stays HLG), OUT/src.wav (48k mono pcm)
4K HEVC decode runs ~1.2x realtime on 4 threads -> chunk = 100 s of source by default.
"""
import argparse, json, os, subprocess, time


FFMPEG = os.environ.get('FFMPEG', 'ffmpeg')    # e.g. FFMPEG=~/bin/ffmpeg44 to force a specific build
FFPROBE = os.environ.get('FFPROBE', 'ffprobe')
ap = argparse.ArgumentParser()
ap.add_argument('mov'); ap.add_argument('out')
ap.add_argument('--budget', type=float, default=140); ap.add_argument('--chunk', type=float, default=100)
a = ap.parse_args()
a.out = os.path.abspath(a.out)  # concat lists resolve relative paths against the list's own folder
os.makedirs(a.out, exist_ok=True)
st_path = os.path.join(a.out, 'proxy_state.json')
dur = float(json.loads(subprocess.run([FFPROBE, '-v', 'error', '-show_entries', 'format=duration', '-of', 'json', a.mov],
                                      capture_output=True, text=True).stdout)['format']['duration'])
st = json.load(open(st_path)) if os.path.exists(st_path) else dict(done=[], wav=False, rate=1.0)
t0 = time.time()
wav = os.path.join(a.out, 'src.wav')
if not st['wav']:
    subprocess.run([FFMPEG, '-v', 'error', '-y', '-i', a.mov, '-vn', '-ac', '1', '-ar', '48000', '-c:a', 'pcm_s16le', wav], check=True)
    st['wav'] = True
    json.dump(st, open(st_path, 'w'))
n = int((dur + a.chunk - 1e-3) // a.chunk) + 1
chunks = [(k * a.chunk, min(dur, (k + 1) * a.chunk)) for k in range(n) if k * a.chunk < dur - 0.05]
for k, (c0, c1) in enumerate(chunks):
    if k in st['done']:
        continue
    est = (c1 - c0) / st['rate']
    if time.time() - t0 + est > a.budget and time.time() - t0 > 1:
        break
    s = time.time()
    subprocess.run([FFMPEG, '-v', 'error', '-y', '-threads', '4', '-ss', f'{c0:.3f}', '-t', f'{c1 - c0:.3f}', '-i', a.mov,
                    # portrait -> 720x1280, landscape (two-shot, ep11) -> 1280x720; never stretch
                    '-vf', "scale='if(gt(iw,ih),1280,720)':'if(gt(iw,ih),720,1280)':flags=bicubic", '-r', '30', '-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18',
                    '-pix_fmt', 'yuv420p', '-an', os.path.join(a.out, f'part{k:02d}.mp4')], check=True)
    st['rate'] = (c1 - c0) / (time.time() - s)
    st['done'].append(k)
    json.dump(st, open(st_path, 'w'))
    print(f'chunk {k + 1}/{len(chunks)} {c1 - c0:.0f}s source in {time.time() - s:.0f}s', flush=True)
if len(st['done']) == len(chunks):
    lst = os.path.join(a.out, 'parts.txt')
    open(lst, 'w').write(''.join(f"file '{os.path.join(a.out, f'part{k:02d}.mp4')}'\n" for k in range(len(chunks))))
    subprocess.run([FFMPEG, '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst, '-i', wav, '-map', '0:v', '-map', '1:a',
                    '-c:v', 'copy', '-c:a', 'aac', '-b:a', '128k', os.path.join(a.out, 'src_720.mp4')], check=True)
    print('PROXY_DONE', os.path.join(a.out, 'src_720.mp4'), wav)
else:
    print(f'PENDING {len(chunks) - len(st["done"])} chunks; call again')
