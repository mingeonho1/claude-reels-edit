#!/usr/bin/env python3
"""Fuse STT + diarization + on-camera mouth motion into one word table (speaker per word).

usage: build_words.py --stt stt.json --diar diar.json --face face.npz --out words.json [--transcript words.txt]

speaker fusion (per word, robust to short 맞장구):
  diar vote  d in [-1,1]  : (host windows - guest windows)/n over [start-0.15, end+0.15]
                            (cluster->role: the cluster whose words show more mouth motion = host/on-camera)
  mouth z    m            : robust z of lower-face motion (minus head motion) over the word, vs whole-take median/MAD
  logit = 1.6*d + 0.9*clip(m,-3,3) ; short words (<0.45 s, e.g. 그치/응/엉) weight mouth 1.5x
  host if logit > 0. Words are then smoothed: a run of <=2 words whose label disagrees with both neighbours
  AND whose |logit| < 1.0 is flipped (removes isolated flips inside a sentence).
Also cross-checks whisper words against zipformer: 'zip' field = zipformer syllables inside the word span;
'flag' marks words to eyeball (matched<0.34 or long unmatched span) when Claude cleans captions.
"""
import argparse, json
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument('--stt', required=True)
ap.add_argument('--diar', required=True)
ap.add_argument('--face', required=True)
ap.add_argument('--out', required=True)
ap.add_argument('--transcript')
ap.add_argument('--patch', help='words_patch.json: {"add":[{w,start,end,spk?}], "set_spk":[[t0,t1,"host|guest"]]} from retranscribe.py')
a = ap.parse_args()
S = json.load(open(a.stt))
D = json.load(open(a.diar))
F = np.load(a.face)
score = F['score']
fps = float(F['fps'])

words = []
for seg in S['segments']:
    toks = seg.get('tokens', [])
    for w in seg['words']:
        st, en = w['start'], max(w['end'], w['start'] + 0.05)
        z = ''.join(t['t'].replace('▁', '') for t in toks if st - 0.05 <= t['ts'] < en - 0.02)
        words.append(dict(w=w['w'], start=st, end=en, matched=w['matched'], vad=seg['i'], zip=z))
PATCH = json.load(open(a.patch)) if a.patch else {}
for nw in PATCH.get('add', []):
    # words the whisper pass dropped (found with retranscribe.py); replace any old word overlapping them
    words = [w for w in words if not (w['start'] < nw['end'] - 0.02 and w['end'] > nw['start'] + 0.02)]
    words.append(dict(w=nw['w'], start=nw['start'], end=nw['end'], matched=1.0, vad=-1, zip=nw['w'], forced=nw.get('spk')))
words.sort(key=lambda x: x['start'])
for i, w in enumerate(words):
    w['i'] = i

win_t = np.array([x['t'] for x in D['windows']])
win_l = np.array([x['spk'] for x in D['windows']])


def mouth(s, e):
    i0, i1 = int(s * fps), max(int(s * fps) + 1, int(e * fps))
    v = score[i0:i1]
    return float(np.nanmean(v)) if len(v) else np.nan


ms = np.array([mouth(w['start'], w['end']) for w in words])
med = np.nanmedian(ms)
mad = np.nanmedian(np.abs(ms - med)) * 1.4826 + 1e-6
# cluster -> role
cl_m = {}
for k in (0, 1):
    v = []
    for w, m in zip(words, ms):
        sel = (win_t >= w['start'] - 0.15) & (win_t <= w['end'] + 0.15)
        if sel.any() and np.bincount(win_l[sel], minlength=2).argmax() == k:
            v.append(m)
    cl_m[k] = float(np.nanmedian(v)) if v else -1
host_cl = max(cl_m, key=cl_m.get)
logits = []
for w, m in zip(words, ms):
    sel = (win_t >= w['start'] - 0.15) & (win_t <= w['end'] + 0.15)
    if sel.any():
        d = float(((win_l[sel] == host_cl).sum() - (win_l[sel] != host_cl).sum()) / sel.sum())
    else:
        d = 0.0
    mz = 0.0 if np.isnan(m) else float(np.clip((m - med) / mad, -3, 3))
    wm = 1.5 if (w['end'] - w['start']) < 0.45 else 1.0
    lg = 1.6 * d + 0.9 * wm * mz
    w.update(diar=round(d, 2), mouth_z=round(mz, 2), logit=round(lg, 2))
    logits.append(lg)
lab = np.array([1 if l > 0 else 0 for l in logits])
# isolated-flip smoothing
for i in range(len(words)):
    for run in (1, 2):
        j = i + run
        if i == 0 or j >= len(words):
            continue
        if lab[i - 1] == lab[j] and all(lab[k] != lab[i - 1] for k in range(i, j)) and \
                all(abs(logits[k]) < 1.0 for k in range(i, j)) and \
                words[j]['start'] - words[i - 1]['end'] < 1.0:
            for k in range(i, j):
                lab[k] = lab[i - 1]
for w, l in zip(words, lab):
    w['spk'] = 'host' if l else 'guest'
    if w.get('forced'):
        w['spk'] = w['forced']
    for t0, t1, sp in PATCH.get('set_spk', []):
        if t0 <= (w['start'] + w['end']) / 2 <= t1:
            w['spk'] = sp
    w['flag'] = bool(w['matched'] < 0.34 or (w['end'] - w['start']) > 1.2)
json.dump(dict(source=S.get('source'), host_cluster=int(host_cl), cluster_mouth=cl_m, words=words),
          open(a.out, 'w'), ensure_ascii=False, indent=0)
if a.transcript:
    with open(a.transcript, 'w') as f:
        f.write('# i  start-end  spk(logit)  word  [zip]  !=flag\n')
        prev = None
        for w in words:
            if prev is not None and w['start'] - prev['end'] > 0.35:
                f.write(f'      ---- pause {w["start"] - prev["end"]:.2f}s\n')
            f.write(f"{w['i']:4d} {w['start']:7.2f}-{w['end']:7.2f} {w['spk'][0].upper()}({w['logit']:+.1f}) "
                    f"{w['w']}  [{w['zip']}]{'  !' if w['flag'] else ''}\n")
            prev = w
print('words', len(words), 'host cluster', host_cl, cl_m, 'host words', int(lab.sum()))
