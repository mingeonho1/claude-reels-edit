#!/usr/bin/env python3
"""Overlay asset generation (PIL + numpy only; runs on the device's python3.10 too).
All geometry is specified on the 2160x3840 canvas (style.json) and scaled by s = H/3840.
Assets are deterministic: same EDL + height -> byte-identical PNG/MOV files, so 4K chunks and 720p previews match.
"""
import json, os, subprocess, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.normpath(os.path.join(HERE, '..', 'assets'))

DEFAULT_STYLE = {
    "font": "DoHyeon-Regular.ttf", "fallback": "Pretendard-ExtraBold.otf",
    "caption": {"size": 110, "box_h": 175, "radius": 35, "pad_x": 26, "cx": 1080,
                "host": {"top": 2146, "color": [0, 0, 0]}, "guest": {"top": 2373, "color": [37, 41, 115]},
                "max_w": 1900},
    "header": {"line1": "01년생 AI 3년차 개발자와 Sydney Uni 금융 경제", "line2": "고품격 힐링 토크쇼",
               "l1_glyph_h": 77, "l1_top": 533, "l1_w": 1473, "l2_glyph_h": 117, "l2_top": 649, "l2_w": 979, "l2_bold": 3, "color": [0, 0, 0]},
    "hook": {"glyph_h": 260, "cy": 708, "max_w": 1700, "stroke": 7, "fill": [0, 0, 0], "stroke_fill": [255, 255, 255],
             "fly_px": 170, "fly_s": 0.5,
             "intro1": "AI 3년차 개발자와 Sydney Uni 금융 경제", "intro2": "고품격 힐링 토크쇼",
             "intro1_glyph_h": 77, "intro1_cy": 2239, "intro1_w": 1490, "intro2_glyph_h": 117, "intro2_cy": 2438, "intro2_w": 1167},
    "english": {"size": 68, "min_size": 50, "color": [236, 236, 236], "shadow": [0, 2, 200, 4], "stroke": 3, "stroke_color": [45, 45, 45], "gap": -6, "max_w": 1900},
    "character": {"gif": "sydney-friend-explaining.gif", "width": 1041, "cx": 1828, "cy": 2375},
    "card": {"radius": 40, "title_size": 104, "line_size": 92, "accent_size": 128, "title_color": [38, 42, 120],
             "accent_color": [214, 58, 58], "down_color": [36, 92, 196], "text_color": [30, 30, 30], "pad": 54, "w": 1060, "right_margin": 110,
             "top": 880, "enter_frames": 6, "exit_frames": 5},
}


# 16:9 two-shot (both people on camera, ep11): canvas 3840x2160, s = H/2160. Captions centred in the lower half,
# kept off the bottom 15 %; header/hook top-left of centre, clear of the host's head on the right. After a clockwise
# rotation (rotate: clock) the top edge sits on the phone's right side, so the header stays above Instagram's
# right-hand buttons. No guest character (the guest is on screen).
LANDSCAPE_STYLE = {
    "caption": {"cx": 1920, "host": {"top": 1330, "color": [0, 0, 0]}, "guest": {"top": 1550, "color": [37, 41, 115]},
                "max_w": 2600},
    "header": {"cx": 1350, "l1_top": 80, "l1_w": 1100, "l2_top": 170, "l2_w": 730},
    "hook": {"cx": 1350, "cy": 260, "max_w": 1500},
    "english": {"max_w": 2400},
    "card": {"top": 260, "right_margin": 140},
}


def merged_style(style, base=None):
    out = json.loads(json.dumps(DEFAULT_STYLE))
    for src in (base, style):
        for k, v in (src or {}).items():
            if isinstance(v, dict) and k in out:
                for kk, vv in v.items():
                    if isinstance(vv, dict) and isinstance(out[k].get(kk), dict):
                        out[k][kk].update(vv)
                    else:
                        out[k][kk] = vv
            else:
                out[k] = v
    return out


class Text:
    """Do Hyeon with per-glyph fallback (Do Hyeon only has KS X 1001 Hangul; no '·', arrows...)."""
    _cache = {}

    def __init__(self, size, style):
        self.size = size
        fp = os.path.join(ASSETS, style['font'])
        fb = os.path.join(ASSETS, style['fallback'])
        self.f = ImageFont.truetype(fp, int(round(size)))
        self.fb = ImageFont.truetype(fb, int(round(size * 0.92)))
        key = (fp, int(round(size)))
        if key not in Text._cache:
            Text._cache[key] = {}
        self.has_cache = Text._cache[key]
        self.notdef = self._raster(chr(0xE000))

    def _raster(self, ch):
        n = int(self.size * 1.6) + 4
        im = Image.new('L', (n, n), 0)
        ImageDraw.Draw(im).text((2, 2), ch, font=self.f, fill=255)
        return im.tobytes()

    def has(self, ch):
        if ch == ' ':
            return True
        if ch not in self.has_cache:
            r = self._raster(ch)
            self.has_cache[ch] = (any(r) and r != self.notdef)
        return self.has_cache[ch]

    def font_for(self, ch):
        return self.f if self.has(ch) else self.fb

    def width(self, s):
        return sum(self.font_for(ch).getlength(ch) for ch in s)

    def hangul_extent(self):
        b = self.f.getbbox('가', anchor='ls')
        return b[1], b[3]  # top (negative), bottom relative to baseline

    def draw(self, draw, x, baseline, s, fill, stroke=0, stroke_fill=None):
        for ch in s:
            f = self.font_for(ch)
            draw.text((x, baseline), ch, font=f, fill=fill, anchor='ls', stroke_width=int(round(stroke)),
                      stroke_fill=stroke_fill)
            x += f.getlength(ch)
        return x


def glyph_ratio(style):
    t = Text(200, style)
    a, b = t.hangul_extent()
    return (b - a) / 200.0


def size_for_glyph(h, style):
    return h / glyph_ratio(style)


def render_text_rgba(s, size, style, fill, stroke=0, stroke_fill=(0, 0, 0), ss=2, shadow=None):
    """Return (RGBA image, baseline_y_in_image, hangul_top, hangul_bottom) at final scale (rendered at ss x)."""
    t = Text(size * ss, style)
    w = int(math.ceil(t.width(s))) + int(4 * stroke * ss) + 8 * ss
    top, bot = t.hangul_extent()
    asc = int(-top + 0.35 * size * ss + stroke * ss * 2)
    h = asc + int(bot + 0.30 * size * ss + stroke * ss * 2)
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    x0 = 2 * stroke * ss + 4 * ss
    if shadow:
        sh = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        ds = ImageDraw.Draw(sh)
        t.draw(ds, x0 + shadow[0] * ss, asc + shadow[1] * ss, s, fill=(0, 0, 0, shadow[2]), stroke=stroke * ss, stroke_fill=(0, 0, 0, shadow[2]))
        sh = sh.filter(ImageFilter.GaussianBlur(shadow[3] * ss))
        im = Image.alpha_composite(im, sh)
        d = ImageDraw.Draw(im)
    t.draw(d, x0, asc, s, fill=tuple(fill) + (255,), stroke=stroke * ss, stroke_fill=tuple(stroke_fill) + (255,) if stroke else None)
    im = im.resize((max(1, w // ss), max(1, h // ss)), Image.LANCZOS)
    return im, asc / ss, (asc + top) / ss, (asc + bot) / ss


def even(v):
    return int(round(v / 2.0)) * 2


def caption_png(text, speaker, st, s, path):
    C = st['caption']
    ss = 3 if s < 0.5 else 2
    size = C['size'] * s
    t = Text(size * ss, st)
    tw = t.width(text)
    max_w = C['max_w'] * s * ss
    if tw + 2 * C['pad_x'] * s * ss > max_w:  # shrink to fit one line (rule: one line only)
        size *= max_w / (tw + 2 * C['pad_x'] * s * ss)
        t = Text(size * ss, st)
        tw = t.width(text)
    bh = C['box_h'] * s * ss
    bw = tw + 2 * C['pad_x'] * s * ss
    im = Image.new('RGBA', (int(math.ceil(bw)), int(math.ceil(bh))), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, im.size[0] - 1, im.size[1] - 1], radius=C['radius'] * s * ss, fill=(255, 255, 255, 255))
    top, bot = t.hangul_extent()
    baseline = bh / 2 - (top + bot) / 2
    t.draw(d, C['pad_x'] * s * ss, baseline, text, fill=tuple(C[speaker]['color']) + (255,))
    W = max(2, even(im.size[0] / ss))
    H = max(2, even(im.size[1] / ss))
    im = im.resize((W, H), Image.LANCZOS)
    im.save(path)
    x = even(C['cx'] * s - W / 2)
    y = even(C[speaker]['top'] * s)
    return dict(png=path, x=x, y=y, w=W, h=H)


def english_png(text, st, s, path, box, above=False):
    """English line under (or above) its Korean box: Do Hyeon 68 px @4K, light grey, soft shadow, no box
    (his approved style from the reels-english-subtitles pass)."""
    E = st['english']
    size = E['size']
    while True:
        im, base, top, bot = render_text_rgba(text, size * s, st, E['color'], stroke=max(1, round(E.get('stroke', 3) * s)) if E.get('stroke', 3) else 0,
                                              stroke_fill=tuple(E.get('stroke_color', [45, 45, 45])),
                                              shadow=tuple(E['shadow'][:3]) + (E['shadow'][3] * s * 2,))
        if im.size[0] <= E['max_w'] * s or size <= E['min_size']:
            break
        size -= 2
    W, H = even(im.size[0]), even(im.size[1])
    im = im.resize((W, H), Image.LANCZOS)
    im.save(path)
    x = even(box['x'] + box['w'] / 2 - W / 2)
    # glyph cap-top / baseline offsets inside the PNG
    if above:
        y = even(box['y'] - E['gap'] * s - bot)
    else:
        y = even(box['y'] + box['h'] + E['gap'] * s - top + 0.10 * size * s)
    return dict(png=path, x=x, y=y, w=W, h=H, size=size)


def header_png(st, s, W, path):
    Hd = st['header']
    canvas_h = int((Hd['l2_top'] + Hd['l2_glyph_h'] + 60) * s)
    im = Image.new('RGBA', (W, canvas_h), (0, 0, 0, 0))
    for key, top, gh, tw, bold in (('line1', Hd['l1_top'], Hd['l1_glyph_h'], Hd.get('l1_w'), 0),
                                   ('line2', Hd['l2_top'], Hd['l2_glyph_h'], Hd.get('l2_w'), Hd['l2_bold'])):
        size = size_for_glyph(gh * s, st)
        # dark backgrounds (stage footage): 'outline' adds a contrasting stroke + soft shadow around the header
        ol = Hd.get('outline')
        def _r(sz):
            if ol:
                return render_text_rgba(Hd[key], sz, st, Hd['color'], stroke=(bold + ol['width']) * s,
                                        stroke_fill=tuple(ol['color']), shadow=(0, 4 * s, 120, 6 * s))
            return render_text_rgba(Hd[key], sz, st, Hd['color'], stroke=bold * s, stroke_fill=Hd['color'])
        li, base, ht, hb = _r(size)
        if tw:  # measured span of his header wins over glyph height (Latin/digits make Do Hyeon run wide)
            size *= tw * s / li.size[0]
            li, base, ht, hb = _r(size)
        x = int(round((Hd['cx'] * s if Hd.get('cx') else W / 2) - li.size[0] / 2))
        y = int(round(top * s - ht))
        im.alpha_composite(li, (max(0, x), max(0, y)))
    y0 = int(Hd['l1_top'] * s * 0.8) // 2 * 2
    im = im.crop((0, y0, W, canvas_h - (canvas_h - y0) % 2))
    im.save(path)
    return dict(png=path, x=0, y=y0)


def hook_assets(text, st, s, W, outdir, fps=30):
    Hk = st['hook']
    size = size_for_glyph(Hk['glyph_h'] * s, st)

    def one(tx, sz):
        return render_text_rgba(tx, sz, st, Hk['fill'], stroke=Hk['stroke'] * s, stroke_fill=Hk['stroke_fill'],
                                shadow=(0, 6 * s, 90, 8 * s))
    lines_ = text.split('\n')
    rr = [one(tx, size) for tx in lines_]
    widest = max(r[0].size[0] for r in rr)
    if widest > Hk['max_w'] * s:   # one size for every line, set by the widest
        size *= Hk['max_w'] * s / widest
        rr = [one(tx, size) for tx in lines_]
    if len(rr) == 1:
        li, base, ht, hb = rr[0]
    else:                           # stacked, centred, line pitch 1.18 x glyph height
        gh = rr[0][3] - rr[0][2]
        pitch = gh * Hk.get('line_pitch', 1.18)
        wmax = max(r[0].size[0] for r in rr)
        hh = int(pitch * (len(rr) - 1) + max(r[0].size[1] for r in rr)) + 2
        li = Image.new('RGBA', (wmax, hh), (0, 0, 0, 0))
        for j, r in enumerate(rr):
            li.alpha_composite(r[0], ((wmax - r[0].size[0]) // 2, int(round(j * pitch))))
        ht = rr[0][2]
        hb = rr[-1][3] + pitch * (len(rr) - 1)
    x = even((Hk['cx'] * s if Hk.get('cx') else W / 2) - li.size[0] / 2)
    y = even(Hk['cy'] * s - (ht + hb) / 2)
    # fly-up animation frames: easeOutCubic offset + alpha fade, then static (last frame repeats)
    n = max(1, int(round(Hk['fly_s'] * fps)))
    pad = int(Hk['fly_px'] * s) // 2 * 2
    frames_dir = os.path.join(outdir, 'hook_frames')
    os.makedirs(frames_dir, exist_ok=True)
    fw, fh = even(li.size[0] + 2), even(li.size[1] + pad + 2)
    for i in range(n + 1):
        p = min(1.0, i / n)
        e = 1 - (1 - p) ** 3
        off = int(round((1 - e) * pad))
        a = min(1.0, p / 0.5)
        fr = Image.new('RGBA', (fw, fh), (0, 0, 0, 0))
        tmp = li.copy()
        tmp.putalpha(tmp.getchannel('A').point(lambda v: int(v * a)))
        fr.alpha_composite(tmp, (0, off))
        fr.save(os.path.join(frames_dir, f'{i:04d}.png'))
    mov = os.path.join(outdir, 'hook.mov')
    png_mov(frames_dir, mov, fps)
    intro = Image.new('RGBA', (W, int(Hk['intro2_cy'] * s - Hk['intro1_cy'] * s + 2 * Hk['intro2_glyph_h'] * s) // 2 * 2), (0, 0, 0, 0))
    iy0 = even(Hk['intro1_cy'] * s - Hk['intro1_glyph_h'] * s * 1.2)
    for key, cy, gh in (('intro1', Hk['intro1_cy'], Hk['intro1_glyph_h']), ('intro2', Hk['intro2_cy'], Hk['intro2_glyph_h'])):
        if not Hk.get(key):
            continue
        sz = size_for_glyph(gh * s, st)
        im2, b2, t2, h2 = render_text_rgba(Hk[key], sz, st, (255, 255, 255), stroke=max(1, 5 * s), stroke_fill=(20, 20, 20),
                                           shadow=(0, 4 * s, 110, 6 * s))
        if Hk.get(key + '_w'):
            sz *= Hk[key + '_w'] * s / im2.size[0]
            im2, b2, t2, h2 = render_text_rgba(Hk[key], sz, st, (255, 255, 255), stroke=max(1, 5 * s), stroke_fill=(20, 20, 20),
                                               shadow=(0, 4 * s, 110, 6 * s))
        intro.alpha_composite(im2, (max(0, int(W / 2 - im2.size[0] / 2)), max(0, int(cy * s - (t2 + h2) / 2 - iy0))))
    ip = os.path.join(outdir, 'intro.png')
    intro.save(ip)
    return dict(mov=mov, x=x, y=y, frames=n + 1), dict(png=ip, x=0, y=iy0)


def png_mov(frames_dir, mov, fps):
    subprocess.run([os.environ.get('FFMPEG', 'ffmpeg'), '-v', 'error', '-y', '-framerate', str(fps), '-i', os.path.join(frames_dir, '%04d.png'),
                    '-c:v', 'png', '-pix_fmt', 'rgba', mov], check=True)


def character_assets(st, s, outdir, fps=30):
    Ch = st['character']
    gif = Image.open(os.path.join(ASSETS, Ch['gif']))
    frames, durs = [], []
    try:
        while True:
            frames.append(gif.convert('RGBA').copy())
            durs.append(gif.info.get('duration', 80) or 80)
            gif.seek(gif.tell() + 1)
    except EOFError:
        pass
    period = sum(durs) / 1000.0
    n = int(round(period * fps))
    w = even(Ch['width'] * s)
    h = even(frames[0].size[1] * w / frames[0].size[0])
    cum = np.cumsum([0] + durs) / 1000.0
    fd = os.path.join(outdir, 'char_frames')
    os.makedirs(fd, exist_ok=True)
    cache = {}
    for i in range(n):
        t = i / fps
        k = int(np.searchsorted(cum, t, side='right') - 1) % len(frames)
        if k not in cache:
            cache[k] = frames[k].resize((w, h), Image.LANCZOS)
        cache[k].save(os.path.join(fd, f'{i:04d}.png'))
    mov = os.path.join(outdir, 'char.mov')
    png_mov(fd, mov, fps)
    return dict(mov=mov, x=even(Ch['cx'] * s - w / 2), y=even(Ch['cy'] * s - h / 2), period_frames=n, w=w, h=h)


def wrap(text, t, maxw):
    words, lines, cur = text.split(' '), [], ''
    for wd in words:
        nxt = (cur + ' ' + wd).strip()
        if t.width(nxt) <= maxw or not cur:
            cur = nxt
        else:
            lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    return lines


DOWN_WORDS = ('부족', '감소', '하락', '덜', '줄', '손실', '적자', '빠지', '↓', '▼', '-')
UP_WORDS = ('증가', '상승', '오르', '올라', '늘', '흑자', '↑', '▲', '+')


def accent_dir(card):
    """'up' | 'down' | '' - the arrow must follow the sign of the number (never ▲ next to 부족)."""
    d = card.get('dir', 'auto')
    if d in ('up', 'down', 'none'):
        return '' if d == 'none' else d
    a = card.get('accent', '')
    dn = any(k in a for k in DOWN_WORDS)
    up = any(k in a for k in UP_WORDS)
    return 'down' if dn and not up else 'up' if up and not dn else ''


def card_assets(card, idx, st, s, W, H, face, outdir, fps=30):
    Cd = st['card']
    ss = 2
    cw = Cd['w'] * s
    if face:  # place on the side away from the face, right side preferred
        fx, fy, fw, fh = face
        right_space = W - Cd['right_margin'] * s - (fx + fw) * W - 40 * s
        left_space = fx * W - Cd['right_margin'] * s - 40 * s
        side = 'right' if right_space >= 0.85 * cw or right_space >= left_space else 'left'
        avail = right_space if side == 'right' else left_space
        cw = max(760 * s, min(cw, avail))
    else:
        side = 'right'
    pad = Cd['pad'] * s
    tt = Text(Cd['title_size'] * s * ss, st)
    tl = Text(Cd['line_size'] * s * ss, st)
    ta = Text(Cd['accent_size'] * s * ss, st)
    inner = (cw - 2 * pad) * ss
    rows = []  # (Text, string, color, gap_after)
    def fit(text, t_, size):
        # shrink a line that is slightly too wide (down to 85 %, so body text stays >= 78 px at 4K) before wrapping
        w_ = t_.width(text)
        if w_ <= inner:
            return t_
        return Text(size * s * ss * max(0.85, inner / w_), st)

    tt = fit(card['title'], tt, Cd['title_size'])
    for ln in wrap(card['title'], tt, inner):
        rows.append((tt, ln, Cd['title_color'], 14 * s * ss))
    rows.append((None, '', None, 10 * s * ss))
    for line in card.get('lines', []):
        tl_ = fit(line, tl, Cd['line_size'])
        for ln in wrap(line, tl_, inner):
            rows.append((tl_, ln, Cd['text_color'], 12 * s * ss))
    if card.get('accent'):
        dr = accent_dir(card)
        acc = card['accent'].lstrip('▲▼↑↓ ')
        acc = ('▲ ' if dr == 'up' else '▼ ' if dr == 'down' else '') + acc
        acol = Cd.get('down_color', Cd['accent_color']) if dr == 'down' else Cd['accent_color']
        rows.append((None, '', None, 8 * s * ss))
        ta = fit(acc, ta, Cd['accent_size'])
        for ln in wrap(acc, ta, inner):
            rows.append((ta, ln, acol, 8 * s * ss))
    hh = 2 * pad * ss
    for t_, ln, c, g in rows:
        if t_:
            a, b = t_.hangul_extent()
            hh += (b - a) * 1.25
        hh += g
    bw, bh = int(cw * ss), int(hh)
    shadow = int(30 * s * ss)
    im = Image.new('RGBA', (bw + 2 * shadow, bh + 2 * shadow), (0, 0, 0, 0))
    sh = Image.new('RGBA', im.size, (0, 0, 0, 0))
    ImageDraw.Draw(sh).rounded_rectangle([shadow, shadow + 8 * s * ss, shadow + bw, shadow + bh + 8 * s * ss],
                                         radius=Cd['radius'] * s * ss, fill=(0, 0, 0, 70))
    sh = sh.filter(ImageFilter.GaussianBlur(14 * s * ss))
    im.alpha_composite(sh)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([shadow, shadow, shadow + bw, shadow + bh], radius=Cd['radius'] * s * ss, fill=(255, 255, 255, 255))
    # red accent bar on the left edge of the title
    y = shadow + pad * ss
    d.rounded_rectangle([shadow + pad * ss * 0.45, y + 4 * s * ss, shadow + pad * ss * 0.45 + 8 * s * ss,
                         y + (Cd['title_size'] * s * ss)], radius=4 * s * ss, fill=tuple(Cd['accent_color']) + (255,))
    for t_, ln, c, g in rows:
        if t_:
            a, b = t_.hangul_extent()
            lh = (b - a) * 1.25
            t_.draw(d, shadow + pad * ss, y - a + (lh - (b - a)) / 2, ln, fill=tuple(c) + (255,))
            y += lh
        y += g
    im = im.resize((even(im.size[0] / ss), even(im.size[1] / ss)), Image.LANCZOS)
    x = W - Cd['right_margin'] * s - cw - shadow / ss if side == 'right' else Cd['right_margin'] * s - shadow / ss
    yy = Cd['top'] * s - shadow / ss
    # animation frames over the card's whole duration (enter easeOutBack 0.9->1 + fade, exit fade)
    n = int(round((card['out_end'] - card['out_start']) * fps))
    ne, nx = Cd['enter_frames'], Cd['exit_frames']
    fd = os.path.join(outdir, f'card{idx}_frames')
    os.makedirs(fd, exist_ok=True)
    cw_, ch_ = im.size
    hold_written = None
    for i in range(n):
        if i < ne:
            p = (i + 1) / ne
            c1, c3 = 1.70158, 2.70158
            e = 1 + c3 * (p - 1) ** 3 + c1 * (p - 1) ** 2
            sc, al = 0.9 + 0.1 * e, p
        elif i >= n - nx:
            sc, al = 1.0, (n - i - 1) / nx
        else:
            sc, al = 1.0, 1.0
        fp = os.path.join(fd, f'{i:04d}.png')
        if sc == 1.0 and al == 1.0:
            if hold_written is None:
                im.save(fp)
                hold_written = fp
            else:
                os.link(hold_written, fp) if not os.path.exists(fp) else None
            continue
        fr = Image.new('RGBA', (cw_, ch_), (0, 0, 0, 0))
        tmp = im.resize((max(2, int(cw_ * sc)), max(2, int(ch_ * sc))), Image.LANCZOS)
        tmp.putalpha(tmp.getchannel('A').point(lambda v: int(v * max(0.0, min(1.0, al)))))
        fr.alpha_composite(tmp, ((cw_ - tmp.size[0]) // 2, (ch_ - tmp.size[1]) // 2))
        fr.save(fp)
    mov = os.path.join(outdir, f'card{idx}.mov')
    png_mov(fd, mov, fps)
    return dict(mov=mov, x=even(x), y=even(yy), frames=n, side=side, w=cw_, h=ch_)


# ------------------------------------------------------------------ panel cards (montage / recap reels, ep12)
# A full-width information panel whose rows reveal on a schedule (seconds from the card start). Used when the
# screen is B-roll and the panel *is* the content: ladders, checklists, a crossed-out question, a definition.
# Geometry in 2160x3840 canvas px, scaled by s. Row types:
#   title {text,size}            text {text,size,color,align}      big {text,size,color,align}
#   strike {text,size,strike_at} bar {label,pct,color,hi_at,hi_color}   check {text,check_at}
#   src {text}                   gap {h}
# Every row may carry 'at' (reveal time, default 0) and 'hi_at'/'hi_color' (colour change).
PANEL = {"w": 1940, "top": 900, "pad": 70, "radius": 44, "bg": [255, 255, 255], "bg_alpha": 0.95,
         "title_size": 96, "text_size": 84, "big_size": 132, "src_size": 50, "row_gap": 30,
         "title_color": [38, 42, 120], "text_color": [30, 30, 30], "accent_color": [214, 58, 58], "dim_color": [150, 150, 150],
         "bar_color": [38, 42, 120], "bar_bg": [232, 232, 238], "enter_frames": 6, "exit_frames": 5, "reveal_frames": 4, "bar_fill_s": 0.35}


def panel_assets(card, idx, st, s, W, H, outdir, fps=30):
    P = dict(PANEL)
    P.update(st.get('panel', {}))
    P.update({k: v for k, v in card.items() if k in PANEL})
    ss = 2
    k = s * ss
    pw = P['w'] * k
    pad = P['pad'] * k
    inner = pw - 2 * pad
    rows = []   # dict(kind, y, h, draw-data)
    y = pad
    for it in card['items']:
        t = it['t']
        at = float(it.get('at', 0.0))
        if t == 'gap':
            y += it.get('h', 30) * k
            continue
        if t in ('title', 'text', 'big', 'strike', 'src', 'check'):
            size = it.get('size', P[{'title': 'title_size', 'big': 'big_size', 'src': 'src_size'}.get(t, 'text_size')])
            tx = Text(size * k, st)
            avail = inner - (size * k * 1.25 if t == 'check' else 0)
            lines = wrap(it['text'], tx, avail)
            a, b = tx.hangul_extent()
            lh = (b - a) * (1.32 if t != 'big' else 1.22)
            col = it.get('color') or (P['title_color'] if t == 'title' else P['accent_color'] if t == 'big'
                                      else P['dim_color'] if t == 'src' else P['text_color'])
            rows.append(dict(kind=t, y=y, h=lh * len(lines), lines=lines, tx=tx, lh=lh, a=a, b=b, col=col, at=at, it=it,
                             align=it.get('align', 'center' if t == 'big' else 'left'), size=size))
            y += lh * len(lines) + P['row_gap'] * k
        elif t == 'bar':
            size = it.get('size', P['text_size'])
            tx = Text(size * k, st)
            a, b = tx.hangul_extent()
            lh = (b - a) * 1.5
            sub = None
            if it.get('sub'):
                sub = Text(it.get('sub_size', 64) * k, st)
                sa, sb = sub.hangul_extent()
                slh = (sb - sa) * 1.35
            else:
                slh = 0
            rows.append(dict(kind='bar', y=y, h=lh + slh, tx=tx, lh=lh, a=a, b=b, at=at, it=it, size=size, sub=sub, slh=slh))
            y += lh + slh + P['row_gap'] * k
        elif t == 'eq':   # left term + multi-line right side ("AX 인재 = | line1 / line2")
            ls_ = it.get('left_size', P['big_size'])
            rs_ = it.get('size', P['big_size'] * 0.85)
            tl_ = Text(ls_ * k, st)
            tr_ = Text(rs_ * k, st)
            la, lb = tl_.hangul_extent()
            ra_, rb_ = tr_.hangul_extent()
            rlh = (rb_ - ra_) * 1.25
            lw = tl_.width(it['left']) + 36 * k
            rlines = []
            for ln in it['right']:
                rlines += wrap(ln, tr_, inner - lw)
            hh = max((lb - la) * 1.25, rlh * len(rlines))
            rows.append(dict(kind='eq', y=y, h=hh, tl=tl_, tr=tr_, la=la, lb=lb, ra=ra_, rb=rb_, rlh=rlh, lw=lw,
                             rlines=rlines, at=at, it=it))
            y += hh + P['row_gap'] * k
    y += pad - P['row_gap'] * k
    ph = y
    shadow = int(30 * k)
    CW, CH = int(pw + 2 * shadow), int(ph + 2 * shadow)
    base = Image.new('RGBA', (CW, CH), (0, 0, 0, 0))
    shd = Image.new('RGBA', base.size, (0, 0, 0, 0))
    ImageDraw.Draw(shd).rounded_rectangle([shadow, shadow + 8 * k, shadow + pw, shadow + ph + 8 * k], radius=P['radius'] * k,
                                          fill=(0, 0, 0, 80))
    shd = shd.filter(ImageFilter.GaussianBlur(14 * k))
    base.alpha_composite(shd)
    ImageDraw.Draw(base).rounded_rectangle([shadow, shadow, shadow + pw, shadow + ph], radius=P['radius'] * k,
                                           fill=tuple(P['bg']) + (int(255 * P['bg_alpha']),))

    def draw_row(im, r, alpha, now):
        layer = Image.new('RGBA', im.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(layer)
        it = r['it']
        hi = it.get('hi_at') is not None and now >= it['hi_at']
        x0 = shadow + pad
        if r['kind'] == 'eq':
            yy = shadow + r['y']
            lcol = tuple(it.get('left_color', P['title_color']))
            rcol = tuple(it.get('color', P['accent_color']))
            bl = yy + r['h'] / 2 - (r['la'] + r['lb']) / 2
            r['tl'].draw(d, x0, bl, it['left'], fill=lcol + (255,))
            ra_at = it.get('right_at', r['at'])
            if now >= ra_at:
                ry = yy + (r['h'] - r['rlh'] * len(r['rlines'])) / 2
                for ln in r['rlines']:
                    r['tr'].draw(d, x0 + r['lw'], ry + r['rlh'] / 2 - (r['ra'] + r['rb']) / 2, ln, fill=rcol + (255,))
                    ry += r['rlh']
        elif r['kind'] == 'bar':
            col = tuple(it.get('hi_color', P['accent_color']) if hi else it.get('color', P['bar_color']))
            lab_w = inner * it.get('label_frac', 0.56)
            yb = shadow + r['y'] + r['lh'] / 2 - (r['a'] + r['b']) / 2
            r['tx'].draw(d, x0, yb, it['label'], fill=col + (255,))
            if r.get('sub'):
                sa, sb = r['sub'].hangul_extent()
                sy = shadow + r['y'] + r['lh'] + r['slh'] / 2 - (sa + sb) / 2 - 6 * k
                r['sub'].draw(d, x0, sy, it['sub'], fill=tuple(it.get('sub_color', [90, 90, 90])) + (255,))
            bx0 = x0 + lab_w
            bx1 = shadow + pad + inner - 190 * k
            bh = (r['b'] - r['a']) * 0.95
            by = shadow + r['y'] + r['lh'] / 2 - bh / 2
            d.rounded_rectangle([bx0, by, bx1, by + bh], radius=bh / 2, fill=tuple(P['bar_bg']) + (255,))
            prog = min(1.0, max(0.0, (now - r['at']) / P['bar_fill_s']))
            prog = 1 - (1 - prog) ** 3
            fw = max(bh, (bx1 - bx0) * it['pct'] / 100.0 * prog)
            d.rounded_rectangle([bx0, by, bx0 + fw, by + bh], radius=bh / 2, fill=col + (255,))
            r['tx'].draw(d, bx1 + 24 * k, yb, f"{it['pct']:g}%", fill=col + (255,))
        else:
            col = tuple(it.get('hi_color', P['accent_color']) if hi else r['col'])
            yy = shadow + r['y']
            for ln in r['lines']:
                w_ = r['tx'].width(ln)
                if r['kind'] == 'check':
                    bs = (r['b'] - r['a']) * 0.95
                    by = yy + r['lh'] / 2 - bs / 2
                    d.rounded_rectangle([x0, by, x0 + bs, by + bs], radius=bs * 0.18, outline=col + (255,), width=max(2, int(6 * k)))
                    if it.get('check_at') is not None and now >= it['check_at']:
                        d.line([(x0 + bs * 0.18, by + bs * 0.52), (x0 + bs * 0.42, by + bs * 0.78), (x0 + bs * 0.86, by + bs * 0.2)],
                               fill=tuple(P['accent_color']) + (255,), width=max(3, int(12 * k)), joint='curve')
                    xt = x0 + bs * 1.3
                else:
                    xt = x0 + (inner - w_) / 2 if r['align'] == 'center' else x0
                bl = yy + r['lh'] / 2 - (r['a'] + r['b']) / 2
                r['tx'].draw(d, xt, bl, ln, fill=col + (255,))
                if r['kind'] == 'strike' and it.get('strike_at') is not None and now >= it['strike_at']:
                    sp = min(1.0, (now - it['strike_at']) / 0.35)
                    ym = bl + (r['a'] + r['b']) / 2
                    d.line([(xt - 10 * k, ym), (xt - 10 * k + (w_ + 20 * k) * sp, ym)], fill=tuple(P['accent_color']) + (255,),
                           width=max(3, int(10 * k)))
                yy += r['lh']
        if alpha < 1.0:
            layer.putalpha(layer.getchannel('A').point(lambda v: int(v * alpha)))
        off = int(round((1 - alpha) * 24 * k))
        im.alpha_composite(layer, (0, off))

    n = int(round((card['out_end'] - card['out_start']) * fps))
    ne, nx, nr = P['enter_frames'], P['exit_frames'], P['reveal_frames']
    fd = os.path.join(outdir, f'card{idx}_frames')
    os.makedirs(fd, exist_ok=True)
    cache = {}
    for i in range(n):
        now = i / fps
        sig = []
        for r in rows:
            p = ((now - r['at']) * fps + 1) / nr if now >= r['at'] - 1e-6 else 0.0
            al = round(min(1.0, max(0.0, p)), 2)
            it = r['it']
            st_ = (al, it.get('hi_at') is not None and now >= it['hi_at'],
                   round(min(1.0, max(0.0, (now - r['at']) / P['bar_fill_s'])), 2) if r['kind'] == 'bar' else 0,
                   round(min(1.0, max(0.0, (now - it.get('strike_at', 1e9)) / 0.35)), 2) if r['kind'] == 'strike' else 0,
                   it.get('check_at') is not None and now >= it.get('check_at', 1e9),
                   now >= it.get('right_at', -1))
            sig.append(st_)
        if i < ne:
            pp = (i + 1) / ne
            c1, c3 = 1.70158, 2.70158
            e = 1 + c3 * (pp - 1) ** 3 + c1 * (pp - 1) ** 2
            sc, gal = 0.94 + 0.06 * e, pp
        elif i >= n - nx:
            sc, gal = 1.0, (n - i - 1) / nx
        else:
            sc, gal = 1.0, 1.0
        key = (tuple(sig), round(sc, 3), round(gal, 3))
        fp = os.path.join(fd, f'{i:04d}.png')
        if key in cache:
            if not os.path.exists(fp):
                os.link(cache[key], fp)
            continue
        im = base.copy()
        for r, sg in zip(rows, sig):
            if sg[0] > 0:
                draw_row(im, r, sg[0], now)
        im = im.resize((even(CW / ss), even(CH / ss)), Image.LANCZOS)
        if sc != 1.0 or gal != 1.0:
            fr = Image.new('RGBA', im.size, (0, 0, 0, 0))
            tmp = im.resize((max(2, int(im.size[0] * sc)), max(2, int(im.size[1] * sc))), Image.LANCZOS)
            tmp.putalpha(tmp.getchannel('A').point(lambda v: int(v * max(0.0, min(1.0, gal)))))
            fr.alpha_composite(tmp, ((im.size[0] - tmp.size[0]) // 2, (im.size[1] - tmp.size[1]) // 2))
            im = fr
        im.save(fp)
        cache[key] = fp
    mov = os.path.join(outdir, f'card{idx}.mov')
    png_mov(fd, mov, fps)
    w_, h_ = even(CW / ss), even(CH / ss)
    x = even(W / 2 - w_ / 2)
    yy = even(P['top'] * s - shadow / ss)
    return dict(mov=mov, x=x, y=yy, frames=n, side='center', w=w_, h=h_)
