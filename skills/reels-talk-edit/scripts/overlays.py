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
    "character": {"gif": "character.gif", "width": 1041, "cx": 1828, "cy": 2375},
    "card": {"radius": 40, "title_size": 104, "line_size": 92, "accent_size": 128, "title_color": [38, 42, 120],
             "accent_color": [214, 58, 58], "down_color": [36, 92, 196], "text_color": [30, 30, 30], "pad": 54, "w": 1060, "right_margin": 110,
             "top": 880, "enter_frames": 8, "exit_frames": 6},
}


def merged_style(style):
    out = json.loads(json.dumps(DEFAULT_STYLE))
    for k, v in (style or {}).items():
        if isinstance(v, dict) and k in out:
            out[k].update(v)
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
        li, base, ht, hb = render_text_rgba(Hd[key], size, st, Hd['color'], stroke=bold * s, stroke_fill=Hd['color'])
        if tw:  # measured span of his header wins over glyph height (Latin/digits make Do Hyeon run wide)
            size *= tw * s / li.size[0]
            li, base, ht, hb = render_text_rgba(Hd[key], size, st, Hd['color'], stroke=bold * s, stroke_fill=Hd['color'])
        x = int(round(W / 2 - li.size[0] / 2))
        y = int(round(top * s - ht))
        im.alpha_composite(li, (max(0, x), max(0, y)))
    y0 = int(Hd['l1_top'] * s * 0.8) // 2 * 2
    im = im.crop((0, y0, W, canvas_h - (canvas_h - y0) % 2))
    im.save(path)
    return dict(png=path, x=0, y=y0)


def hook_assets(text, st, s, W, outdir, fps=30):
    Hk = st['hook']
    size = size_for_glyph(Hk['glyph_h'] * s, st)
    li, base, ht, hb = render_text_rgba(text, size, st, Hk['fill'], stroke=Hk['stroke'] * s, stroke_fill=Hk['stroke_fill'],
                                        shadow=(0, 6 * s, 90, 8 * s))
    if li.size[0] > Hk['max_w'] * s:
        size *= Hk['max_w'] * s / li.size[0]
        li, base, ht, hb = render_text_rgba(text, size, st, Hk['fill'], stroke=Hk['stroke'] * s, stroke_fill=Hk['stroke_fill'],
                                            shadow=(0, 6 * s, 90, 8 * s))
    x = even(W / 2 - li.size[0] / 2)
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
    gp = os.path.join(ASSETS, Ch['gif'])
    if not os.path.exists(gp):  # bring your own guest character (transparent GIF); legacy name kept as fallback
        gp = os.path.join(ASSETS, 'sydney-friend-explaining.gif')
    gif = Image.open(gp)
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
