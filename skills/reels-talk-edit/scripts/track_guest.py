#!/usr/bin/env python3
"""Track the on-camera GUEST's face (two-shot takes) for the soft face mosaic.

usage: track_guest.py PROXY.mp4 OUT.npz [--side left|right] [--every 2] [--model yunet.onnx]

Picks, per detection frame, the face on the guest's side of the frame (default: centre x < 50 % = left) that is
closest to the previous pick; fills misses (hand over the face, head turned) by linear interpolation for gaps up
to 2 s and by holding the last box beyond that; then smooths with a 0.4 s moving median so the mosaic doesn't
jitter. Output (one row per proxy frame): t (s), box (x, y, w, h) normalised to the frame, found (bool).
"""
import argparse, json, os, subprocess
import numpy as np
import cv2

ap = argparse.ArgumentParser()
ap.add_argument('proxy')
ap.add_argument('out')
ap.add_argument('--side', default='left', choices=['left', 'right'])
ap.add_argument('--every', type=int, default=2)
ap.add_argument('--model', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets', 'yunet.onnx'))
a = ap.parse_args()

pr = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                                'stream=width,height,r_frame_rate', '-of', 'json', a.proxy],
                               capture_output=True, text=True).stdout)['streams'][0]
W, H = pr['width'], pr['height']
num, den = map(int, pr['r_frame_rate'].split('/'))
fps = num / den
det = cv2.FaceDetectorYN.create(a.model, '', (W, H), 0.55, 0.3, 5000)
cap = cv2.VideoCapture(a.proxy)
boxes, found, i, prev = [], [], 0, None
while True:
    ok, fr = cap.read()
    if not ok:
        break
    b = None
    if i % a.every == 0:
        _, f = det.detect(fr)
        cands = []
        for r in (f if f is not None else []):
            x, y, w, h = [float(v) for v in r[:4]]
            cx = (x + w / 2) / W
            if (cx < 0.5) == (a.side == 'left'):
                cands.append((x / W, y / H, w / W, h / H))
        if cands:
            if prev is None:
                b = max(cands, key=lambda c: c[2] * c[3])
            else:
                b = min(cands, key=lambda c: abs(c[0] + c[2] / 2 - prev[0] - prev[2] / 2) + abs(c[1] + c[3] / 2 - prev[1] - prev[3] / 2))
            prev = b
    boxes.append(b)
    found.append(b is not None)
    i += 1
n = len(boxes)
t = np.arange(n) / fps
B = np.full((n, 4), np.nan)
for k, b in enumerate(boxes):
    if b is not None:
        B[k] = b
idx = np.where(~np.isnan(B[:, 0]))[0]
if len(idx) == 0:
    raise SystemExit('no guest face found on the ' + a.side + ' side')
MAX_GAP = int(2.0 * fps)  # interpolate gaps up to 2 s, hold the last box beyond that
for c in range(4):
    col = B[:, c]
    filled = np.interp(np.arange(n), idx, col[idx])
    # hold instead of interpolating across long gaps
    for s, e in zip(idx[:-1], idx[1:]):
        if e - s > MAX_GAP:
            filled[s:e] = col[s]
    B[:, c] = filled
k = max(1, int(0.4 * fps)) | 1  # odd window
pad = k // 2
Bp = np.pad(B, ((pad, pad), (0, 0)), mode='edge')
B = np.stack([np.median(Bp[j:j + k], axis=0) for j in range(n)])
np.savez(a.out, t=t, box=B.astype(np.float32), found=np.array(found), fps=fps)
print(f'guest face: {len(idx)} detections / {n} frames ({len(idx) * a.every / max(1, n):.0%} of detection frames), '
      f'median box {np.median(B, axis=0).round(3).tolist()} -> {a.out}')
