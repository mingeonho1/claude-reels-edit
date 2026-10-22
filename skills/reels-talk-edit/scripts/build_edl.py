#!/usr/bin/env python3
"""plan.json (Claude's editorial decisions) + words.json + rms envelope + face track -> edl.json

usage: build_edl.py --plan plan.json --words words.json --rms stt_rms10ms.npy --face face.npz --out edl.json
                    [--style style.json] [--src-name NAME]

Cut engine (word-boundary safe):
  * kept words = words[start_word..end_word] minus plan.drop (word ranges or source-time ranges)
  * islands: consecutive kept words; a new island starts after a drop or a pause > PAUSE_CUT (0.40 s)
  * in-point  = first-word start - PAD_IN (0.10 s), out-point = last-word end + PAD_OUT (0.14 s);
    if the neighbouring (kept or dropped) word is closer than the pad, the point moves to the energy minimum
    (30 ms smoothed RMS) between the two words, never inside a word span; otherwise it is nudged to the
    lowest-energy 10 ms frame within +-0.05 s.  Pause left across a cut = PAD_OUT+PAD_IN = 0.24 s source.
  * islands whose gap after padding < 0.12 s are merged (no cut).
  * speed per segment: host-dominant 1.20, guest-dominant (>=3 s) 1.30, else 1.25  (plan.speed overrides)
Captions: times come only from word timestamps (or explicit plan 'src' overrides) mapped through the cut/speed
  map; lead 0.05 s, tail 0.15 s; same-speaker gaps < 1.2 s are closed (no flicker); min 0.6 s.
Character (guest avatar) blocks: guest captions merged across gaps < 3.0 s (plan char_merge_gap) or across host 맞장구
  (host caption <= 1.3 s and <= 6 chars, no '?'); blocks < 1.5 s dropped; never during the hook.
Zoom ('구도 전환'): host talking -> 1.10 (his approved punch-in); otherwise 1.00/1.08 alternate so no framing lasts
  > ~4-5 s (plan "retention":"strong" -> 1.00/1.10 every ~2.7 s). Switches happen only at cuts or caption starts.
Hard checks (exit 2, EDL not written unless --force): caption > 16 chars w/o spaces or > 21 with spaces, < 0.45 s,
  > 13 cps, same-speaker overlap, card < 2.5 s, card promising a next episode/CTA, output > target_out x 1.05.
Warnings: uncaptioned kept speech >= 0.35 s, caption holes > 1 s, card numbers not in the transcript, cards < 8 s apart.
"""
import argparse, json, re
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument('--plan', required=True)
ap.add_argument('--words', required=True)
ap.add_argument('--rms', required=True)
ap.add_argument('--face', required=True)
ap.add_argument('--out', required=True)
ap.add_argument('--style')
ap.add_argument('--src-name')
ap.add_argument('--force', action='store_true', help='write the EDL even if hard checks fail (preview only)')
a = ap.parse_args()
P = json.load(open(a.plan))
WJ = json.load(open(a.words))
W = WJ['words']
env = np.load(a.rms).astype(float)
HOP = 0.01
# ---- workflow stage -> which layers are rendered (user 2026-10-22: cut preview -> captions KR+EN -> enhancements) ----
STAGE = P.get('stage', 'final')            # 'cut' | 'subs' | 'final'
MOD = dict(header=True, hook=True, character=True, zoom=True, cards=True)
MOD.update(P.get('modules', {}))
if STAGE == 'cut':
    LAYERS = dict(captions=False, english=False, header=False, hook=False, character=False, cards=False, zoom=False)
elif STAGE == 'subs':
    LAYERS = dict(captions=True, english=True, header=False, hook=False, character=False, cards=False, zoom=False)
else:
    LAYERS = dict(captions=True, english=P.get('english', True), **MOD)

F = np.load(a.face)
FPS_OUT = 30

PAUSE_CUT = P.get('pause_cut', 0.40)
PAD_IN, PAD_OUT = P.get('pad_in', 0.10), P.get('pad_out', 0.14)
SPD = dict(host=1.20, guest=1.30, mixed=1.25)
SPD.update(P.get('speed', {}))

# smoothed envelope (30 ms)
k = np.ones(3) / 3
envs = np.convolve(env, k, mode='same')


def e_at(t):
    return envs[min(len(envs) - 1, max(0, int(round(t / HOP))))]


def argmin_e(t0, t1, anchor=None, slope=20.0):
    """lowest smoothed energy in [t0, t1]; with an anchor (the word edge) every 0.1 s away costs 2 dB, so a short
    dip inside the NEXT word (e.g. between '라' and '고') does not beat the dip right at the word boundary."""
    i0, i1 = int(round(t0 / HOP)), int(round(t1 / HOP))
    if i1 <= i0:
        return (t0 + t1) / 2
    seg = envs[i0:i1 + 1].copy()
    if anchor is not None:
        seg += slope * np.abs(np.arange(i0, i1 + 1) * HOP - anchor)
    return (i0 + int(np.argmin(seg))) * HOP


# ---- captions may address words by source time instead of index: {"t":[t0,t1]} ----
for c in P.get('captions', []):
    if 'w' not in c and 't' in c:
        idx = [w['i'] for w in W if c['t'][0] <= (w['start'] + w['end']) / 2 <= c['t'][1]]
        if not idx:
            raise SystemExit(f"caption {c['text']!r}: no words in {c['t']}")
        c['w'] = [idx[0], idx[-1]]
for k in ('start_word', 'end_word'):
    if isinstance(P.get(k), float):
        P[k] = min(W, key=lambda w: abs(w['start'] - P[k]))['i'] if k == 'start_word' else min(W, key=lambda w: abs(w['end'] - P[k]))['i']
if P.get('hook', {}).get('until_t') is not None:
    P['hook']['until_word'] = min(W, key=lambda w: abs(w['end'] - P['hook']['until_t']))['i']
for c in P.get('cards', []):
    if 'at_t' in c:
        c['at_word'] = min(W, key=lambda w: abs(w['start'] - c['at_t']))['i']

# ---- word overrides (retimed words from retranscribe) ----
for o in P.get('retime', []):
    W[o['i']]['start'], W[o['i']]['end'] = o['src']

# ---- kept words ----
s_w, e_w = P.get('start_word', 0), P.get('end_word', len(W) - 1)
dropped = set()
for d in P.get('drop', []):
    if 'w' in d:
        dropped.update(range(d['w'][0], d['w'][1] + 1))
drop_t = [tuple(d['t']) for d in P.get('drop', []) if 't' in d]
for w in W:
    mid = (w['start'] + w['end']) / 2
    if any(t0 <= mid <= t1 for t0, t1 in drop_t):
        dropped.add(w['i'])
kept = [w for w in W if s_w <= w['i'] <= e_w and w['i'] not in dropped]
FILL = {'음', '어', '엄', '흠'}

QTHR = float(np.percentile(envs, 10)) + 6.0   # "quiet" = within 6 dB of the room-noise floor
Q_MIN = P.get('quiet_min', 0.28)              # a pause is cut only if a verified quiet run >= 0.28 s exists


def quiet_runs(t0, t1, min_len=0.04):
    i0, i1 = max(0, int(t0 / HOP)), min(len(envs), int(t1 / HOP) + 1)
    runs, st = [], None
    for i in range(i0, i1):
        if envs[i] < QTHR:
            st = i if st is None else st
        else:
            if st is not None:
                runs.append((st * HOP, i * HOP))
            st = None
    if st is not None:
        runs.append((st * HOP, i1 * HOP))
    return [r for r in runs if r[1] - r[0] >= min_len]


# boundaries between consecutive kept words
islands = [[kept[0]]] if kept else []
pause_run = {}
for p_, w in zip(kept, kept[1:]):
    crosses_drop = w['i'] != p_['i'] + 1
    if not crosses_drop:
        rs = quiet_runs(p_['end'] - 0.08, w['start'] + 0.08)
        best = max(rs, key=lambda r: r[1] - r[0]) if rs else None
        need = max(0.15, min(Q_MIN, 0.5 * (w['start'] - p_['end'])))  # long word gaps (breath/noise inside) need less
        if best is None or best[1] - best[0] < need:
            islands[-1].append(w)
            continue
        pause_run[w['i']] = best
    islands.append([w])
# drop filler-only islands
islands = [isl for isl in islands if not all(re.sub(r'[,.?!]', '', w['w']) in FILL for w in isl)]

segs = []
for isl in islands:
    f, l = isl[0], isl[-1]
    # ---- in-point ----
    if f['i'] in pause_run:
        r0, r1 = pause_run[f['i']]
        sin, tight_in = r1 - min(PAD_IN, (r1 - r0) / 2), False
    else:
        prv = W[f['i'] - 1] if f['i'] > 0 else None
        lim = prv['end'] - 0.05 if prv else f['start'] - 0.6
        rs = quiet_runs(min(lim, f['start'] - 0.05), f['start'] + 0.10)
        if rs:
            r0, r1 = rs[-1]
            sin, tight_in = r1 - min(PAD_IN, (r1 - r0) * 0.6), (r1 - r0) < 0.12
        else:
            # word times are +-0.15 s: search the energy minimum from 0.12 s before the previous word's end
            sin, tight_in = argmin_e(min(lim - 0.07, f['start'] - 0.06), f['start'] + 0.03, anchor=f['start']), True
    # ---- out-point ----
    nk = kept[kept.index(l) + 1] if kept.index(l) + 1 < len(kept) else None
    if nk is not None and nk['i'] in pause_run:
        r0, r1 = pause_run[nk['i']]
        sout, tight_out = r0 + min(PAD_OUT, (r1 - r0) / 2), False
    else:
        nxt = W[l['i'] + 1] if l['i'] + 1 < len(W) else None
        lim = nxt['start'] + 0.05 if nxt else l['end'] + 0.6
        rs = quiet_runs(l['end'] - 0.10, max(lim, l['end'] + 0.05))
        if rs:
            r0, r1 = rs[0]
            sout, tight_out = r0 + min(PAD_OUT, (r1 - r0) * 0.6), (r1 - r0) < 0.12
        else:
            sout, tight_out = argmin_e(l['end'] - 0.06, max(lim + 0.07, l['end']), anchor=l['end']), True
    segs.append(dict(src_start=round(max(0, sin), 3), src_end=round(sout, 3), words=[w['i'] for w in isl],
                     tight=[bool(tight_in), bool(tight_out)]))
# merge near-contiguous
merged = []
for s_ in segs:
    if merged and s_['src_start'] - merged[-1]['src_end'] < 0.12:
        merged[-1]['src_end'] = s_['src_end']
        merged[-1]['words'] += s_['words']
        merged[-1]['tight'][1] = s_['tight'][1]
    else:
        merged.append(s_)
segs = merged

# ---- cold open (user 2026-10-22: put the ending question first as the hook) ----
# plan: "cold_open": {"t": [src0, src1]}  -> that span is played FIRST (duplicated), then the edit starts.
CO = P.get('cold_open')
if CO:
    # "spans": [[src_in, src_out], ...] played first in this order (each its own segment); legacy "src"/"t" = one span
    spans = CO.get('spans') or [CO.get('src') or CO['t']]
    for k, (c_in, c_out) in enumerate(spans):
        cw = [w for w in W if c_in <= (w['start'] + w['end']) / 2 <= c_out]
        segs.insert(k, dict(src_start=round(c_in, 3), src_end=round(c_out, 3), words=[w['i'] for w in cw],
                            tight=[True, True], cold=True))

# ---- speed ----
for s in segs:
    hw = sum(W[i]['end'] - W[i]['start'] for i in s['words'] if W[i]['spk'] == 'host')
    gw = sum(W[i]['end'] - W[i]['start'] for i in s['words'] if W[i]['spk'] != 'host')
    dur = s['src_end'] - s['src_start']
    s['host_frac'] = round(hw / max(1e-6, hw + gw), 2)
    if s['host_frac'] >= 0.6:
        sp = SPD['host']
    elif s['host_frac'] <= 0.4 and dur >= 3.0:
        sp = SPD['guest']
    else:
        sp = SPD['mixed']
    s['speed'] = sp
for o in P.get('seg_speed', []):  # explicit overrides by first word index
    for s in segs:
        if o['w'] in s['words']:
            s['speed'] = o['speed']

# duration discipline: if the edit is longer than target_out, raise all speeds proportionally (cap 1.40 = the
# user's upper bound) instead of cutting inside sentences; whatever is still over must be dropped editorially.
TARGET = P.get('target_out', 88.0)
SPEED_CAP = P.get('speed_cap', 1.40)
if P.get('auto_speed', True):
    for _ in range(4):
        out_est = sum((s['src_end'] - s['src_start']) / s['speed'] for s in segs)
        if out_est <= TARGET:
            break
        f_ = out_est / TARGET
        for s in segs:
            s['speed'] = round(min(SPEED_CAP, s['speed'] * f_ + 0.004), 2)

# speaker-turn breathing room (user 2026-10-22: "정우와 내 텀이 너무 짧아"): at every cut where the speaker changes,
# guarantee >= turn_gap s of silence in the OUTPUT. Order: extend the out-point of A forward through verified quiet,
# then the in-point of B backward through quiet, and only then pre-roll B's video with muted audio (mute_lead).
TURN_GAP = P.get('turn_gap', 0.20)   # research: natural turn gap ~200 ms (Stivers 2009); >500 ms reads as hesitation
def _quiet_src(t):
    return e_at(t) < QTHR - 1.0   # floor+5 dB: breath/room noise between turns does not count as a pause
for a_, b_ in zip(segs, segs[1:]):
    if abs(b_['src_start'] - a_['src_end']) < 0.02:
        continue                                    # contiguous in source (speed split): natural gap
    la, fb = W[a_['words'][-1]], W[b_['words'][0]]
    if la['spk'] == fb['spk'] and not a_.get('cold'):
        continue
    # current silence: quiet after the last voiced frame of A + quiet before the first voiced frame of B
    qa = 0.0
    while qa < 1.0 and _quiet_src(a_['src_end'] - qa - HOP):
        qa += HOP
    qb = 0.0
    while qb < 1.0 and _quiet_src(b_['src_start'] + qb + HOP):
        qb += HOP
    need = TURN_GAP - (qa / a_['speed'] + qb / b_['speed'])
    if need <= 0:
        continue
    nxt_w = W[la['i'] + 1]['start'] if la['i'] + 1 < len(W) else a_['src_end'] + 1.0
    ext = 0.0
    while need > 0 and a_['src_end'] + ext + HOP < nxt_w - 0.03 and _quiet_src(a_['src_end'] + ext + HOP):
        ext += HOP
        need -= HOP / a_['speed']
    a_['src_end'] = round(a_['src_end'] + ext, 4)
    if ext > 0:
        a_['tight'][1] = False
    prv_w = W[fb['i'] - 1]['end'] if fb['i'] > 0 else 0.0
    ext = 0.0
    _floor_b = max(prv_w + 0.03, a_['src_end']) if a_['src_end'] <= b_['src_start'] else prv_w + 0.03   # cold open jumps back in source
    while need > 0 and b_['src_start'] - ext - HOP > _floor_b and _quiet_src(b_['src_start'] - ext - HOP):
        ext += HOP
        need -= HOP / b_['speed']
    b_['src_start'] = round(b_['src_start'] - ext, 4)
    if need > 0:
        ml = round(need * b_['speed'], 3)
        if b_['src_start'] - ml > _floor_b - 0.03 or a_.get('cold'):   # after the cold open the white flash hides the pre-roll
            b_['src_start'] = round(b_['src_start'] - ml, 4)
            b_['mute_lead'] = ml                      # source seconds of pre-roll whose audio is muted
    print(f"turn gap @src {b_['src_start']:.2f}: had {qa / a_['speed'] + qb / b_['speed']:.2f}s out, mute_lead {b_.get('mute_lead', 0)}")

# QA fixes: extra muted lead-in on a segment (residual syllable of a dropped word right after a tight in-point)
for mx in P.get('mute_extra', []):
    for s_ in segs:
        if abs(s_['src_start'] - mx['src']) <= 0.2 and not s_.get('cold'):
            s_['mute_lead'] = round(s_.get('mute_lead', 0.0) + mx['add'], 3)

# frame-exact output timeline: each segment gets an integer number of output frames
t = 0.0
fr = 0
for s in segs:
    x_ = (s['src_end'] - s['src_start']) / s['speed'] * FPS_OUT
    n = int(np.floor(x_ + 1e-6)) if s['tight'][1] else int(round(x_))   # never run past a tight out-point
    s['frames'] = n
    s['out_start'] = round(fr / FPS_OUT, 4)
    fr += n
    s['out_end'] = round(fr / FPS_OUT, 4)
    # make src_end consistent with the frame count (sub-frame adjust)
    s['src_end'] = round(s['src_start'] + n / FPS_OUT * s['speed'], 4)
OUT_DUR = fr / FPS_OUT


def s2o(x, side='start'):
    for s in segs:
        if s.get('cold'):
            continue
        if s['src_start'] - 1e-6 <= x <= s['src_end'] + 1e-6:
            return s['out_start'] + (x - s['src_start']) / s['speed']
    # in a cut gap: snap to the next segment start (for starts) / previous end (for ends)
    if side == 'start':
        nxt = [s for s in segs if s['src_start'] > x and not s.get('cold')]
        return nxt[0]['out_start'] if nxt else OUT_DUR
    prv = [s for s in segs if s['src_end'] < x and not s.get('cold')]
    return prv[-1]['out_end'] if prv else 0.0


# ---- hook ----
H = P.get('hook', {})
hook_end = 0.0
if H.get('text'):
    hw_end = W[H['until_word']]['end'] if H.get('until_word') is not None else W[kept[0]['i']]['end']
    hook_end = min(H.get('max_dur', 3.0), max(H.get('min_dur', 2.4), s2o(hw_end, 'end') + 0.15))
    hook_end = round(round(hook_end * FPS_OUT) / FPS_OUT, 4)
    if CO:
        hook_end = max(s['out_end'] for s in segs if s.get('cold'))   # the cold open IS the hook

# ---- captions ----
caps = []
for c in P['captions']:
    i0, i1 = c['w']
    if 'src' in c:
        a0, a1 = c['src']
    else:
        a0, a1 = W[i0]['start'], W[i1]['end']
    # skip captions fully dropped
    if all(i in dropped or not (s_w <= i <= e_w) for i in range(i0, i1 + 1)) and 'src' not in c:
        continue
    o0, o1 = s2o(a0, 'start') - 0.05, s2o(a1, 'end') + 0.15
    # never start before the cut that brings in the caption's first word (no flash over the previous shot's tail)
    _host_seg = [s for s in segs if s['src_end'] + 1e-6 >= a0]
    if _host_seg:
        o0 = max(o0, _host_seg[0]['out_start'])
    # content check: caption syllables must mostly appear in its own spoken word span
    _sy = lambda t: [ch for ch in t if '\uac00' <= ch <= '\ud7a3' or ch.isdigit()]
    _spoken = ''.join(_sy(''.join(W[k]['w'] for k in range(i0, i1 + 1))))
    _cs = _sy(c['text'])
    if _cs and sum(1 for ch in _cs if ch in _spoken) / len(_cs) < 0.6:
        print(f"WARN caption text not in its own word span: '{c['text']}' vs '{_spoken[:40]}'")
    caps.append(dict(text=c['text'], speaker=c['speaker'], out_start=o0, out_end=o1, nat_end=o1, w=c['w'], en=c.get('en')))
caps.sort(key=lambda c: c['out_start'])
# hook suppression: captions inside the hook window are represented by the hook title
cc = []
for c in caps:
    if c['out_end'] <= hook_end + 0.25:
        continue
    if c['out_start'] < hook_end:
        c['out_start'] = hook_end
    cc.append(c)
caps = cc
# cold-open captions (time-addressed in source; mapped through the cold segments only)
if CO:
    def s2o_cold(x):
        for s in segs:
            if s.get('cold') and s['src_start'] - 1e-6 <= x <= s['src_end'] + 1e-6:
                return s['out_start'] + (x - s['src_start']) / s['speed']
        return None
    for c in CO.get('captions', []):
        o0, o1 = s2o_cold(c['t'][0]), s2o_cold(c['t'][1])
        if o0 is None or o1 is None:
            raise SystemExit(f"cold caption {c['text']!r} outside the cold spans")
        caps.append(dict(text=c['text'], speaker=c['speaker'], out_start=max(0.0, o0 - 0.05), out_end=min(hook_end, o1 + 0.15),
                         nat_end=min(hook_end, o1 + 0.15), w=[0, 0], cold=True, en=c.get('en')))
    caps.sort(key=lambda c: c['out_start'])
# close small gaps / speaker-change handoff
for i, c in enumerate(caps):
    nxt = [d for d in caps[i + 1:] if d['out_start'] >= c['out_start']]
    same = [d for d in nxt if d['speaker'] == c['speaker']]
    if same and same[0]['out_start'] - c['out_end'] < 1.2:
        c['out_end'] = same[0]['out_start']
    if nxt:
        n0 = nxt[0]
        if n0['speaker'] != c['speaker'] and n0['out_start'] >= c['nat_end'] - 0.05:
            # sequential turn: hold until the other speaker's caption appears (max +0.8 s)
            c['out_end'] = min(max(c['nat_end'], n0['out_start']), c['nat_end'] + 0.8) if n0['out_start'] - c['nat_end'] < 0.8 else c['nat_end'] + 0.3
            c['out_end'] = min(c['out_end'], n0['out_start']) if n0['out_start'] > c['out_start'] + 0.6 else c['out_end']
    # never overlap a following caption of the same speaker
    if same:
        c['out_end'] = min(c['out_end'], same[0]['out_start'])
    c['out_end'] = min(c['out_end'], OUT_DUR)
# min duration 0.6 s (extend end into free space, else start earlier)
for i, c in enumerate(caps):
    if c['out_end'] - c['out_start'] < 0.6:
        same_n = [d for d in caps[i + 1:] if d['speaker'] == c['speaker']]
        lim = same_n[0]['out_start'] if same_n else OUT_DUR
        c['out_end'] = min(lim, c['out_start'] + 0.6)
        if c['out_end'] - c['out_start'] < 0.6:
            same_p = [d for d in caps[:i] if d['speaker'] == c['speaker']]
            lo = same_p[-1]['out_end'] if same_p else hook_end
            c['out_start'] = max(lo, c['out_end'] - 0.6)
for c in caps:
    if c.get('cold'):
        c['out_end'] = min(c['out_end'], hook_end)
# handoff overlaps between speakers shorter than 0.3 s are just hold-over: end the earlier caption when the next
# speaker's caption appears (two rows + two English lines for 0.1-0.2 s read as flicker)
for c in caps:
    for d in caps:
        if d is not c and d['speaker'] != c['speaker'] and c['out_start'] < d['out_start'] < c['out_end'] and c['out_end'] - d['out_start'] < 0.3:
            c['out_end'] = d['out_start']
warn = []
form_viol = []   # hard: must be empty before rendering (B graft)
CAP_MAX_NS, CAP_MAX_WS = P.get('cap_max', 16), P.get('cap_max_ws', 21)
for c in caps:
    c['out_start'], c['out_end'] = round(c['out_start'], 3), round(c['out_end'], 3)
    L = len(c['text'].replace(' ', ''))
    d = c['out_end'] - c['out_start']
    if L > CAP_MAX_NS or len(c['text']) > CAP_MAX_WS:
        form_viol.append(f"too long ({L} chars w/o spaces, {len(c['text'])} with; max {CAP_MAX_NS}/{CAP_MAX_WS}): '{c['text']}' @ {c['out_start']:.2f}")
    if d < 0.45:
        form_viol.append(f"too short ({d:.2f} s < 0.45): '{c['text']}' @ {c['out_start']:.2f}")
    if L / max(d, 0.05) > 13:
        form_viol.append(f"too fast ({L / max(d, .05):.1f} cps > 13): '{c['text']}' @ {c['out_start']:.2f}")
    if d < 0.6:
        warn.append(f"caption '{c['text']}' shown only {d:.2f} s")
    c.pop('nat_end', None)
# same-speaker overlap (scorer + readability)
for x in caps:
    for y in caps:
        if x is not y and x['speaker'] == y['speaker'] and x['out_start'] < y['out_start'] < x['out_end'] - 0.02:
            form_viol.append(f"same-speaker overlap '{x['text']}' / '{y['text']}' @ {y['out_start']:.2f}")

# uncaptioned kept speech (e.g. a word left out of every caption range -> visible gap with audible speech)
covered = set()
for c in P['captions']:
    covered.update(range(c['w'][0], c['w'][1] + 1))
run = []
def _flush(run):
    if not run:
        return
    o0, o1 = s2o(run[0]['start'], 'start'), s2o(run[-1]['end'], 'end')
    if o1 - o0 >= 0.35 and not all(re.sub(r'[,.?!]', '', w['w']) in FILL for w in run):
        warn.append(f"UNCAPTIONED speech {o0:.2f}-{o1:.2f} out: '{' '.join(w['w'] for w in run)}' -> add to a caption or drop it")
for w in kept:
    if w['i'] in covered or (hook_end and s2o(w['start'], 'start') < hook_end):
        _flush(run); run = []
    else:
        run.append(w)
_flush(run)
# caption-free holes inside the edit (> 1.0 s with no caption while not in the hook)
cov = sorted((c['out_start'], c['out_end']) for c in caps)
t_ = hook_end
for c0, c1 in cov:
    if c0 - t_ > 1.0:
        warn.append(f"caption hole {t_:.2f}-{c0:.2f} out ({c0 - t_:.2f} s)")
    t_ = max(t_, c1)

# ---- character blocks ----
blocks = []
cur = None
for c in caps:
    if c['speaker'] == 'guest':
        if cur and c['out_start'] - cur[1] < P.get('char_merge_gap', 3.0):
            cur[1] = max(cur[1], c['out_end'])
        else:
            if cur:
                blocks.append(cur)
            cur = [c['out_start'], c['out_end']]
    else:
        short = (c['out_end'] - c['out_start'] <= 1.3 and len(c['text'].replace(' ', '')) <= 6 and '?' not in c['text'])
        if cur and not short:
            blocks.append(cur)
            cur = None
if cur:
    blocks.append(cur)
character = [dict(out_start=round(max(b[0] - 0.1, hook_end), 3), out_end=round(b[1], 3)) for b in blocks if b[1] - b[0] >= 1.5]
if CO and any(c.get('cold') and c['speaker'] == 'guest' for c in caps):
    character.insert(0, dict(out_start=0.0, out_end=round(hook_end, 3)))
character = [c for c in character if c['out_end'] - c['out_start'] >= 0.1]

# ---- face per segment + zoom ----
ft, fb = F['t'], F['box']


def face_stats(s0, s1):
    sel = (ft >= s0) & (ft <= s1)
    b = fb[sel]
    b = b[~np.isnan(b).any(1)] if len(b) else b
    if not len(b):
        return None, False
    med = np.median(b, 0)
    cx = b[:, 0] + b[:, 2] / 2
    cy = b[:, 1] + b[:, 3] / 2
    stable = bool(np.std(cx) < 0.015 and np.std(cy) < 0.01 and np.ptp(b[:, 2]) < 0.06)
    return [round(float(v), 4) for v in med], stable


# framing ('구도 전환'): his approved 110 % host punch-in + an alternation so no framing lasts > max_same.
# default = 'normal' (1.00/1.08 every >= 4 s, close to his look); 'strong' = B-style retention layer
# (1.00/1.10 about every 2.7 s at caption starts) - only when the user asks for more movement.
RET = P.get('retention', 'normal')
Z = dict(host=1.10, alt=1.08, max_same=4.0) if RET != 'strong' else dict(host=1.10, alt=1.10, max_same=2.7)
Z.update(P.get('zoom', {}))
for s in segs:
    s['face'], s['face_stable'] = face_stats(s['src_start'], s['src_end'])
# candidate framing-switch points: segment boundaries (hard cuts) + caption starts (sentence/breath boundaries)
cand = sorted(set([round(s['out_start'], 4) for s in segs] + [round(round(c['out_start'] * FPS_OUT) / FPS_OUT, 4) for c in caps]))
cand = [t for t in cand if t >= hook_end - 1e-6] + [round(OUT_DUR, 4)]


def seg_at(t):
    for s in segs:
        if s['out_start'] - 1e-6 <= t < s['out_end'] - 1e-6:
            return s
    return segs[-1]


def host_at(t0, t1):
    # framing for the interval: host punch-in when the host is the one talking (host caption covers > 50 %)
    hc = sum(max(0, min(t1, c['out_end']) - max(t0, c['out_start'])) for c in caps if c['speaker'] == 'host')
    gc = sum(max(0, min(t1, c['out_end']) - max(t0, c['out_start'])) for c in caps if c['speaker'] == 'guest')
    return hc > 0.5 * (t1 - t0) and hc > gc


zt = []  # [t0, t1, scale]
if not LAYERS.get('zoom', True):
    P['zoom_mode'] = 'off'
if P.get('zoom_mode') == 'off':
    clean = [[0.0, round(OUT_DUR, 4), 1.0]]
    for s in segs:
        s['_zface'] = s['face']
elif P.get('zoom_mode', 'host_cut') == 'host_cut':
    # research + user: punch-in ONLY as a hard cut (never mid-shot), only when the host (black caption) starts talking
    # right at a cut; it ends at the first cut once the guest has started (>= 1.5 s on screen), scale 1.08,
    # at most one punch-in start per 8 s; everything else 1.00.
    ZH, HOLD, GAP = Z.get('host_cut', 1.08), Z.get('min_hold', 3.0), Z.get('min_gap', 8.0)
    cut_idx = [i for i, s in enumerate(segs) if i and abs(s['src_start'] - segs[i - 1]['src_end']) > 0.02]
    hostc = [c for c in caps if c['speaker'] == 'host']
    zt_ = []
    last_start = -1e9
    for i in cut_idx:
        t0 = segs[i]['out_start']
        if t0 < hook_end - 1e-6 or t0 - last_start < GAP:
            continue
        hc = [c for c in hostc if abs(c['out_start'] - t0) <= 0.45]
        if not hc:
            continue
        # end: the next hard cut after the host's turn (guest starts) but at least HOLD later
        nxt = [segs[j]['out_start'] for j in cut_idx if segs[j]['out_start'] >= t0 + Z.get('min_zoom', 1.5)]
        guest_after = [c['out_start'] for c in caps if c['speaker'] == 'guest' and c['out_start'] > t0 + 0.3]
        if not guest_after:
            continue
        g0 = min(guest_after)
        near = [nc for nc in nxt if g0 - 0.5 <= nc <= g0 + 0.6]
        # punch-out on the turn change: at a cut if one is close, otherwise exactly when the guest's caption appears
        t1 = near[0] if near else round(round((g0 - 0.03) * FPS_OUT) / FPS_OUT, 4)
        if t1 - t0 < Z.get('min_zoom', 1.5):
            continue
        zt_.append([t0, t1, ZH])
        last_start = t0
    t = 0.0
    for a0, a1, z in zt_:
        if a0 > t:
            zt.append([t, a0, 1.0])
        zt.append([a0, a1, z])
        t = a1
    if t < OUT_DUR:
        zt.append([t, round(OUT_DUR, 4), 1.0])
    clean = [iv for iv in zt if iv[1] - iv[0] > 1e-6]
    fs = [s['face'] for s in segs if s['face']]
    FC = [float(np.median([f[k] for f in fs])) for k in range(4)] if fs else [0.3, 0.3, 0.3, 0.2]
    for s in segs:
        s['_zface'] = FC
elif P.get('zoom_mode') == 'host':
    # user 2026-10-22: "검정 자막이 나올때만 줌" -> punch-in (1.06) only while a HOST caption (black) is on screen,
    # 1.00 otherwise. Host spans closer than 0.6 s merge; spans < min_hold (1.2 s, e.g. a lone 맞장구) get no zoom;
    # a switch within 0.3 s of a hard cut snaps to the cut (the cut hides it). One fixed centre for the episode.
    ZH, MIN_HOLD = Z.get('host_cut', 1.06), Z.get('min_hold', 1.2)
    hs = []
    for c in sorted([c for c in caps if c['speaker'] == 'host'], key=lambda c: c['out_start']):
        if hs and c['out_start'] - hs[-1][1] < 0.6:
            hs[-1][1] = max(hs[-1][1], c['out_end'])
        else:
            hs.append([c['out_start'], c['out_end']])
    cuts = [s['out_start'] for i, s in enumerate(segs) if i and abs(s['src_start'] - segs[i - 1]['src_end']) > 0.02]
    def snap(t):
        near = [c for c in cuts if abs(c - t) <= 0.45]
        t = min(near, key=lambda c: abs(c - t)) if near else t
        return round(round(t * FPS_OUT) / FPS_OUT, 4)
    hs = [[snap(max(a0, hook_end)), snap(a1)] for a0, a1 in hs if a1 - max(a0, hook_end) >= MIN_HOLD]
    t = 0.0
    for a0, a1 in hs:
        if a0 > t:
            zt.append([t, a0, 1.0])
        zt.append([a0, a1, ZH])
        t = a1
    if t < OUT_DUR:
        zt.append([t, round(OUT_DUR, 4), 1.0])
    clean = [iv for iv in zt if iv[1] - iv[0] > 1e-6]
    fs = [s['face'] for s in segs if s['face']]
    FC = [float(np.median([f[k] for f in fs])) for k in range(4)] if fs else [0.3, 0.3, 0.3, 0.2]
    for s in segs:
        s['_zface'] = FC
elif P.get('zoom_mode') == 'cut':
    # user 2026-10-22 ("줌 하는거 좀 어색하다"): framing changes ONLY on hard cuts (source jumps), never inside a
    # continuous shot. host-question segment -> 1.08; otherwise each jump cut flips 1.00 <-> 1.05 so the jump is masked;
    # a new framing must last >= 2.0 s (shorter segments keep the current framing); during the hook = 1.00.
    ZH, ZA, MIN_HOLD = Z.get('host_cut', 1.08), Z.get('alt_cut', 1.05), Z.get('min_hold', 2.0)
    cur, since = 1.0, 0.0
    if hook_end > 0:
        zt.append([0.0, hook_end, 1.0])
    for i, s in enumerate(segs):
        t0, t1 = s['out_start'], s['out_end']
        if t1 <= hook_end + 1e-6:
            continue
        t0 = max(t0, hook_end)
        hard_cut = i == 0 or abs(s['src_start'] - segs[i - 1]['src_end']) > 0.02
        z = cur
        if hard_cut and t0 - since >= MIN_HOLD - 1e-6:
            if s['host_frac'] >= 0.6:
                z = ZH if cur != ZH else 1.0
            else:
                z = ZA if cur == 1.0 else 1.0
            # a short segment followed by more of the same speaker: don't flash a framing for < MIN_HOLD
            if z != cur and t1 - t0 < MIN_HOLD:
                nxt = [x for x in segs[i + 1:i + 3]]
                if not nxt or nxt[0]['src_start'] - s['src_end'] > 0.02:
                    z = cur
        if zt and zt[-1][2] == z:
            zt[-1][1] = t1
        else:
            zt.append([t0, t1, z])
            since = t0
        cur = z
    clean = zt
    # one framing centre for the whole episode (median face) -> no sideways jumps between framings
    fs = [s['face'] for s in segs if s['face']]
    FC = [float(np.median([f[k] for f in fs])) for k in range(4)] if fs else [0.3, 0.3, 0.3, 0.2]
    for s in segs:
        s['_zface'] = FC
else:
    zt = []  # [t0, t1, scale]
    if hook_end > 0:
        zt.append([0.0, hook_end, 1.0])
    cur, run = 1.0, (hook_end if hook_end else 0.0)
    hold_until = -1.0
    for t0, t1 in zip(cand[:-1], cand[1:]):
        if t1 - t0 < 1e-6:
            continue
        seg_change = any(abs(t0 - s['out_start']) < 1e-4 for s in segs)
        if host_at(t0, t1) and t0 >= hold_until:
            if cur == Z['host'] and run >= 1.25 * Z['max_same']:   # long host stretch: breathe out to 1.00 for >= 2.5 s
                z, hold_until = 1.0, t0 + 2.5
            else:
                z = Z['host']
        elif t0 < hold_until:
            z = cur
        elif cur == Z['host']:
            z = 1.0 if seg_change or True else cur
        elif run >= Z['max_same'] or (run >= 0.5 * Z['max_same'] and run + (t1 - t0) > 1.25 * Z['max_same']):
            z = Z['alt'] if cur == 1.0 else 1.0     # switch now rather than overshoot (captions can be 2-3 s apart)
        else:
            z = cur
        if zt and zt[-1][2] == z:
            zt[-1][1] = t1
            run += t1 - t0
        else:
            zt.append([t0, t1, z])
            run = t1 - t0
        cur = z
    # merge framings shorter than 1.2 s into the previous one (avoid flicker)
    clean = []
    for iv in zt:
        if clean and (iv[1] - iv[0] < 1.2 or clean[-1][2] == iv[2]):
            clean[-1][1] = iv[1]
        else:
            clean.append(iv)
zooms = []
for t0, t1, z in clean:
    s = seg_at(t0)
    f = s.get('_zface') or s['face'] or [0.3, 0.3, 0.3, 0.2]
    zooms.append(dict(out_start=round(t0, 4), out_end=round(t1, 4), scale=z,
                      cx=round(f[0] + f[2] / 2, 4), cy=round(f[1] + f[3] * 0.45, 4)))
for s in segs:
    s['zoom'] = max((z['scale'] for z in zooms if z['out_start'] < s['out_end'] and z['out_end'] > s['out_start']), default=1.0)

# ---- cards ----
cards = []
ALLTXT = re.sub(r'[^0-9]', '', ''.join(w['w'] for w in W))
for c in P.get('cards', []):
    t0 = s2o(W[c['at_word']]['start'], 'start')
    t1 = min(OUT_DUR - 0.2, t0 + c.get('dur', 4.0))
    if t1 - t0 < 2.5:
        form_viol.append(f"card '{c['title']}' only {t1 - t0:.1f} s on screen (min 2.5; move it earlier)")
    body = ' '.join([c['title']] + c.get('lines', []) + [c.get('accent', '')])
    for num in re.findall(r'\d[\d,]*', re.sub(r'(^|\s)\d\.\s', ' ', body)):
        n_ = num.replace(',', '')
        if n_ not in ALLTXT:
            warn.append(f"card '{c['title']}': number {num} not found in the transcript - cards may only state spoken facts")
    if re.search(r'다음\s*편|next episode|구독|팔로우', body):
        form_viol.append(f"card '{c['title']}' promises a next episode / CTA - only if the host says it on tape")
    cards.append(dict(out_start=round(t0, 3), out_end=round(t1, 3), title=c['title'], lines=c.get('lines', []),
                      accent=c.get('accent', ''), dir=c.get('dir', 'auto'), side=c.get('side', 'auto')))
for x, y in zip(cards, cards[1:]):
    if y['out_start'] - x['out_end'] < 8.0:
        warn.append(f"cards '{x['title']}' and '{y['title']}' only {y['out_start'] - x['out_end']:.1f} s apart (want >= 8 s)")

style = json.load(open(a.style)) if a.style else {}
edl = dict(source=a.src_name or WJ.get('source'), fps=FPS_OUT, out_frames=fr, out_duration=round(OUT_DUR, 4),
           segments=[dict(src_start=s['src_start'], src_end=s['src_end'], speed=s['speed'], frames=s['frames'],
                          out_start=s['out_start'], out_end=s['out_end'], zoom=s['zoom'], face=s['face'],
                          face_stable=s['face_stable'], host_frac=s['host_frac'], tight=s['tight'],
                          words=[s['words'][0], s['words'][-1]], mute_lead=s.get('mute_lead', 0.0),
                          gain_db=(P.get('audio', {}).get('host_gain_db', 0.0) if s['host_frac'] >= 0.6 else 0.0), cold=bool(s.get('cold'))) for s in segs],
           captions=[dict(text=c['text'], speaker=c['speaker'], out_start=c['out_start'], out_end=c['out_end'], w=c['w'],
                          en=c.get('en'), en_above=bool(c.get('en') and c['speaker'] == 'host' and any(
                              d['speaker'] != 'host' and min(c['out_end'], d['out_end']) - max(c['out_start'], d['out_start']) > 0.4 * (c['out_end'] - c['out_start']) for d in caps)))
                     for c in caps],
           layers=LAYERS, stage=STAGE, preview_timecode=P.get('preview_timecode', STAGE != 'final'),
           character=character,
           hook=dict(text=H.get('text', ''), out_start=0.0, out_end=hook_end, sub=H.get('sub'),
                     intro=H.get('intro', not CO)),
           transitions=([dict(t=hook_end, type=CO.get('transition', 'cut'), out_frames=4, in_frames=6, whoosh=CO.get('whoosh', False))] if CO else []),
           header=dict(out_start=hook_end, out_end=round(OUT_DUR, 4)),
           zooms=zooms, cards=cards,
           grade=P.get('grade', {}), retouch=P.get('retouch', {}),
           audio=dict(target_lufs=P.get('audio', {}).get('target_lufs', -11.0), true_peak=-1.5, fade_ms=12,
                      mode=P.get('audio', {}).get('mode', 'voice_chain')),
           style=style, warnings=warn)
sp = np.array([s['speed'] for s in segs]); wd = np.array([s['src_end'] - s['src_start'] for s in segs])
if OUT_DUR > TARGET * 1.05:
    form_viol.append(f"output {OUT_DUR:.1f} s > {TARGET * 1.05:.1f} s (target {TARGET} s): drop ~{(OUT_DUR - TARGET) * 1.3:.0f} s of source")
elif OUT_DUR > TARGET:
    warn.append(f"output {OUT_DUR:.1f} s > target {TARGET} s")
chars = sum(len(c['text'].replace(' ', '')) for c in caps)
cap_dur = max(1e-6, OUT_DUR - hook_end)
Ls = [len(c['text'].replace(' ', '')) for c in caps]
print(f"segments {len(segs)} kept_src {wd.sum():.1f}s out {OUT_DUR:.2f}s (target <= {TARGET}) avg_speed {(sp * wd).sum() / wd.sum():.3f} "
      f"captions {len(caps)} chars {chars} density {chars / cap_dur:.2f}/s (aim 4.3-5.2) len median {np.median(Ls) if Ls else 0:.0f} max {max(Ls) if Ls else 0} "
      f"char_blocks {len(character)} cards {len(cards)} hook_end {hook_end} tight_cuts {sum(sum(s['tight']) for s in segs)}")
for w_ in warn:
    print('WARN', w_)
print('FORM_VIOLATIONS', json.dumps(form_viol, ensure_ascii=False, indent=0) if form_viol else '[]')
edl['form_violations'] = form_viol
if form_viol and not a.force:
    import sys
    print('EDL NOT WRITTEN: fix the plan (or --force for a throw-away preview)')
    sys.exit(2)
json.dump(edl, open(a.out, 'w'), ensure_ascii=False, indent=1)
print('wrote', a.out)
