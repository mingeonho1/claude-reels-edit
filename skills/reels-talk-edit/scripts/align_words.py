"""Align whisper text (good wording, no timing) to zipformer tokens (timing) at syllable level."""
import difflib


def syl(c):
    return '가' <= c <= '힣' or c.isalnum()


def align_words(wt, toks, s, e):
    zc = []
    zt = []
    for j, tk in enumerate(toks):
        t = tk['t'].replace('▁', '')
        nxt = toks[j + 1]['ts'] if j + 1 < len(toks) else tk['ts'] + 0.25
        cs = [c for c in t if syl(c)]
        for m, c in enumerate(cs):
            zc.append(c)
            zt.append(tk['ts'] + (nxt - tk['ts']) * m / max(1, len(cs)))
    wc = []
    wi = []
    ws = wt.split()
    for n, w in enumerate(ws):
        for c in w:
            if syl(c):
                wc.append(c)
                wi.append(n)
    tmap = [None] * len(wc)
    sm = difflib.SequenceMatcher(a=wc, b=zc, autojunk=False)
    for blk in sm.get_matching_blocks():
        for q in range(blk.size):
            tmap[blk.a + q] = zt[blk.b + q]
    known = [(i, t) for i, t in enumerate(tmap) if t is not None]
    ks = set(i for i, _ in known)
    if not known:
        known = [(0, s), (max(0, len(wc) - 1), e)]
    for i in range(len(tmap)):
        if tmap[i] is None:
            lo = max([k for k in known if k[0] < i], default=(None, None))
            hi = min([k for k in known if k[0] > i], default=(None, None))
            if lo[0] is None and hi[0] is None:
                tmap[i] = s
            elif lo[0] is None:
                tmap[i] = max(s, hi[1] - 0.15 * (hi[0] - i))
            elif hi[0] is None:
                tmap[i] = min(e, lo[1] + 0.15 * (i - lo[0]))
            else:
                tmap[i] = lo[1] + (hi[1] - lo[1]) * (i - lo[0]) / (hi[0] - lo[0])
    words = []
    for n, w in enumerate(ws):
        idx = [i for i, x in enumerate(wi) if x == n]
        if not idx:
            continue
        words.append(dict(w=w, start=round(tmap[idx[0]], 3), end=round(tmap[idx[-1]] + 0.18, 3),
                          matched=round(sum(1 for i in idx if i in ks) / len(idx), 2)))
    for a_, b_ in zip(words, words[1:]):
        if a_['end'] > b_['start']:
            a_['end'] = round(max(a_['start'] + 0.05, b_['start'] - 0.01), 3)
    return words
