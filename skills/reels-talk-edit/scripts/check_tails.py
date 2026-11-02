#!/usr/bin/env python3
"""Flag segment ends that may cut a word (ep13 2026-11-02: "말을 끝까지 끝내고 정우가 말하는 걸로 해야지").
usage: check_tails.py --edl edl.json --rms stt_rms10ms.npy --face face.npz [--words words.json]
For every segment end it reports
  MID  : the end sits on voiced energy (> floor + 12 dB)  -> the last syllable is chopped
  TAIL : (speaker changes only) a burst (> floor + 20 dB, >= 30 ms) follows within 0.25 s before the next kept speech, and (host segments)
         the on-camera mouth is still moving after the end -> the line may continue ('있지' -> '있지?')
Fix: `retime` the last word so build_edl's src_end lands on the dip after the tail (try a few values: output frames
quantise src_end in steps of speed/30 s), or trim the next speaker's onset with `mute_extra`. Then listen.
"""
import argparse, json, numpy as np
ap = argparse.ArgumentParser()
ap.add_argument('--edl', required=True); ap.add_argument('--rms', required=True); ap.add_argument('--face')
a = ap.parse_args()
db = np.load(a.rms); fl = float(np.percentile(db, 10)); H = 0.01
E = json.load(open(a.edl)); S = [s for s in E['segments'] if not s.get('cold')]
F = np.load(a.face) if a.face else None
def env(t): return db[min(len(db) - 1, max(0, int(round(t / H))))]
n = 0
for k, s in enumerate(S):
    t = s['src_end']
    msg = []
    if min(env(t - 0.01), env(t)) > fl + 14:
        msg.append('MID  end on voiced energy %.0f dB (floor %.0f)' % (min(env(t - 0.01), env(t)), fl))
    nxt = S[k + 1]['src_start'] if k + 1 < len(S) else t + 1.0
    lim = min(t + 0.25, nxt if nxt > t else t + 0.25)
    run = 0; best = 0
    for x in np.arange(t + 0.01, lim, H):
        run = run + 1 if env(x) > fl + 20 else 0; best = max(best, run)
    mouth = None
    if F is not None and s.get('host_frac', 0) >= 0.6:
        m = (F['t'] > t) & (F['t'] < t + 0.2)
        mouth = float(np.nanmean(F['score'][m])) if m.any() else None
    turn = k + 1 < len(S) and (s.get('host_frac', 0) >= 0.6) != (S[k + 1].get('host_frac', 0) >= 0.6)
    if turn and best >= 3 and (s.get('host_frac', 0) < 0.6 or (mouth is not None and mouth > 1.0)):
        msg.append('TAIL burst %d ms after the end%s' % (best * 10, '' if mouth is None else ', host mouth %.2f' % mouth))
    for m_ in msg:
        n += 1
        print('out %6.2f  src %7.2f  %s' % (s['out_end'], t, m_))
print('%d flag(s); listen to each (whisper [end-0.9, end+0.2]) before changing anything' % n)
