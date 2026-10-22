#!/usr/bin/env python3
"""Automatic QA of a rendered reel (independent of how it was edited: it re-listens and re-watches the OUTPUT).

usage: qa_auto.py --video out.mp4 --edl edl.json [--render-dir rXXX] --out qa/   [--no-stt]
writes qa/qa_report.json, qa/flag_*.jpg (one still per flag, labelled), qa/contact.jpg, qa/pairs.md (KR/EN/heard table)

Checks (numbers are the thresholds):
  audio  : re-STT of the output (whisper+zipformer) -> caption text vs heard syllables (match < 0.5 = mismatch),
           caption timing (starts > 0.40 s before / > 0.30 s after its speech), speech with no caption (>= 0.35 s),
           dead air > 0.70 s, clicks at cut points (|Δsample| spike > 6x local median within ±4 ms),
           loudness (target ±1 LU) and true peak (<= -1.0 dBTP)
  video  : frame-diff spikes that are NOT at an EDL cut / zoom change / transition (unexpected jump),
           global shake (phase-correlation shift > 1.5 px at 180 px width between consecutive frames, outside cuts),
           black/white frames (mean < 12 or > 245), frozen runs (>= 8 identical frames outside the hook hold),
           harsh cuts (diff at a cut > 2.5x the median cut diff) listed as info
  text   : English missing / longer than 3.2x the Korean characters / numbers that differ between KR and EN,
           captions shorter than 0.45 s or faster than 13 chars/s, caption on screen with no speech under it
  layout : card rectangle over the face box or over a caption box while both are visible
"""
import argparse, json, os, re, subprocess, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser()
ap.add_argument('--video', required=True)
ap.add_argument('--edl', required=True)
ap.add_argument('--render-dir')
ap.add_argument('--out', required=True)
ap.add_argument('--no-stt', action='store_true')
ap.add_argument('--models', default=os.environ.get('REELS_MODELS', os.path.expanduser('~/reels_models')))
a = ap.parse_args()
os.makedirs(a.out, exist_ok=True)
E = json.load(open(a.edl))
FPS = 30
flags = []


def flag(t, cat, sev, msg, **kw):
    flags.append(dict(t=round(float(t), 2), cat=cat, sev=sev, msg=msg, **kw))


def syl(s):
    return [c for c in s if '\uac00' <= c <= '\ud7a3' or c.isdigit()]


# ------------------------------------------------------------------ audio
wav = os.path.join(a.out, 'out.wav')
subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', a.video, '-vn', '-ac', '1', '-ar', '16000', wav], check=True)
x = np.frombuffer(subprocess.run(['ffmpeg', '-v', 'error', '-i', wav, '-f', 'f32le', '-'], capture_output=True).stdout, np.float32)
hop = 160
nb = len(x) // hop
db = 20 * np.log10(np.sqrt((x[:nb * hop].reshape(nb, hop) ** 2).mean(1)) + 1e-9)
floor = float(np.percentile(db, 10))
quiet = db < floor + 6
# dead air
run = 0
for i, q in enumerate(quiet):
    run = run + 1 if q else 0
    if run == 70:
        flag(i / 100 - 0.7, 'dead_air', 'major', 'silence > 0.70 s')
# clicks at cut points (48 kHz)
x48 = np.frombuffer(subprocess.run(['ffmpeg', '-v', 'error', '-i', a.video, '-vn', '-ac', '1', '-ar', '48000', '-f', 'f32le', '-'],
                                   capture_output=True).stdout, np.float32)
cut_t = [s['out_start'] for s in E['segments'][1:]]
for t in cut_t:
    i = int(t * 48000)
    if i < 960 or i + 960 >= len(x48):
        continue
    d = np.abs(np.diff(x48[i - 960:i + 960]))
    loc = d[960 - 192:960 + 192].max()
    med = np.median(d) + 1e-6
    if loc > 6 * med and loc > 0.02:
        flag(t, 'click', 'major' if loc > 0.08 else 'minor', f'possible click at cut (Δ {loc:.3f} vs median {med:.4f}) - listen')
# loudness
r = subprocess.run(['ffmpeg', '-v', 'info', '-nostats', '-i', a.video, '-af', 'ebur128=peak=true', '-f', 'null', '-'],
                   capture_output=True, text=True).stderr
I = float(re.findall(r'I:\s+(-?[\d.]+) LUFS', r)[-1])
TP = float(re.findall(r'Peak:\s+(-?[\d.inf]+) dBFS', r)[-1])
tgt = E.get('audio', {}).get('target_lufs', -11.0)
if abs(I - tgt) > 1.0:
    flag(0, 'loudness', 'major', f'integrated {I} LUFS vs target {tgt}')
if TP > -1.0:
    flag(0, 'true_peak', 'major', f'true peak {TP} dBTP > -1.0')

# re-STT of the output
heard = []
if not a.no_stt:
    stt = os.path.join(a.out, 'stt_out.json')
    if not os.path.exists(stt):
        subprocess.run([sys.executable, os.path.join(HERE, 'analyze_audio.py'), wav, stt, '--models', a.models], check=True,
                       stdout=subprocess.DEVNULL)
    S = json.load(open(stt))
    for sg in S['segments']:
        ww = sg.get('words') or []
        toks = [w['w'] for w in ww]
        halluc = len(toks) >= 4 and (len(set(toks)) / len(toks) < 0.35 or not any(syl(t) for t in toks))
        if halluc:   # whisper loops ("Q. Q. Q.") on some chunks -> trust zipformer only there
            flag(sg['start'], 'qa_note', 'info', f"whisper hallucinated at {sg['start']:.1f}-{sg['end']:.1f}s; zipformer used")
            ww = []
        for w in ww:
            heard.append(dict(w=w['w'], start=w['start'], end=w['end']))
        # zipformer tokens as a second opinion (keeps syllables whisper dropped)
        for tk in sg['tokens']:
            heard.append(dict(w=tk['t'].replace('\u2581', ''), start=tk['ts'], end=tk['ts'] + 0.2, zip=True))

caps = E['captions']
pairs = ['| # | 시간 | 화자 | 자막 | English | 들린 말(재인식) | 일치 |', '|---|---|---|---|---|---|---|']
for k, c in enumerate(caps):
    t0, t1 = c['out_start'], c['out_end']
    L = len(c['text'].replace(' ', ''))
    if t1 - t0 < 0.45:
        flag(t0, 'caption_short', 'minor', f"'{c['text']}' only {t1 - t0:.2f} s")
    if L / max(0.05, t1 - t0) > 13:
        flag(t0, 'caption_fast', 'minor', f"'{c['text']}' {L / (t1 - t0):.1f} chars/s")
    en = c.get('en')
    if E.get('layers', {}).get('english', True) and E.get('stage') != 'cut':
        if not en:
            flag(t0, 'en_missing', 'major', f"no English for '{c['text']}'")
        elif len(en) > 3.2 * max(1, len(c['text'])):
            flag(t0, 'en_long', 'minor', f"English much longer than Korean: '{en}'")
        if en:
            def nums_kr(s):
                v = []
                for m in re.finditer(r'(\d[\d,\.]*)\s*(억|천만|백만|만|천)?', s):
                    n = float(m.group(1).replace(',', ''))
                    n *= {'억': 1e8, '천만': 1e7, '백만': 1e6, '만': 1e4, '천': 1e3}.get(m.group(2), 1)
                    v.append(n)
                return v
            def nums_en(s):
                v = []
                for m in re.finditer(r'(\d[\d,\.]*)\s*(billion|million|thousand|[MKB])?\b', s):
                    n = float(m.group(1).replace(',', ''))
                    n *= {'billion': 1e9, 'B': 1e9, 'million': 1e6, 'M': 1e6, 'thousand': 1e3, 'K': 1e3}.get(m.group(2), 1)
                    v.append(n)
                return v
            nk, ne = sorted(nums_kr(c['text'])), sorted(nums_en(en))
            if nk and nk != ne and not (len(nk) == len(ne) and all(abs(p - q) / max(p, q, 1) < 0.01 for p, q in zip(nk, ne))):
                flag(t0, 'en_number', 'major', f"numbers differ KR {nk} vs EN {ne}: '{c['text']}' / '{en}'")
    if heard:
        ws = [w for w in heard if t0 - 0.15 <= (w['start'] + w['end']) / 2 <= t1 + 0.15]
        hs = syl(''.join(w['w'] for w in ws))
        cs = syl(c['text'])
        match = sum(1 for ch in cs if ch in hs) / max(1, len(cs))
        wt = [w for w in ws if not w.get('zip')]
        zip_only = not wt
        if cs and match < 0.5:
            flag(t0, 'caption_mismatch', 'major' if zip_only or match >= 0.25 else 'blocker',
                 f"caption '{c['text']}' vs heard '{' '.join(w['w'] for w in wt)[:60]}' (match {match:.2f})")
        own = [w for w in wt if set(syl(w['w'])) & set(cs)]       # words that belong to THIS caption
        if own:
            first = min(w['start'] for w in own)
            if t0 < first - 0.40:
                flag(t0, 'caption_early', 'minor', f"'{c['text']}' appears {first - t0:.2f} s before the speech")
            if t0 > first + 0.30:
                flag(t0, 'caption_late', 'major' if t0 - first > 0.45 else 'minor', f"'{c['text']}' appears {t0 - first:.2f} s after the speech starts")
        if not wt:
            ss = quiet[int(t0 * 100):int(t1 * 100)]
            if len(ss) and ss.mean() > 0.85:
                flag(t0, 'caption_on_silence', 'major', f"'{c['text']}' shown while nothing is said")
        pairs.append(f"| {k} | {t0:.2f}-{t1:.2f} | {c['speaker']} | {c['text']} | {en or ''} | {' '.join(w['w'] for w in wt)} | {match:.2f} |")
    else:
        pairs.append(f"| {k} | {t0:.2f}-{t1:.2f} | {c['speaker']} | {c['text']} | {en or ''} | | |")
if heard and E.get('stage') != 'cut':
    cov = np.zeros(int(E['out_duration'] * 100) + 10, bool)
    for c in caps:
        cov[int(c['out_start'] * 100):int(c['out_end'] * 100)] = True
    hk = E.get('hook', {}).get('out_end', 0) if not any(c.get('cold') for c in caps) else 0
    for w in heard:
        if w.get('zip'):
            continue
        m = (w['start'] + w['end']) / 2
        if m > hk and w['end'] - w['start'] >= 0.15 and not cov[min(len(cov) - 1, int(m * 100))]:
            if not syl(w['w']) or w['w'].strip('?.,!') in ('음', '어', '응', '엉', '아'):
                continue
            flag(m, 'uncaptioned', 'minor', f"'{w['w']}' heard with no caption")
open(os.path.join(a.out, 'pairs.md'), 'w').write('\n'.join(pairs) + '\n')

# ------------------------------------------------------------------ video
Wv, Hv = 180, 320
raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', a.video, '-vf', f'scale={Wv}:{Hv}:flags=area,format=gray', '-f', 'rawvideo', '-'],
                     capture_output=True).stdout
F = np.frombuffer(raw, np.uint8).reshape(-1, Hv, Wv).astype(np.float32)
n = len(F)
diff = np.abs(np.diff(F, axis=0)).mean((1, 2))
expected = set()
for s in E['segments'][1:]:
    f = int(round(s['out_start'] * FPS))
    expected.update(range(f - 2, f + 2))
for z in E.get('zooms', []):
    f = int(round(z['out_start'] * FPS))
    expected.update(range(f - 2, f + 2))
for tr in E.get('transitions', []):
    f = int(round(tr['t'] * FPS))
    expected.update(range(f - 8, f + 9))
for c in E.get('cards', []):
    for tt in (c['out_start'], c['out_end']):
        f = int(round(tt * FPS))
        expected.update(range(f - 10, f + 10))
for c in caps:  # caption pop-in/out changes pixels too
    for tt in (c['out_start'], c['out_end']):
        f = int(round(tt * FPS))
        expected.update(range(f - 1, f + 2))
for iv in E.get('character', []):
    for tt in (iv['out_start'], iv['out_end']):
        f = int(round(tt * FPS))
        expected.update(range(f - 1, f + 2))
med = float(np.median(diff))
mad = float(np.median(np.abs(diff - med))) + 1e-3
for i, d in enumerate(diff):
    if i + 1 not in expected and i not in expected and d > med + 12 * mad and d > 6:
        flag((i + 1) / FPS, 'unexpected_jump', 'major', f'frame jump {d:.1f} (median {med:.1f}) not at a planned cut/zoom')
cut_d = [diff[int(round(s['out_start'] * FPS)) - 1] for s in E['segments'][1:] if 0 < int(round(s['out_start'] * FPS)) <= len(diff)]
if cut_d:
    mc = float(np.median(cut_d))
    for s in E['segments'][1:]:
        f = int(round(s['out_start'] * FPS))
        if 0 < f <= len(diff) and diff[f - 1] > 2.5 * mc and diff[f - 1] > 10:
            flag(s['out_start'], 'harsh_cut', 'info', f'cut jump {diff[f - 1]:.1f} vs median cut {mc:.1f}')
try:
    import cv2
    win = np.outer(np.hanning(Hv), np.hanning(Wv)).astype(np.float32)
    for i in range(1, n):
        if i in expected or i - 1 in expected:
            continue
        (dx, dy), resp = cv2.phaseCorrelate(F[i - 1] * win, F[i] * win)
        if (dx * dx + dy * dy) ** 0.5 > 1.5 and resp > 0.2:
            flag(i / FPS, 'shake', 'major', f'global shift {dx:.1f},{dy:.1f}px @180w between consecutive frames')
except Exception as e:  # cv2 missing -> skip
    flag(0, 'qa_note', 'info', f'shake check skipped: {e}')
means = F.mean((1, 2))
hook_hold = set(range(0, int(E.get('hook', {}).get('out_end', 0) * FPS) + 1))
for i, m in enumerate(means):
    if (m < 12 or m > 245) and i not in expected:
        flag(i / FPS, 'black_white_frame', 'major', f'frame mean {m:.0f}')
runlen = 0
for i, d in enumerate(diff):
    runlen = runlen + 1 if d < 0.05 else 0
    if runlen == 8 and i not in hook_hold:
        flag((i - 7) / FPS, 'frozen', 'major', '>= 8 identical frames')

# ------------------------------------------------------------------ layout (needs the render manifest)
if a.render_dir:
    man = json.load(open(os.path.join(a.render_dir, 'manifest.json')))
    s_ = man['s']
    def ov(r1, r2):
        return not (r1[0] + r1[2] <= r2[0] or r2[0] + r2[2] <= r1[0] or r1[1] + r1[3] <= r2[1] or r2[1] + r2[3] <= r1[1])
    for cd in man.get('cards', []):
        crect = (cd['x'], cd['y'], cd.get('w', 0), cd.get('h', 0))
        for cp in man['captions']:
            if cp['t0'] < cd['t1'] and cp['t1'] > cd['t0'] and ov(crect, (cp['x'], cp['y'], cp['w'], cp['h'])):
                flag(max(cp['t0'], cd['t0']), 'overlap', 'major', 'card covers a caption')
        for sg in E['segments']:
            if sg['out_start'] < cd['t1'] and sg['out_end'] > cd['t0'] and sg.get('face'):
                fx, fy, fw, fh = sg['face']
                frect = (fx * man['W'], fy * man['H'], fw * man['W'], fh * man['H'])
                if ov(crect, frect):
                    flag(max(sg['out_start'], cd['t0']), 'overlap', 'major', 'card covers the face')
                    break

# ------------------------------------------------------------------ stills for every flag + contact sheet
from PIL import Image, ImageDraw, ImageFont
fnt_p = os.path.join(HERE, '..', 'assets', 'Pretendard-ExtraBold.otf')
fnt = ImageFont.truetype(fnt_p, 16)
flags.sort(key=lambda f: f['t'])
for j, f in enumerate([f for f in flags if f['sev'] in ('blocker', 'major')][:40]):
    p = os.path.join(a.out, f'flag_{j:02d}_{f["cat"]}_{f["t"]:.2f}.jpg')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-ss', f'{max(0, f["t"]):.3f}', '-i', a.video, '-frames:v', '1', '-vf', 'scale=540:960', p])
    f['still'] = p
dur = E['out_duration']
ts = np.linspace(0.5, dur - 0.5, 20)
tiles = []
for t in ts:
    b = subprocess.run(['ffmpeg', '-v', 'error', '-ss', f'{t:.3f}', '-i', a.video, '-frames:v', '1', '-vf', 'scale=216:384',
                        '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True).stdout
    if len(b) == 216 * 384 * 3:
        im = Image.frombytes('RGB', (216, 384), b)
        ImageDraw.Draw(im).text((6, 6), f'{t:.1f}s', fill=(255, 255, 0), font=fnt)
        tiles.append(im)
if tiles:
    sheet = Image.new('RGB', (216 * 5, 384 * ((len(tiles) + 4) // 5)))
    for i, im in enumerate(tiles):
        sheet.paste(im, ((i % 5) * 216, (i // 5) * 384))
    sheet.save(os.path.join(a.out, 'contact.jpg'), quality=85)
summary = {k: sum(1 for f in flags if f['sev'] == k) for k in ('blocker', 'major', 'minor', 'info')}
rep = dict(video=a.video, duration=dur, lufs=I, true_peak=TP, summary=summary, flags=flags)
json.dump(rep, open(os.path.join(a.out, 'qa_report.json'), 'w'), ensure_ascii=False, indent=1)
print(json.dumps(summary), 'flags ->', os.path.join(a.out, 'qa_report.json'))
for f in flags:
    if f['sev'] in ('blocker', 'major'):
        print(f"  {f['t']:7.2f}s {f['sev']:7s} {f['cat']:18s} {f['msg']}")
