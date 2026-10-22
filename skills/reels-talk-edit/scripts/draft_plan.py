#!/usr/bin/env python3
"""Draft plan from the fused word table: auto caption chunks (filler-stripped) + speakers.
Claude then edits the draft (text cleanup, drops, hook, cards) -> plan.json (see SKILL.md 'plan.json').

usage: draft_plan.py words.json plan_draft.json [--max-chars 14] [--end-word N]
Chunk rules (numbers from his ep9 + research):
  break at: speaker change | sentence end (?.!) | pause > 0.30 s | comma when chunk >= 6 chars
  max 14 Hangul chars (no spaces) per caption (his median 12 incl. spaces, scorer max 18)
  overlong phrases are split at the most balanced word boundary
Fillers dropped from caption text (audio untouched): 음 어 엄 흠 뭐 그 막 이제 좀 약간 이렇게 그냥 (standalone words);
clause-initial glue dropped: 근데 그래서 그러니까 그러면 아니 실제로 아무래도 당연히 사실.
Output keys match build_edl (start_word/end_word/target_out/hook.until_t); Claude still rewrites every text
(endings, restarts, numbers) and the draft is never final.
"""
import argparse, json, re

FILLERS = {'음', '어', '엄', '흠', '뭐', '그', '막', '이제', '아', '응', '좀', '저기', '약간', '이렇게', '그냥'}
GLUE = {'근데', '그래서', '그러니까', '그러면', '아니', '실제로', '아무래도', '당연히', '사실'}
ap = argparse.ArgumentParser()
ap.add_argument('words')
ap.add_argument('out')
ap.add_argument('--max-chars', type=int, default=14)
ap.add_argument('--end-word', type=int)
a = ap.parse_args()
W = json.load(open(a.words))['words']
if a.end_word is not None:
    W = W[:a.end_word + 1]


def clen(ws):
    return sum(len(re.sub(r'[\s,.?!]', '', w['w'])) for w in ws)


chunks, cur = [], []
for w in W:
    if cur:
        p = cur[-1]
        brk = (w['spk'] != p['spk'] or re.search(r'[?.!]$', p['w']) or w['start'] - p['end'] > 0.30
               or (p['w'].endswith(',') and clen(cur) >= 6) or clen(cur + [w]) > a.max_chars)
        if brk:
            chunks.append(cur)
            cur = []
    cur.append(w)
if cur:
    chunks.append(cur)


def clean(ws):
    toks = [re.sub(r'[,.]$', '', w['w']) for w in ws]
    out = [t for t in toks if t not in FILLERS]
    while out and out[0] in GLUE:
        out = out[1:]
    # collapse immediate repeats (stutter): "그치 그치" kept (meaningful), "이런 이런" -> "이런"
    res = []
    for t in out:
        if res and res[-1] == t and t not in ('그치',):
            continue
        res.append(t)
    return ' '.join(res)


caps = []
for ch in chunks:
    txt = clean(ch)
    caps.append(dict(w=[ch[0]['i'], ch[-1]['i']], speaker=ch[0]['spk'], text=txt,
                     raw=' '.join(w['w'] for w in ch), src=[round(ch[0]['start'], 2), round(ch[-1]['end'], 2)]))
caps = [c for c in caps if c['text']]
plan = dict(start_word=W[0]['i'], end_word=W[-1]['i'], target_out=88.0, drop=[], captions=caps,
            hook=dict(text='', until_t=None, min_dur=2.4, max_dur=3.0), cards=[])
json.dump(plan, open(a.out, 'w'), ensure_ascii=False, indent=1)
for c in caps:
    print(f"{c['w'][0]:4d}-{c['w'][1]:4d} {c['speaker'][0].upper()} {c['src'][0]:7.2f} | {c['text']:<24} | {c['raw']}")
