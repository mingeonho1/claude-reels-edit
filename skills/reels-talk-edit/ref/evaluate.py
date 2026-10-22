#!/usr/bin/env python3
"""Score a candidate edit against Geonho's own edit of episode 9 (ground truth) + generic checks.

usage: evaluate.py --edl EDL.json --video OUT.mp4 [--gt gt9.json] [--out score.json]

EDL contract (all times seconds):
{
  "segments": [{"src_start":..,"src_end":..,"speed":1.2}, ...],      # output order
  "captions": [{"text":"..","speaker":"host"|"guest","out_start":..,"out_end":..}, ...],
  "character": [{"out_start":..,"out_end":..}, ...],                   # guest avatar on-screen intervals
  ... any other keys are ignored by the scorer
}
host  = on-camera person (Geonho, black text)   guest = off-camera friend 정우 (navy text + character gif)
"""
import json, argparse, subprocess, re, os, sys
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument('--edl', required=True)
ap.add_argument('--video', required=True)
ap.add_argument('--gt', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'gt9.json'))
ap.add_argument('--out')
a = ap.parse_args()
E = json.load(open(a.edl))
G = json.load(open(a.gt))
R = {}
DT = 0.01


def o2s_factory(segs):
    acc = []
    t = 0
    for g in segs:
        d = (g['src_end'] - g['src_start']) / g.get('speed', 1)
        acc.append((t, t + d, g))
        t += d
    def f(x):
        for a0, a1, g in acc:
            if a0 - 1e-6 <= x <= a1 + 1e-6:
                return g['src_start'] + (x - a0) * g.get('speed', 1)
        return None
    return f, t


def mask(intervals, dur):
    m = np.zeros(int(dur / DT) + 2, bool)
    for s, e in intervals:
        m[max(0, int(s / DT)):max(0, int(e / DT))] = True
    return m


SD = G['source_duration']
cand_segs = E['segments']
o2s, out_dur = o2s_factory(cand_segs)
gt_o2s, gt_dur = o2s_factory(G['segments'])

# 1. cut agreement (source timeline F1)  -- 25
cm = mask([(g['src_start'], g['src_end']) for g in cand_segs], SD)
gm = mask([(g['src_start'], g['src_end']) for g in G['segments']], SD)
inter = (cm & gm).sum()
P = inter / max(1, cm.sum())
Rc = inter / max(1, gm.sum())
F1 = 2 * P * Rc / max(1e-9, P + Rc)
R['cut_precision'] = round(float(P), 3)
R['cut_recall'] = round(float(Rc), 3)
R['cut_f1'] = round(float(F1), 3)
R['kept_src_s'] = round(float(cm.sum() * DT), 1)
R['gt_kept_src_s'] = round(float(gm.sum() * DT), 1)
# cut boundaries: penalise cuts landing inside GT-kept speech (mid-word risk): fraction of cand cut points inside gt-kept but >0.15s from gt boundary
gt_b = np.array([x for g in G['segments'] for x in (g['src_start'], g['src_end'])])
bad = 0
pts = [x for g in cand_segs for x in (g['src_start'], g['src_end'])]
for x in pts:
    if gm[min(len(gm) - 1, int(x / DT))] and np.min(np.abs(gt_b - x)) > 0.15:
        bad += 1
R['cut_points'] = len(pts)
R['cut_points_inside_gt_speech'] = bad
s_cut = 25 * F1 * (1 - 0.5 * bad / max(1, len(pts)))

# 2. pacing -- 10   (user wants 1.2-1.4x, output not longer than GT)
sp = np.array([g.get('speed', 1) for g in cand_segs])
w = np.array([g['src_end'] - g['src_start'] for g in cand_segs])
avg_sp = float((sp * w).sum() / max(1e-9, w.sum()))
R['avg_speed'] = round(avg_sp, 3)
R['out_duration'] = round(out_dur, 2)
R['gt_out_duration'] = round(gt_dur, 2)
sp_ok = 1.0 if 1.18 <= avg_sp <= 1.42 else max(0, 1 - min(abs(avg_sp - 1.2), abs(avg_sp - 1.4)) / 0.2)
dur_ok = 1.0 if out_dur <= gt_dur * 1.05 else max(0, 1 - (out_dur / gt_dur - 1.05) / 0.4)
shot = [d / s for d, s in zip(w, sp)]
R['median_shot_s'] = round(float(np.median(shot)), 2) if shot else 0
s_pace = 5 * sp_ok + 5 * dur_ok


def norm(t):
    return re.sub(r'[^\uac00-\ud7a3A-Za-z0-9%]', '', t)


def lev(x, y):
    if len(x) < len(y):
        x, y = y, x
    prev = list(range(len(y) + 1))
    for i, cx in enumerate(x, 1):
        cur = [i]
        for j, cy in enumerate(y, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (cx != cy)))
        prev = cur
    return prev[-1]


caps = E.get('captions', [])
for c in caps:
    m = (c['out_start'] + c['out_end']) / 2
    c['_src'] = o2s(m)
# 3. caption text accuracy -- 20 : CER of candidate vs GT over the source-time region both kept
gcaps = G['captions']
lo, hi = 0, SD
def caps_text_in(cs, key='_src'):
    return ''.join(norm(c['text']) for c in sorted(cs, key=lambda c: c[key] if c[key] is not None else 1e9) if c[key] is not None and gm[min(len(gm)-1, int(c[key] / DT))] and cm[min(len(cm)-1, int(c[key] / DT))])
for c in gcaps:
    c['_src'] = gt_o2s((c['out_start'] + c['out_end']) / 2)
ct = caps_text_in(caps)
gt_t = caps_text_in(gcaps)
cer = lev(ct, gt_t) / max(1, len(gt_t))
R['caption_cer_vs_gt'] = round(cer, 3)
R['caption_chars_cand'] = len(ct)
R['caption_chars_gt'] = len(gt_t)
# coverage: fraction of kept speech (output time) that has a caption
cov_m = mask([(c['out_start'], c['out_end']) for c in caps], out_dur)
R['caption_coverage_out'] = round(float(cov_m[:int(out_dur / DT)].mean()) if out_dur > 0 else 0, 3)
s_text = 20 * max(0, 1 - cer / 0.6) * min(1, R['caption_coverage_out'] / 0.85)

# 4. caption form -- 10 : length & duration & cps
L = [len(c['text'].replace(' ', '')) for c in caps]
D = [c['out_end'] - c['out_start'] for c in caps]
cps = [l / max(0.05, d) for l, d in zip(L, D)]
R['captions'] = len(caps)
R['cap_len_median'] = float(np.median(L)) if L else 0
R['cap_len_max'] = max(L) if L else 0
R['cap_dur_median'] = round(float(np.median(D)), 2) if D else 0
R['cap_cps_p90'] = round(float(np.percentile(cps, 90)), 1) if cps else 0
viol = sum(1 for l, d, c in zip(L, D, cps) if l > 18 or d < 0.45 or c > 14)
overl = sum(1 for x, y in zip(caps, caps[1:]) if x['out_end'] > y['out_start'] + 0.02 and x.get('speaker') == y.get('speaker'))
R['cap_violations'] = viol
R['cap_same_speaker_overlaps'] = overl
s_form = 10 * max(0, 1 - (viol + overl) / max(1, len(caps)) * 2)

# 5. speaker attribution -- 15 (10 caption speaker acc + 5 character interval IoU)
def gt_speaker_at(src):
    best = None
    for g in gcaps:
        if g['src_start'] - 0.3 <= src <= g['src_end'] + 0.3:
            d = abs(src - (g['src_start'] + g['src_end']) / 2)
            if best is None or d < best[0]:
                best = (d, g['speaker'])
    return best[1] if best else None
ok = n = 0
for c in caps:
    if c['_src'] is None:
        continue
    gs = gt_speaker_at(c['_src'])
    if gs is None:
        continue
    n += 1
    ok += (('host' if gs == 'geonho' else 'guest') == c.get('speaker'))
acc = ok / max(1, n)
R['speaker_acc'] = round(acc, 3)
R['speaker_checked'] = n
# character intervals in source time
def ivals_src(iv, f):
    out = []
    for x in iv:
        s, e = f(x['out_start'] + 0.01), f(x['out_end'] - 0.01)
        if s is not None and e is not None:
            out.append((s, e))
    return out
cg = mask(ivals_src(E.get('character', []), o2s), SD) & cm
gg = mask(ivals_src(G['character_gif'], gt_o2s), SD) & cm
iou = (cg & gg).sum() / max(1, (cg | gg).sum())
R['character_iou_src'] = round(float(iou), 3)
s_spk = 10 * acc + 5 * iou

# 6. render conformance -- 15 (spec + style probes on frames)
pr = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration:stream=width,height,codec_type', '-of', 'json', a.video], capture_output=True, text=True)
pj = json.loads(pr.stdout or '{}')
vs = [s for s in pj.get('streams', []) if s.get('codec_type') == 'video']
W, H = (vs[0]['width'], vs[0]['height']) if vs else (0, 0)
vdur = float(pj.get('format', {}).get('duration', 0))
R['video_wh'] = [W, H]
R['video_duration'] = round(vdur, 2)
spec = (abs(W / H - 9 / 16) < 0.01 if H else False) + (abs(vdur - out_dur) < 0.5) + (any(s.get('codec_type') == 'audio' for s in pj.get('streams', [])))
# style probes
EXP = {'host': (0.5815, (0, 0, 0)), 'guest': (0.6409, (37, 41, 115))}
probe = [c for c in caps if c['out_end'] - c['out_start'] > 0.6][::max(1, len(caps) // 10)][:10]
good = 0
for c in probe:
    t = (c['out_start'] + c['out_end']) / 2
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{t:.3f}', '-i', a.video, '-frames:v', '1', '-vf', 'scale=540:960', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True).stdout
    if len(raw) != 540 * 960 * 3:
        continue
    im = np.frombuffer(raw, np.uint8).reshape(960, 540, 3).astype(int)
    yexp, col = EXP.get(c.get('speaker'), EXP['host'])
    y0, y1 = int((yexp - 0.06) * 960), int((yexp + 0.06) * 960)
    band = im[y0:y1, 60:480]
    wm = (band.min(2) >= 228)
    def longest(r):
        best = cur = 0
        for v in r:
            cur = cur + 1 if v else 0
            best = max(best, cur)
        return best
    rows = np.array([i for i in range(wm.shape[0]) if longest(wm[i]) >= 40])
    if len(rows) < 8:
        continue
    cy = (y0 + (rows.min() + rows.max()) / 2) / 960
    pos_ok = abs(cy - yexp) < 0.02
    inner = band[rows.min():rows.max()]
    txt = inner[inner.max(2) < 150]
    col_ok = len(txt) > 30 and np.abs(np.median(txt, 0) - np.array(col)).max() < 45
    good += 0.5 * pos_ok + 0.5 * col_ok
style = good / max(1, len(probe))
R['style_probe'] = round(style, 3)
# header present in a frame at t=5s: dark text pixels in y 13.5%-20.5%
raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', '5', '-i', a.video, '-frames:v', '1', '-vf', 'scale=540:960', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True).stdout
hdr = 0
if len(raw) == 540 * 960 * 3:
    im = np.frombuffer(raw, np.uint8).reshape(960, 540, 3).astype(int)
    hdr = float(((im[int(0.135 * 960):int(0.205 * 960), 60:480].max(2) < 60).sum()) > 400)
R['header_present'] = hdr
s_render = 5 * spec / 3 + 8 * style + 2 * hdr

# 7. audio loudness -- 5
lr = subprocess.run(['ffmpeg', '-v', 'info', '-nostats', '-i', a.video, '-af', 'ebur128=peak=true', '-f', 'null', '-'], capture_output=True, text=True).stderr
mI = re.findall(r'I:\s+(-?[\d.]+) LUFS', lr)
mP = re.findall(r'Peak:\s+(-?[\d.]+) dBFS', lr)
I = float(mI[-1]) if mI else -70
TP = float(mP[-1]) if mP else 0
R['lufs'] = I
R['true_peak'] = TP
s_audio = 4 * max(0, 1 - max(0, abs(I + 11) - 1) / 4) + (1 if TP <= -0.9 else 0)  # target -11 LUFS (user: source too quiet; his CapCut export is -9)

R['scores'] = dict(cut=round(s_cut, 2), pace=round(s_pace, 2), caption_text=round(s_text, 2), caption_form=round(s_form, 2), speaker=round(s_spk, 2), render=round(s_render, 2), audio=round(s_audio, 2))
R['auto_total_95'] = round(sum(R['scores'].values()), 2)
print(json.dumps(R, ensure_ascii=False, indent=1))
if a.out:
    json.dump(R, open(a.out, 'w'), ensure_ascii=False, indent=1)
