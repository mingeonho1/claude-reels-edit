#!/usr/bin/env python3
"""Face track + on-camera mouth-motion signal from a 720p (or any) proxy.

usage: face_track.py PROXY.mp4 OUT.npz [--model yunet.onnx] [--w 360] [--det-every 3]

Outputs (npz, one row per proxy frame @ native fps):
  t        frame time (s)
  box      face box (x,y,w,h) normalised to frame W/H (interpolated between detections; nan if never found)
  lmk      5 landmarks (re, le, nose, rm, lm) normalised (10 values)
  mouth    mean |frame diff| inside lower-face ROI (mouth corners -> chin), head-motion compensated
  ref      mean |frame diff| inside upper-face ROI (eyes/forehead) = head-motion reference
  score    mouth - 0.8*ref, clipped >=0  (talking evidence)
Also writes OUT.json with per-second face summary (median box) used for retouch/zoom/card layout.
Requires cv2 >= 4.5.4 (FaceDetectorYN). Model: opencv_zoo face_detection_yunet_2023mar.onnx
 (download: https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx)
"""
import argparse, json, subprocess, os
import numpy as np
import cv2

ap = argparse.ArgumentParser()
ap.add_argument('proxy')
ap.add_argument('out')
ap.add_argument('--model', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets', 'yunet.onnx'))
ap.add_argument('--w', type=int, default=360)
ap.add_argument('--det-every', type=int, default=3)
a = ap.parse_args()

pr = json.loads(subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'v:0', '-show_entries',
                                'stream=width,height,r_frame_rate', '-of', 'json', a.proxy],
                               capture_output=True, text=True).stdout)['streams'][0]
W0, H0 = pr['width'], pr['height']
num, den = map(int, pr['r_frame_rate'].split('/'))
fps = num / den
W = a.w
H = int(round(H0 * W / W0 / 2) * 2)
det = cv2.FaceDetectorYN.create(a.model, '', (W, H), 0.6, 0.3, 50)
p = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', a.proxy, '-vf', f'scale={W}:{H}', '-f', 'rawvideo',
                      '-pix_fmt', 'bgr24', '-'], stdout=subprocess.PIPE)
fs = W * H * 3
boxes, lmks, frames_ok = [], [], []
mouth, ref = [], []
prev = None
last = None  # last detection (box, lmk) in pixels
n = 0
while True:
    buf = p.stdout.read(fs)
    if len(buf) < fs:
        break
    img = np.frombuffer(buf, np.uint8).reshape(H, W, 3)
    g = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).astype(np.float32)
    if n % a.det_every == 0:
        _, faces = det.detect(img)
        if faces is not None and len(faces):
            f = max(faces, key=lambda r: r[2] * r[3])
            last = (f[:4].copy(), f[4:14].copy())
            boxes.append((n, f[:4] / [W, H, W, H]))
            lmks.append((n, f[4:14] / np.tile([W, H], 5)))
    m = r = np.nan
    if last is not None and prev is not None:
        (x, y, w, h), L = last
        mx0, mx1 = min(L[6], L[8]), max(L[6], L[8])
        mw = max(4, mx1 - mx0)
        cy = (L[7] + L[9]) / 2
        # lower face ROI: around mouth, from just below nose to chin
        X0, X1 = int(max(0, mx0 - 0.35 * mw)), int(min(W, mx1 + 0.35 * mw))
        Y0, Y1 = int(max(0, (L[5] + cy) / 2)), int(min(H, y + h * 1.02))
        # upper ROI: eye band
        ey = (L[1] + L[3]) / 2
        U0, U1 = int(max(0, ey - 0.18 * h)), int(min(H, ey + 0.10 * h))
        UX0, UX1 = int(max(0, x + 0.1 * w)), int(min(W, x + 0.9 * w))
        if X1 - X0 > 3 and Y1 - Y0 > 3:
            m = float(np.abs(g[Y0:Y1, X0:X1] - prev[Y0:Y1, X0:X1]).mean())
        if UX1 - UX0 > 3 and U1 - U0 > 3:
            r = float(np.abs(g[U0:U1, UX0:UX1] - prev[U0:U1, UX0:UX1]).mean())
    mouth.append(m)
    ref.append(r)
    prev = g
    n += 1
p.wait()
N = n
t = np.arange(N) / fps


def interp(rows, dim):
    out = np.full((N, dim), np.nan, np.float32)
    if not rows:
        return out
    idx = np.array([i for i, _ in rows])
    val = np.array([v for _, v in rows])
    for k in range(dim):
        out[:, k] = np.interp(np.arange(N), idx, val[:, k])
    return out


box = interp(boxes, 4)
lmk = interp(lmks, 10)
mouth = np.array(mouth, np.float32)
ref = np.array(ref, np.float32)
score = np.clip(np.nan_to_num(mouth) - 0.8 * np.nan_to_num(ref), 0, None)
np.savez_compressed(a.out, t=t, box=box, lmk=lmk, mouth=mouth, ref=ref, score=score, fps=fps)
# per-second summary
summ = []
for s in range(int(np.ceil(N / fps))):
    sl = slice(int(s * fps), min(N, int((s + 1) * fps)))
    b = np.nanmedian(box[sl], 0) if N else [np.nan] * 4
    summ.append([round(float(v), 4) for v in b])
json.dump(dict(fps=fps, frames=N, src_wh=[W0, H0], detections=len(boxes), face_per_sec=summ), open(a.out.replace('.npz', '.json'), 'w'))
print('frames', N, 'detections', len(boxes), 'fps', fps)
