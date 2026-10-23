#!/usr/bin/env python3
"""Readable cut list for the stage-1 approval: what is kept (with output timecodes) and what was dropped.
usage: cutlist.py --edl edl.json --words words.json --plan plan.json --out cutlist.md
"""
import argparse, json

ap = argparse.ArgumentParser()
ap.add_argument('--edl', required=True)
ap.add_argument('--words', required=True)
ap.add_argument('--plan', required=True)
ap.add_argument('--out', required=True)
a = ap.parse_args()
E = json.load(open(a.edl))
WJ = json.load(open(a.words))
W = WJ['words'] if isinstance(WJ, dict) else WJ
P = json.load(open(a.plan))


def fmt(t):
    return f"{int(t // 60)}:{t % 60:04.1f}"


lines = [f"# 컷 리스트 — 출력 {E['out_duration']:.1f}s, 세그먼트 {len(E['segments'])}개, 평균 배속 "
         f"{sum((s['src_end'] - s['src_start']) for s in E['segments']) / max(1e-6, E['out_duration']):.2f}x", "",
         "| 출력 | 원본 | 배속 | 화자 | 들리는 말 |", "|---|---|---|---|---|"]
for s in E['segments']:
    ws = [w for w in W if s['src_start'] - 0.02 <= (w['start'] + w['end']) / 2 <= s['src_end'] + 0.02]
    NM = P.get('names', {})
    spk = '/'.join(dict.fromkeys((NM.get('host', '나') if w['spk'] == 'host' else NM.get('guest', '정우')) for w in ws)) or '-'
    tag = ' (콜드오픈)' if s.get('cold') else ''
    lines.append(f"| {fmt(s['out_start'])}–{fmt(s['out_end'])}{tag} | {s['src_start']:.1f}–{s['src_end']:.1f} | "
                 f"{s['speed']:.2f} | {spk} | {' '.join(w['w'] for w in ws)} |")
lines += ["", "## 잘라낸 부분", "", "| 원본 | 이유 | 내용 |", "|---|---|---|"]
for d in P.get('drop', []):
    t0, t1 = d['t'] if 't' in d else (W[d['w'][0]]['start'], W[d['w'][1]]['end'])
    ws = [w['w'] for w in W if t0 <= (w['start'] + w['end']) / 2 <= t1]
    lines.append(f"| {t0:.1f}–{t1:.1f} | {d.get('why', '')} | {' '.join(ws)[:80]} |")
open(a.out, 'w').write('\n'.join(lines) + '\n')
print('wrote', a.out)
