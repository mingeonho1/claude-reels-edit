#!/usr/bin/env python3
"""Chunked, resumable renderer: EDL -> finished reel. Same code path for the 720p cloud preview and the
4K HEVC Main10 device render (ffmpeg 4.4 compatible: lut3d, bilateral, maskedmerge, remap, overlay
format=yuv420p10, alimiter level=0, concat demuxer -c copy).

  render.py prepare --edl EDL --out DIR --height 1280|3840 --mode proxy|final [--max-frames 120] [--input hlg|sdr]
  render.py run     --out DIR --src VIDEO [--budget 140] [--threads 4]   # renders pending pieces, stops before budget
  render.py audio   --out DIR --audio SRC_AUDIO_OR_VIDEO                  # cut/speed/clean/loudness, exact length
  render.py finish  --out DIR --dest OUT.mp4                              # concat -c copy + mux + verify
  render.py verify  --out DIR --file OUT.mp4
  render.py still   --out DIR --src VIDEO --t OUT_TIME --png X.png       # single frame through the real graph
  render.py status  --out DIR
Every device call must stay < 150 s: 'run' measures fps per piece (state.json) and only starts a piece when
elapsed + estimate < budget. Re-run 'run' until it prints ALL_DONE.
"""
import argparse, json, os, subprocess, sys, time, shutil, math, re
import numpy as np

FFMPEG = os.environ.get('FFMPEG', 'ffmpeg')    # e.g. FFMPEG=~/bin/ffmpeg44 to force a specific build
FFPROBE = os.environ.get('FFPROBE', 'ffprobe')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import overlays as OV
import make_lut

FPS = 30


def sh(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, **kw)
    if r.returncode != 0:
        raise RuntimeError(f"cmd failed ({r.returncode}): {' '.join(cmd)[:400]}\n{r.stderr[-3000:]}")
    return r


def load(p):
    return json.load(open(p))


def save(o, p):
    tmp = p + '.tmp'
    json.dump(o, open(tmp, 'w'), ensure_ascii=False, indent=1)
    os.replace(tmp, p)


# ------------------------------------------------------------------ prepare
def retouch_assets(face, R, W, H, mode, outdir, key):
    """Static per-face-position assets: crop rect, soft skin/face mask (raw yuv, all planes) and slimming remap maps."""
    fx, fy, fw, fh = face
    bw, bh = fw * W, fh * H
    cx, cy = (fx + fw / 2) * W, (fy + fh / 2) * H
    x0 = int(max(0, cx - bw * 0.95)) // 4 * 4
    x1 = int(min(W, cx + bw * 0.95)) // 4 * 4
    y0 = int(max(0, cy - bh * 0.95)) // 4 * 4
    y1 = int(min(H, cy + bh * 0.85)) // 4 * 4
    cw, ch = x1 - x0, y1 - y0
    yy, xx = np.mgrid[0:ch, 0:cw].astype(np.float32)
    u = (xx + x0 - cx) / (bw / 2)
    v = (yy + y0 - cy) / (bh / 2)
    # face ellipse (forehead..chin), soft edge
    r = np.sqrt((u / 0.95) ** 2 + ((v - 0.05) / 1.05) ** 2)
    m = np.clip((1.0 - r) / 0.30, 0, 1) ** 1.5 * R.get('smooth', 0.55)
    depth = 10 if mode == 'final' else 8
    mx = (1 << depth) - 1
    my = np.round(m * mx)
    mc = my[::2, ::2]
    dt = np.uint16 if depth > 8 else np.uint8
    mask = os.path.join(outdir, f'mask_{key}.raw')
    with open(mask, 'wb') as f:
        f.write(my.astype(dt).tobytes())
        f.write(mc.astype(dt).tobytes())
        f.write(mc.astype(dt).tobytes())
    out = dict(x=x0, y=y0, w=cw, h=ch, mask=mask)
    k = R.get('slim', 0.0)
    if k > 0:
        # horizontal inward pull of cheeks/jaw: sample further out -> content moves toward the face centre line
        bump = np.exp(-((np.abs(u) - 0.85) / 0.25) ** 2)
        vwin = np.clip((v + 0.05) / 0.35, 0, 1) * np.clip((1.15 - v) / 0.25, 0, 1)   # nose level .. chin
        wgt = bump * vwin * (np.abs(u) < 1.5)
        xs = xx + (xx + x0 - cx) * k * wgt
        # zero displacement on the crop border (identity seam)
        edge = np.minimum.reduce([xx, cw - 1 - xx, yy, ch - 1 - yy]) / 8.0
        xs = xx + (xs - xx) * np.clip(edge, 0, 1)
        xm = os.path.join(outdir, f'xmap_{key}.raw')
        ym = os.path.join(outdir, f'ymap_{key}.raw')
        np.clip(np.round(xs), 0, cw - 1).astype('<u2').tofile(xm)
        yy.astype('<u2').tofile(ym)
        out.update(xmap=xm, ymap=ym, max_disp_px=float(np.abs(xs - xx).max()))
    hk = R.get('head_shrink', 0.0)
    if hk > 0:
        # uniform head shrink (user 2026-10-22: "전체적인 머리크기 정도 줄여주면돼", jaw-only slimming looked unnatural):
        # everything within R1 of the head centre is scaled by (1-hk) about that centre (shape preserved), the
        # displacement fades to zero at R2 with a smoothstep, so the background ring stretches by < hk and lines stay
        # straight-ish; zero displacement on the crop border.
        hcx, hcy = cx, cy - 0.12 * bh                     # head centre: a bit above the face-box centre (hair)
        R1, R2 = 0.80 * bh, 1.45 * bh
        hx0, hx1 = int(max(0, hcx - R2)) // 4 * 4, int(min(W, hcx + R2)) // 4 * 4
        hy0, hy1 = int(max(0, hcy - R2)) // 4 * 4, int(min(H, hcy + R2)) // 4 * 4
        hw_, hh_ = hx1 - hx0, hy1 - hy0
        gy, gx = np.mgrid[0:hh_, 0:hw_].astype(np.float32)
        dx, dy = gx + hx0 - hcx, gy + hy0 - hcy
        rr = np.sqrt(dx * dx + dy * dy)
        t_ = np.clip((rr - R1) / (R2 - R1), 0, 1)
        wgt = 1 - t_ * t_ * (3 - 2 * t_)
        f_ = 1 + hk * wgt                                  # sample further out -> content shrinks toward the centre
        edge = np.clip(np.minimum.reduce([gx, hw_ - 1 - gx, gy, hh_ - 1 - gy]) / 8.0, 0, 1)
        sx = gx + dx * (f_ - 1) * edge
        sy = gy + dy * (f_ - 1) * edge
        # float maps, applied with BILINEAR cv2.remap in a pipe (ffmpeg 4.4 remap is nearest-only -> jaggies/blocks
        # on the neck and sweater at 1.00 framing, user 2026-10-22). Chroma maps on the half-res grid.
        cx2 = sx[::2, ::2] / 2.0
        cy2 = sy[::2, ::2] / 2.0
        hwp = os.path.join(outdir, f'hwarp_{key}.npz')
        np.savez(hwp, yx=sx.astype(np.float32), yy=sy.astype(np.float32), cx=cx2.astype(np.float32), cy=cy2.astype(np.float32))
        out.update(hx=hx0, hy=hy0, hw=hw_, hh=hh_, hwarp=hwp, head_disp_px=float(max(np.abs(sx - gx).max(), np.abs(sy - gy).max())))
    return out


def cmd_prepare(a):
    E = load(a.edl)
    H = a.height
    land = E.get('orientation', 'portrait') == 'landscape'
    if land:   # --height = frame height: 720 proxy / 2160 master -> 1280x720 / 3840x2160 canvas
        W = int(round(H * 16 / 9 / 2)) * 2
        s = H / 2160.0
    else:
        W = int(round(H * 9 / 16 / 2)) * 2
        s = H / 3840.0
    D = os.path.abspath(a.out)
    AD = os.path.join(D, 'assets')
    os.makedirs(AD, exist_ok=True)
    st = OV.merged_style(E.get('style'), base=OV.LANDSCAPE_STYLE if land else None)
    rot = E.get('rotate') if a.mode == 'final' or a.rotate else None
    man = dict(W=W, H=H, s=s, mode=a.mode, fps=FPS, edl=os.path.abspath(a.edl), input=a.input,
               orientation='landscape' if land else 'portrait', rotate=rot)
    # colour LUT
    # grade modes: 'none' (input already corrected in CapCut -> untouched), 'his_look' (fitted to his CapCut
    # export: assets/his_look.cube, raw iPhone HLG input), 'param' (make_lut parametric look)
    gm = E.get('grade', {}).get('mode', 'his_look' if a.input == 'hlg' else 'none')
    man['grade_mode'] = gm
    cube = os.path.join(AD, 'grade.cube')
    if gm == 'his_look':
        shutil.copy(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets', 'his_look.cube'), cube)
    elif gm == 'param':
        gp = dict(make_lut.DEFAULT)
        gp.update(E.get('grade', {}).get('lut', {}))
        make_lut.write_cube(cube, gp, a.input)
    man['cube'] = cube
    man['sharpen'] = E.get('grade', {}).get('sharpen', gm != 'none')
    L = E.get('layers', {})
    man['layers'] = L
    man['preview_tc'] = bool(E.get('preview_timecode')) and a.mode != 'final'
    man['grade'] = E.get('grade', {})
    # captions
    caps = []
    for i, c in enumerate(E['captions'] if L.get('captions', True) else []):
        p = os.path.join(AD, f'cap{i:03d}.png')
        info = OV.caption_png(c['text'], c['speaker'], st, s, p)
        info.update(t0=c['out_start'], t1=c['out_end'], speaker=c['speaker'])
        caps.append(info)
        if L.get('english', True) and c.get('en'):
            pe = os.path.join(AD, f'en{i:03d}.png')
            ei = OV.english_png(c['en'], st, s, pe, box=info, above=c.get('en_above', False))
            ei.update(t0=c['out_start'], t1=c['out_end'])
            caps.append(ei)
    man['captions'] = caps
    if L.get('header', True):
        man['header'] = OV.header_png(st, s, W, os.path.join(AD, 'header.png'))
        man['header'].update(t0=E['header']['out_start'], t1=E['header']['out_end'])
    else:
        man['header'] = None
    if E['hook'].get('text') and L.get('hook', True):
        hk, intro = OV.hook_assets(E['hook']['text'], st, s, W, AD)
        hk.update(t0=0.0, t1=E['hook']['out_end'])
        intro.update(t0=0.0, t1=E['hook']['out_end'])
        man['hook'], man['intro'] = hk, (intro if E['hook'].get('intro', True) else None)
    man['transitions'] = E.get('transitions', [])
    if E.get('character') and L.get('character', True):
        ch = OV.character_assets(st, s, AD)
        ch['intervals'] = [[c['out_start'], c['out_end']] for c in E['character']]
        man['character'] = ch
    # cards (face of the segment at card start decides the side)
    segs = E['segments']

    def seg_at(t):
        for sg in segs:
            if sg['out_start'] - 1e-6 <= t < sg['out_end']:
                return sg
        return segs[-1]
    cards = []
    for i, c in enumerate(E.get('cards', []) if L.get('cards', True) else []):
        info = OV.card_assets(c, i, st, s, W, H, seg_at(c['out_start']).get('face'), AD)
        info.update(t0=c['out_start'], t1=c['out_end'])
        cards.append(info)
    man['cards'] = cards
    # retouch assets per (quantised) face position
    # defaults fitted to his CapCut 1022 retouch on ep10 (inner-face MAE 10.6 -> 6.1 /255 vs his export)
    R = dict(smooth=0.60, slim=0.0, head_shrink=0.035, bilateral_s=4.0, bilateral_r=0.08, lift=0.14, lift_off=0.025, vshift=-0.008)
    R.update(E.get('retouch', {}))
    man['retouch'] = R
    # soft face mosaic for an on-camera guest (two-shot takes; user 2026-10-23 '은은하게 보일듯말듯')
    MZ = E.get('mosaic')
    if MZ and L.get('mosaic', True):
        tp = MZ['track'] if os.path.isabs(MZ['track']) else os.path.join(os.path.dirname(os.path.abspath(a.edl)), MZ['track'])
        shutil.copy(tp, os.path.join(AD, 'mosaic_track.npz'))
        man['mosaic'] = dict(track=os.path.join(AD, 'mosaic_track.npz'), block=MZ.get('block', 0.10), blend=MZ.get('blend', 0.9),
                             soften=MZ.get('soften', 0.45), feather=MZ.get('feather', 0.30), pad=MZ.get('pad', [0.12, 0.10]))
    else:
        man['mosaic'] = None
    rt = {}
    for sg in segs:
        if not sg.get('face') or R.get('off'):
            sg['_rt'] = None
            continue
        q = [round(v * 50) / 50 for v in sg['face']]  # 2 % grid -> few variants, little disk on the device
        key = '_'.join(f'{v:.2f}' for v in q) + ('_s' if sg.get('face_stable') else '_n')
        if key not in rt:
            Rk = dict(R)
            if not sg.get('face_stable'):
                Rk['slim'] = 0.0  # face moves inside this segment: never warp (would bend background)
            rt[key] = retouch_assets(q, Rk, W, H, a.mode, AD, len(rt))
        sg['_rt'] = key
    man['retouch_assets'] = rt
    # pieces: split at segment and zoom boundaries, cap at max_frames (default 240 proxy / 120 final = < 150 s even
    # at 1 fps; 'run' re-splits further if the measured fps is lower)
    if not a.max_frames:
        a.max_frames = 120 if a.mode == 'final' else 240
    zb = sorted(set(int(round(z['out_start'] * FPS)) for z in E.get('zooms', [])))
    pieces = []
    for si, sg in enumerate(segs):
        f0 = int(round(sg['out_start'] * FPS))
        f1 = f0 + sg['frames']
        cuts = [f0] + [b for b in zb if f0 < b < f1] + [f1]
        for c0, c1 in zip(cuts[:-1], cuts[1:]):
            n = c1 - c0
            k = max(1, math.ceil(n / a.max_frames))
            bounds = [c0 + round(n * j / k) for j in range(k + 1)]
            for b0, b1 in zip(bounds[:-1], bounds[1:]):
                if b1 <= b0:
                    continue
                z = 1.0
                cxy = (0.5, 0.5)
                for zz in E.get('zooms', []):
                    if zz['out_start'] * FPS - 0.5 <= b0 < zz['out_end'] * FPS - 0.5:
                        z, cxy = zz['scale'], (zz['cx'], zz['cy'])
                pieces.append(dict(i=len(pieces), seg=si, f0=b0, n=b1 - b0, speed=sg['speed'],
                                   src=round(sg['src_start'] + (b0 - f0) / FPS * sg['speed'], 4),
                                   zoom=z, zc=cxy, rt=sg['_rt'], done=False))
    man['pieces'] = pieces
    man['out_frames'] = sum(p['n'] for p in pieces)
    assert man['out_frames'] == E['out_frames'], (man['out_frames'], E['out_frames'])
    save(man, os.path.join(D, 'manifest.json'))
    st_path = os.path.join(D, 'state.json')
    if not os.path.exists(st_path):
        save(dict(done={}, fps=[]), st_path)
    print(f'prepared {len(pieces)} pieces, {man["out_frames"]} frames ({man["out_frames"] / FPS:.2f}s) at {W}x{H} mode={a.mode}; '
          f'retouch variants {len(rt)}; assets in {AD}')


# ------------------------------------------------------------------ per-piece graph
def piece_graph(man, p, threads):
    W, H, s, mode = man['W'], man['H'], man['s'], man['mode']
    PF = 'yuv420p10le' if mode == 'final' else 'yuv420p'
    OVF = 'yuv420p10' if mode == 'final' else 'yuv420'
    T0 = p['f0'] / FPS
    T1 = (p['f0'] + p['n']) / FPS
    N = p['n']
    inputs = []  # list of arg lists
    fl = []
    sp = p['speed']
    dur_src = N / FPS * sp + 0.6
    if needs_pipe(man, p):
        # stage A (speed + scale), then the bilinear head warp and/or face mosaic in python; frames arrive on stdin
        inputs.append(['-f', 'rawvideo', '-pix_fmt', PF, '-s', f'{W}x{H}', '-r', str(FPS), '-i', 'pipe:0'])
        fl.append("[0:v]setpts=PTS-STARTPTS")
    else:
        inputs.append(['-ss', f"{p['src']:.4f}", '-t', f'{dur_src:.4f}', '-i', '{SRC}'])
        # 1. speed -> exact 30 fps timeline
        fl.append(f"[0:v]setpts=(PTS-STARTPTS)/{sp},fps={FPS},scale={W}:{H}:flags=lanczos" if mode != 'final' else
                  f"[0:v]setpts=(PTS-STARTPTS)/{sp},fps={FPS}")
    # 2. colour: HLG/BT.2020 (or SDR) -> BT.709 + calibrated look, via 3D LUT in RGB
    inm = 'bt2020' if man.get('input', 'hlg') == 'hlg' else 'bt709'
    if man.get('grade_mode', 'param') == 'none':
        fl[-1] += f",format={PF}[g]"                 # corrected input: pixels pass through untouched
    else:
        fl[-1] += (f",scale=in_color_matrix={inm}:in_range=tv:out_range=pc,format=gbrp10le,"
                   f"lut3d=file='{man['cube']}':interp=tetrahedral,"
                   f"scale=out_color_matrix=bt709:in_range=pc:out_range=tv,format={PF}[g]")
    last = 'g'
    # 3. retouch: skin-masked bilateral + face lift (+ static slimming remap on stable segments)
    R = man['retouch']
    rk = p.get('rt')
    if rk:
        ra = man['retouch_assets'][rk]
        mi = len(inputs)
        inputs.append(['-f', 'rawvideo', '-pix_fmt', PF, '-s', f"{ra['w']}x{ra['h']}", '-i', ra['mask']])
        ss_ = R['bilateral_s'] * s * 3
        fl.append(f"[{last}]split=2[ga][gb];[gb]crop={ra['w']}:{ra['h']}:{ra['x']}:{ra['y']},split=2[fo][fs];"
                  f"[fs]bilateral=sigmaS={ss_:.2f}:sigmaR={R['bilateral_r']}:planes=7,"
                  f"lutyuv=y='clip(val*{1 + R['lift']}+{R['lift_off']}*maxval,minval,maxval)':v='clip(val-{R['vshift']}*maxval,minval,maxval)'[fsm];"
                  f"[fo][fsm][{mi}:v]maskedmerge[fm]")
        fc = 'fm'
        if ra.get('xmap'):
            xi = len(inputs)
            inputs.append(['-f', 'rawvideo', '-pix_fmt', 'gray16le', '-s', f"{ra['w']}x{ra['h']}", '-i', ra['xmap']])
            inputs.append(['-f', 'rawvideo', '-pix_fmt', 'gray16le', '-s', f"{ra['w']}x{ra['h']}", '-i', ra['ymap']])
            hi = 'yuv444p10le' if mode == 'final' else 'yuv444p'
            fl.append(f"[fm]format={hi}[f4];[f4][{xi}:v][{xi + 1}:v]remap,format={PF}[fr]")
            fc = 'fr'
        fl.append(f"[ga][{fc}]overlay=x={ra['x']}:y={ra['y']}:format={OVF}[rt]")
        last = 'rt'
        pass
    # 4. mild sharpen (CapCut sharpen 0.077 / clarity 0.099 equivalent)
    if man.get('sharpen', True):
        us = 5 if H <= 1400 else 9
        fl.append(f"[{last}]unsharp=lx={us}:ly={us}:la=0.35:cx={us}:cy={us}:ca=0[sh]")
        last = 'sh'
    # 5. framing (punch-in) about the face point, hard cut
    if p['zoom'] and abs(p['zoom'] - 1.0) > 1e-3:
        z = p['zoom']
        cw, ch = int(W / z) // 2 * 2, int(H / z) // 2 * 2
        cx, cy = p['zc']
        x = int(min(max(0, cx * W * (1 - 1 / z)), W - cw)) // 2 * 2
        y = int(min(max(0, cy * H * (1 - 1 / z)), H - ch)) // 2 * 2
        fl.append(f"[{last}]crop={cw}:{ch}:{x}:{y},scale={W}:{H}:flags=lanczos[zm]")
        last = 'zm'

    def en(t0, t1):
        a, b = max(0.0, t0 - T0), t1 - T0
        return f"between(t,{a:.4f},{b - 0.0005:.4f})"

    def live(t0, t1):
        return t0 < T1 - 1e-6 and t1 > T0 + 1e-6
    k = 0

    def add_overlay(idx, x, y, enable, eof='repeat'):
        nonlocal last, k
        k += 1
        lab = f'o{k}'
        fl.append(f"[{last}][{idx}]overlay=x={x}:y={y}:format={OVF}:eof_action={eof}:enable='{enable}'[{lab}]")
        last = lab
    # character (looping clip, global phase)
    ch = man.get('character')
    if ch:
        ivs = [iv for iv in ch['intervals'] if live(*iv)]
        if ivs:
            phase = (p['f0'] % ch['period_frames']) / FPS
            ci = len(inputs)
            inputs.append(['-stream_loop', '-1', '-ss', f'{phase:.4f}', '-i', ch['mov']])
            fl.append(f"[{ci}:v]setpts=PTS-STARTPTS,format=rgba[chr]")
            add_overlay('chr', ch['x'], ch['y'], '+'.join(en(*iv) for iv in ivs))
    # cards (animated clips)
    for j, c in enumerate(man.get('cards', [])):
        if live(c['t0'], c['t1']):
            off = max(0.0, T0 - c['t0'])
            ci = len(inputs)
            inputs.append(['-ss', f'{off:.4f}', '-i', c['mov']])
            delay = max(0.0, c['t0'] - T0)
            fl.append(f"[{ci}:v]setpts=PTS-STARTPTS+{delay:.4f}/TB,format=rgba[cd{j}]")
            add_overlay(f'cd{j}', c['x'], c['y'], en(c['t0'], c['t1']), eof='pass')
    # captions
    for c in man['captions']:
        if live(c['t0'], c['t1']):
            ci = len(inputs)
            inputs.append(['-i', c['png']])
            add_overlay(f'{ci}:v', c['x'], c['y'], en(c['t0'], c['t1']))
    # hook (fly-up clip, last frame holds) + intro block, then persistent header
    hk = man.get('hook')
    if hk and live(hk['t0'], hk['t1']):
        off = min(max(0.0, T0 - hk['t0']), (hk['frames'] - 1) / FPS)  # past the fly-in: hold last frame
        ci = len(inputs)
        inputs.append(['-ss', f'{off:.4f}', '-i', hk['mov']])
        fl.append(f"[{ci}:v]setpts=PTS-STARTPTS,format=rgba[hk]")
        add_overlay('hk', hk['x'], hk['y'], en(hk['t0'], hk['t1']))
        it = man.get('intro')
        if it:
            ci = len(inputs)
            inputs.append(['-i', it['png']])
            add_overlay(f'{ci}:v', it['x'], it['y'], en(it['t0'], it['t1']))
    hd = man.get('header')
    if hd and live(hd['t0'], hd['t1']):
        ci = len(inputs)
        inputs.append(['-i', hd['png']])
        add_overlay(f'{ci}:v', hd['x'], hd['y'], en(hd['t0'], hd['t1']))
    # exact frame count
    # transitions (cold open -> edit): 'flash' = fade to white over the last out_frames of the piece ending at t, and
    # from white over the first in_frames of the piece starting at t (applied above all overlays)
    fx = ''
    for tr in man.get('transitions', []):
        fc_ = int(round(tr['t'] * FPS))
        if tr.get('type', 'cut') not in ('flash', 'soft_flash'):
            continue                              # 'cut' = plain hard cut (default; research: no flash/whoosh)
        col = 'white' if tr['type'] == 'flash' else '0xF4F0EC'
        if p['f0'] + N == fc_:
            k = min(tr['out_frames'], N)
            fx += f"fade=t=out:st={(N - k) / FPS:.4f}:d={k / FPS:.4f}:color={col},"
        if p['f0'] == fc_:
            fx += f"fade=t=in:st=0:d={min(tr['in_frames'], N) / FPS:.4f}:color={col},"
    if man.get('preview_tc'):
        # small running timecode (output seconds) in the top-left so the user can say "37초 컷이 어색해"
        fnt = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'assets', 'Pretendard-ExtraBold.otf')
        fx += (f"drawtext=fontfile='{fnt}':text='%{{eif\\:t+{T0:.4f}\\:d\\:1}}.%{{eif\\:mod((t+{T0:.4f})*10\\,10)\\:d\\:1}}s':"
               f"x=16:y=16:fontsize={int(max(W, H) * 0.022)}:fontcolor=white:box=1:boxcolor=black@0.45:boxborderw=6,")
    rot = {'cclock': 'transpose=cclock,', 'clock': 'transpose=clock,'}.get(man.get('rotate') or '', '')
    fl.append(f"[{last}]{fx}tpad=stop_mode=clone:stop=6,trim=end_frame={N},setpts=PTS-STARTPTS,{rot}format={PF}[vout]")
    return inputs, ';'.join(fl)


def encode_args(man, threads):
    if man['mode'] == 'final':
        return ['-c:v', 'libx265', '-preset', os.environ.get('REELS_X265_PRESET', 'superfast'), '-crf', os.environ.get('REELS_X265_CRF', '15'), '-pix_fmt', 'yuv420p10le', '-profile:v', 'main10',
                '-x265-params', f'log-level=error:pools={threads}:keyint=60:colorprim=bt709:transfer=bt709:colormatrix=bt709:range=limited',
                '-tag:v', 'hvc1', '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709', '-color_range', 'tv']
    return ['-c:v', 'libx264', '-preset', 'veryfast', '-crf', '18', '-pix_fmt', 'yuv420p', '-threads', str(threads),
            '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709', '-color_range', 'tv']


def stage_a(man, p, src, threads, nframes):
    """decode + speed (+ proxy scale) -> raw frames on stdout, for the bilinear head warp"""
    W, H, mode = man['W'], man['H'], man['mode']
    PF = 'yuv420p10le' if mode == 'final' else 'yuv420p'
    sp = p['speed']
    vf = f"setpts=(PTS-STARTPTS)/{sp},fps={FPS}" + (f",scale={W}:{H}:flags=lanczos" if mode != 'final' else '')
    return [FFMPEG, '-v', 'error', '-threads', str(threads), '-ss', f"{p['src']:.4f}", '-t', f'{nframes / FPS * sp + 0.6:.4f}',
            '-i', src, '-vf', vf, '-frames:v', str(nframes + 6), '-pix_fmt', PF, '-f', 'rawvideo', 'pipe:1']


def needs_pipe(man, p):
    ra = man['retouch_assets'].get(p.get('rt')) if p.get('rt') else None
    return bool((ra and ra.get('hwarp')) or man.get('mosaic'))


def warp_cmd(man, p):
    ra = man['retouch_assets'].get(p.get('rt')) if p.get('rt') else None
    cmd = [sys.executable, os.path.abspath(__file__), '_warp', '--w', str(man['W']), '--h', str(man['H']),
           '--bits', '10' if man['mode'] == 'final' else '8']
    if ra and ra.get('hwarp'):
        cmd += ['--map', ra['hwarp'], '--rect', f"{ra['hx']},{ra['hy']},{ra['hw']},{ra['hh']}"]
    if man.get('mosaic'):
        cmd += ['--mosaic', json.dumps(man['mosaic']), '--src0', f"{p['src']:.4f}", '--speed', str(p['speed'])]
    return cmd


def run_pipeline(man, p, src, threads, cmd):
    if not needs_pipe(man, p):
        return sh(cmd)
    a_ = subprocess.Popen(stage_a(man, p, src, threads, p['n']), stdout=subprocess.PIPE)
    w_ = subprocess.Popen(warp_cmd(man, p), stdin=a_.stdout, stdout=subprocess.PIPE)
    a_.stdout.close()
    b_ = subprocess.Popen(cmd, stdin=w_.stdout)
    w_.stdout.close()
    rc = b_.wait(); w_.wait(); a_.wait()
    if rc != 0:
        raise RuntimeError('piece pipeline failed: ' + ' '.join(cmd[:6]))


def _mosaic_plane(P_, x0, y0, x1, y1, blk, sig, mask, blend):
    import cv2
    roi = P_[y0:y1, x0:x1].astype(np.float32)
    h, w = roi.shape
    sw, sh_ = max(1, int(round(w / blk))), max(1, int(round(h / blk)))
    up = cv2.resize(cv2.resize(roi, (sw, sh_), interpolation=cv2.INTER_AREA), (w, h), interpolation=cv2.INTER_NEAREST)
    if sig > 0.3:
        up = cv2.GaussianBlur(up, (0, 0), sig)          # soften the block edges -> '보일듯말듯', not a hard grid
    a_ = mask * blend
    P_[y0:y1, x0:x1] = np.clip(roi * (1 - a_) + up * a_, 0, np.iinfo(P_.dtype).max).astype(P_.dtype)


def cmd_warp(a):
    """raw yuv420 frames stdin -> stdout: optional bilinear head warp (--map) and/or soft face mosaic (--mosaic)"""
    import cv2
    W, H = a.w, a.h
    dt = np.uint16 if a.bits > 8 else np.uint8
    bpp = 2 if a.bits > 8 else 1
    ys, cs = W * H, (W // 2) * (H // 2)
    fsz = (ys + 2 * cs) * bpp
    if a.map:
        M = np.load(a.map)
        x0, y0, w, h = [int(v) for v in a.rect.split(',')]
        yx, yy, cx, cy = M['yx'], M['yy'], M['cx'], M['cy']
    MZ = json.loads(a.mosaic) if a.mosaic else None
    if MZ:
        TR = np.load(MZ['track'])
        tt, bb = TR['t'], TR['box']
        mask_cache = {}
    inp, outp = sys.stdin.buffer, sys.stdout.buffer
    j = 0
    while True:
        buf = inp.read(fsz)
        if len(buf) < fsz:
            break
        fr = np.frombuffer(buf, dt).copy()
        Y = fr[:ys].reshape(H, W)
        U = fr[ys:ys + cs].reshape(H // 2, W // 2)
        V = fr[ys + cs:].reshape(H // 2, W // 2)
        if a.map:
            Y[y0:y0 + h, x0:x0 + w] = cv2.remap(np.ascontiguousarray(Y[y0:y0 + h, x0:x0 + w]), yx, yy, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
            c0, c1, cw, ch = x0 // 2, y0 // 2, w // 2, h // 2
            for P_ in (U, V):
                P_[c1:c1 + ch, c0:c0 + cw] = cv2.remap(np.ascontiguousarray(P_[c1:c1 + ch, c0:c0 + cw]), cx[:ch, :cw], cy[:ch, :cw], cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        if MZ:
            t = a.src0 + j / FPS * a.speed
            bx = [float(np.interp(t, tt, bb[:, k])) for k in range(4)]
            px, py = MZ['pad']
            fx0, fy0 = (bx[0] - px * bx[2]) * W, (bx[1] - py * bx[3]) * H
            fw, fh = bx[2] * (1 + 2 * px) * W, bx[3] * (1 + 2 * py) * H
            X0, Y0 = max(0, int(fx0) // 2 * 2), max(0, int(fy0) // 2 * 2)
            X1, Y1 = min(W, int(fx0 + fw + 1) // 2 * 2), min(H, int(fy0 + fh + 1) // 2 * 2)
            if X1 - X0 >= 8 and Y1 - Y0 >= 8:
                key = (X1 - X0, Y1 - Y0)
                if key not in mask_cache:
                    hh, ww = key[1], key[0]
                    gy, gx = np.mgrid[0:hh, 0:ww].astype(np.float32)
                    r = np.sqrt(((gx + 0.5) / ww * 2 - 1) ** 2 + ((gy + 0.5) / hh * 2 - 1) ** 2)  # ellipse, 1 at the rim
                    f = MZ['feather']
                    m = np.clip((1 - r) / f, 0, 1)
                    mask_cache[key] = (m, cv2.resize(m, (ww // 2, hh // 2), interpolation=cv2.INTER_AREA))
                m, mc = mask_cache[key]
                blk = max(2.0, MZ['block'] * bx[2] * W)          # block size = fraction of the face width
                _mosaic_plane(Y, X0, Y0, X1, Y1, blk, MZ['soften'] * blk, m, MZ['blend'])
                for P_ in (U, V):
                    _mosaic_plane(P_, X0 // 2, Y0 // 2, X1 // 2, Y1 // 2, blk / 2, MZ['soften'] * blk / 2, mc, MZ['blend'])
        outp.write(fr.tobytes())
        j += 1
    outp.flush()


def build_cmd(man, p, src, threads, out, still=None):
    inputs, graph = piece_graph(man, p, threads)
    gfile = os.path.join(os.path.dirname(out), f'graph_{p["i"]:04d}.txt')
    with open(gfile, 'w') as f:
        f.write(graph)
    cmd = [FFMPEG, '-v', 'error', '-y', '-threads', str(threads), '-filter_threads', str(threads)]
    for inp in inputs:
        cmd += [src if x == '{SRC}' else x for x in inp]
    cmd += ['-filter_complex_script', gfile, '-map', '[vout]', '-an']
    if still is not None:
        cmd += ['-vf' if False else '-frames:v', '1', out]
        return cmd
    cmd += encode_args(man, threads) + ['-r', str(FPS), out]
    return cmd


def probe_frames(path):
    r = sh([FFPROBE, '-v', 'error', '-select_streams', 'v:0', '-count_packets', '-show_entries', 'stream=nb_read_packets',
            '-of', 'csv=p=0', path])
    return int(r.stdout.strip().split(',')[0])


def cmd_run(a):
    D = a.out
    man = load(os.path.join(D, 'manifest.json'))
    stp = os.path.join(D, 'state.json')
    st = load(stp)
    PD = os.path.join(D, 'pieces')
    os.makedirs(PD, exist_ok=True)
    t_start = time.time()
    default_fps = 2.5 if man['mode'] == 'final' else 25.0
    def split_piece(p, k):
        """re-split a pending piece into k frame-exact parts (measured fps too low for the per-call budget)."""
        idx = man['pieces'].index(p)
        nid = max(q['i'] for q in man['pieces']) + 1
        bounds = [round(p['n'] * j / k) for j in range(k + 1)]
        parts = []
        for j, (b0, b1) in enumerate(zip(bounds[:-1], bounds[1:])):
            q = dict(p, i=nid + j, f0=p['f0'] + b0, n=b1 - b0, src=round(p['src'] + b0 / FPS * p['speed'], 4))
            parts.append(q)
        man['pieces'][idx:idx + 1] = parts
        save(man, os.path.join(D, 'manifest.json'))
        print(f'split piece {p["i"]} ({p["n"]}f) into {k} parts to fit the {a.budget:.0f}s budget', flush=True)

    while True:
        todo = [p for p in man['pieces'] if str(p['i']) not in st['done']]
        if not todo:
            break
        p = todo[0]
        fps_est = float(np.median(st['fps'][-8:])) if st['fps'] else default_fps
        est = p['n'] / fps_est * 1.15 + 3
        el = time.time() - t_start
        if a.budget and est > a.budget - 5 and p['n'] > 20:
            fit = max(15, int((a.budget - 8) / 1.15 * fps_est * 0.9))
            split_piece(p, math.ceil(p['n'] / fit))
            continue
        if a.budget and el + est > a.budget and el > 0.5:
            break
        out = os.path.join(PD, f'p{p["i"]:04d}.mp4')
        t0 = time.time()
        run_pipeline(man, p, a.src, a.threads, build_cmd(man, p, a.src, a.threads, out))
        dt = time.time() - t0
        nf = probe_frames(out)
        if nf != p['n']:
            raise RuntimeError(f'piece {p["i"]} has {nf} frames, expected {p["n"]}')
        st['done'][str(p['i'])] = dict(file=out, frames=nf, sec=round(dt, 2))
        st['fps'].append(nf / dt)
        save(st, stp)
        print(f'piece {p["i"]}/{len(man["pieces"])} {nf}f {dt:.1f}s ({nf / dt:.1f} fps)', flush=True)
    left = [p for p in man['pieces'] if str(p['i']) not in st['done']]
    if left:
        fps_est = float(np.median(st['fps'][-8:])) if st['fps'] else default_fps
        rem = sum(p['n'] for p in left) / fps_est
        print(f'PENDING {len(left)} pieces, ~{rem:.0f}s of render left (~{math.ceil(rem / (a.budget or 1e9) + 0.01)} more calls)')
    else:
        print('ALL_DONE')


def cmd_still(a):
    man = load(os.path.join(a.out, 'manifest.json'))
    f = int(round(a.t * FPS))
    p = next(pp for pp in man['pieces'] if pp['f0'] <= f < pp['f0'] + pp['n'])
    q = dict(p)
    df = f - p['f0']
    q['f0'] = f
    q['n'] = 1
    q['src'] = round(p['src'] + df / FPS * p['speed'], 4)
    os.makedirs(os.path.dirname(os.path.abspath(a.png)), exist_ok=True)
    run_pipeline(man, q, a.src, 2, build_cmd(man, q, a.src, 2, os.path.abspath(a.png), still=True))
    print('wrote', a.png)


# ------------------------------------------------------------------ audio
def measure(path, extra_af=''):
    af = (extra_af + ',' if extra_af else '') + 'ebur128=peak=true'
    r = subprocess.run([FFMPEG, '-v', 'info', '-nostats', '-i', path, '-af', af, '-f', 'null', '-'], capture_output=True, text=True)
    I = float(re.findall(r'I:\s+(-?[\d.]+) LUFS', r.stderr)[-1])
    TP = float(re.findall(r'Peak:\s+(-?[\d.inf]+) dBFS', r.stderr)[-1])
    return I, TP


def cmd_audio(a):
    D = a.out
    man = load(os.path.join(D, 'manifest.json'))
    E = load(man['edl'])
    AU = os.path.join(D, 'audio')
    os.makedirs(AU, exist_ok=True)
    fade = E.get('audio', {}).get('fade_ms', 12) / 1000.0
    # 1) cut + speed with word-safe micro-fades, exact sample length per segment (A/V lock by construction)
    parts = []
    for i, sg in enumerate(E['segments']):
        n = sg['frames']
        dur = n / FPS
        ns = int(round(dur * 48000))
        parts.append(f"[0:a]atrim=start={sg['src_start']:.4f}:end={sg['src_start'] + dur * sg['speed'] + 0.05:.4f},asetpts=PTS-STARTPTS,"
                     f"aresample=48000,atempo={sg['speed']},afade=t=in:st=0:d={fade},"
                     + (f"volume={sg['gain_db']}dB," if sg.get('gain_db') else '')
                     + ""
                     + (f"volume=volume=0.03:enable='lt(t,{sg['mute_lead'] / sg['speed']:.4f})',"
                        if sg.get('mute_lead', 0) > 0 else '')
                     + f"apad,atrim=end_sample={ns},"
                     f"afade=t=out:st={dur - fade:.4f}:d={fade}[a{i}]")
    n = len(E['segments'])
    graph = ';'.join(parts) + ';' + ''.join(f'[a{i}]' for i in range(n)) + f'concat=n={n}:v=0:a=1[cat]'
    gf = os.path.join(AU, 'cut_graph.txt')
    open(gf, 'w').write(graph)
    cut = os.path.join(AU, 'cut.wav')
    sh([FFMPEG, '-v', 'error', '-y', '-i', a.audio, '-filter_complex_script', gf, '-map', '[cat]', '-ac', '1', '-ar', '48000',
        '-c:a', 'pcm_f32le', cut])
    I0, TP0 = measure(cut)
    # noise floor estimate (10th percentile of 50 ms RMS)
    raw = sh([FFMPEG, '-v', 'error', '-i', cut, '-f', 'f32le', '-ac', '1', '-ar', '16000', '-'], ).stdout if False else None
    data = subprocess.run([FFMPEG, '-v', 'error', '-i', cut, '-f', 'f32le', '-ac', '1', '-ar', '16000', '-'], capture_output=True).stdout
    x = np.frombuffer(data, np.float32)
    hop = 800
    nb = len(x) // hop
    rms = 20 * np.log10(np.sqrt((x[:nb * hop].reshape(nb, hop) ** 2).mean(1)) + 1e-9)
    nf = float(np.clip(np.percentile(rms, 10), -80, -20))
    # 2) voice chain at a safe working level, then measured static gain + true-peak-safe limiter
    pre = -20.0 - I0
    if E.get('audio', {}).get('mode', 'voice_chain') == 'passthrough':
        # input already processed in CapCut (denoise/EQ/loudness): keep its sound, only level + true-peak safety
        chain = f"volume={pre:.2f}dB"
    else:
        chain = (f"volume={pre:.2f}dB,highpass=f=80:poles=2,afftdn=nr=10:nf={max(-80, min(-20, nf + pre + 3)):.1f},"
                 f"equalizer=f=300:t=q:w=1:g=-2,equalizer=f=3000:t=q:w=1:g=2,"
                 f"acompressor=threshold=-26dB:ratio=3:attack=10:release=150:makeup=1")
    I1, TP1 = measure(cut, chain)
    target = E.get('audio', {}).get('target_lufs', -11.0)
    lim = 0.89  # alimiter (4.4) holds output ~2 dB under 'limit' -> measured true peak ~ -3.5 dBTP
    final = os.path.join(AU, 'final.wav')
    hist = []  # (gain, measured I) -> secant search, loudness is monotonic in gain
    g = target - I1
    for it in range(5):
        af = f"{chain},volume={g:.2f}dB,alimiter=limit={lim}:attack=3:release=60:level=0,aresample=48000"
        sh([FFMPEG, '-v', 'error', '-y', '-i', cut, '-af', af, '-ac', '2', '-ar', '48000', '-c:a', 'pcm_s24le', final])
        I2, TP2 = measure(final)
        hist.append((g, I2))
        if abs(I2 - target) <= 0.15:
            break
        if len(hist) >= 2 and abs(hist[-1][1] - hist[-2][1]) > 0.05:
            (g0, i0), (g1, i1) = hist[-2], hist[-1]
            g = g1 + (target - i1) * (g1 - g0) / (i1 - i0)
        else:
            g += 1.5 * (target - I2)
    total = man['out_frames'] / FPS
    for k, tr in enumerate([t_ for t_ in E.get('transitions', []) if t_.get('whoosh')]):
        # soft whoosh under the flash: 0.45 s pink-noise swell, band-limited, peaks at the cut, ~ -22 dBFS
        tw = max(0.0, tr['t'] - 0.30)
        wh = os.path.join(AU, f'whoosh{k}.wav')
        sh([FFMPEG, '-v', 'error', '-y', '-f', 'lavfi', '-i', 'anoisesrc=d=0.45:c=pink:r=48000:a=0.5',
            '-af', 'highpass=f=500,lowpass=f=5000,afade=t=in:st=0:d=0.30:curve=exp,afade=t=out:st=0.30:d=0.15,volume=-12dB',
            '-ac', '2', wh])
        mixed = os.path.join(AU, f'final_mix{k}.wav')
        sh([FFMPEG, '-v', 'error', '-y', '-i', final, '-i', wh, '-filter_complex',
            f"[1]adelay={int(tw * 1000)}|{int(tw * 1000)},apad[w];[0][w]amix=inputs=2:duration=first:dropout_transition=0,volume=2",
            '-c:a', 'pcm_s24le', mixed])
        final = mixed
    m4a = os.path.join(AU, 'final.m4a')
    sh([FFMPEG, '-v', 'error', '-y', '-i', final, '-af', f'apad,atrim=end_sample={int(round(total * 48000))}',
        '-c:a', 'aac', '-b:a', '256k', '-ar', '48000', '-ac', '2', m4a])
    I3, TP3 = measure(m4a)
    info = dict(src_I=I0, src_TP=TP0, noise_floor=nf, voice_I=I1, final_I=I3, final_TP=TP3, gain=g, duration=total)
    save(info, os.path.join(AU, 'audio.json'))
    print('audio', json.dumps(info))


# ------------------------------------------------------------------ finish / verify
def cmd_finish(a):
    D = a.out
    man = load(os.path.join(D, 'manifest.json'))
    st = load(os.path.join(D, 'state.json'))
    missing = [p['i'] for p in man['pieces'] if str(p['i']) not in st['done']]
    if missing:
        sys.exit(f'pieces missing: {missing[:10]}... run "run" again')
    lst = os.path.join(D, 'concat.txt')
    with open(lst, 'w') as f:
        for p in man['pieces']:
            f.write(f"file '{os.path.abspath(st['done'][str(p['i'])]['file'])}'\n")
    vid = os.path.join(D, 'video_only.mp4')
    sh([FFMPEG, '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', lst, '-c', 'copy', vid])
    m4a = os.path.join(D, 'audio', 'final.m4a')
    tag = ['-tag:v', 'hvc1'] if man['mode'] == 'final' else []
    sh([FFMPEG, '-v', 'error', '-y', '-i', vid, '-i', m4a, '-map', '0:v', '-map', '1:a', '-c', 'copy'] + tag +
       ['-movflags', '+faststart', a.dest])
    a.file = a.dest
    cmd_verify(a)


def cmd_verify(a):
    D = a.out
    man = load(os.path.join(D, 'manifest.json'))
    r = json.loads(sh([FFPROBE, '-v', 'error', '-show_entries', 'stream=codec_type,codec_name,width,height,pix_fmt,r_frame_rate,'
                       'duration,color_primaries,color_transfer,color_space,channels,sample_rate', '-show_entries', 'format=duration',
                       '-of', 'json', a.file]).stdout)
    v = next(s for s in r['streams'] if s['codec_type'] == 'video')
    au = next((s for s in r['streams'] if s['codec_type'] == 'audio'), None)
    nf = probe_frames(a.file)
    I, TP = measure(a.file)
    exp = man['out_frames']
    checks = dict(
        resolution=(v['width'], v['height']) == ((man['H'], man['W']) if man.get('rotate') else (man['W'], man['H'])),
        fps=v['r_frame_rate'] == '30/1',
        frames=nf == exp,
        pix_fmt=v['pix_fmt'] == ('yuv420p10le' if man['mode'] == 'final' else 'yuv420p'),
        codec=v['codec_name'] == ('hevc' if man['mode'] == 'final' else 'h264'),
        bt709=v.get('color_primaries') == 'bt709' and v.get('color_transfer') == 'bt709',
        audio=bool(au) and au.get('sample_rate') == '48000',
        av_sync=bool(au) and abs(float(au['duration']) - exp / FPS) < 1.5 / FPS,
        loudness=abs(I - load(man['edl']).get('audio', {}).get('target_lufs', -11.0)) <= 1.0 and TP <= -1.0,
    )
    rep = dict(file=a.file, frames=nf, expected=exp, video_dur=v.get('duration'), audio_dur=au and au.get('duration'),
               lufs=I, true_peak=TP, checks=checks, ok=all(checks.values()))
    save(rep, os.path.join(D, 'verify.json'))
    print(json.dumps(rep, indent=1))


def cmd_status(a):
    man = load(os.path.join(a.out, 'manifest.json'))
    st = load(os.path.join(a.out, 'state.json'))
    done = sum(1 for p in man['pieces'] if str(p['i']) in st['done'])
    fr = sum(p['n'] for p in man['pieces'] if str(p['i']) in st['done'])
    print(f"{done}/{len(man['pieces'])} pieces, {fr}/{man['out_frames']} frames, median fps "
          f"{np.median(st['fps']) if st['fps'] else float('nan'):.2f}")


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('prepare'); p.add_argument('--edl', required=True); p.add_argument('--out', required=True)
    p.add_argument('--height', type=int, default=1280); p.add_argument('--mode', default='proxy', choices=['proxy', 'final'])
    p.add_argument('--max-frames', type=int, default=0); p.add_argument('--input', default='hlg', choices=['hlg', 'sdr'])
    p.add_argument('--rotate', action='store_true', help='apply the EDL rotate in proxy mode too (default: final only)')
    p = sub.add_parser('run'); p.add_argument('--out', required=True); p.add_argument('--src', required=True)
    p.add_argument('--budget', type=float, default=0); p.add_argument('--threads', type=int, default=2)
    p = sub.add_parser('audio'); p.add_argument('--out', required=True); p.add_argument('--audio', required=True)
    p = sub.add_parser('finish'); p.add_argument('--out', required=True); p.add_argument('--dest', required=True)
    p = sub.add_parser('verify'); p.add_argument('--out', required=True); p.add_argument('--file', required=True)
    p = sub.add_parser('still'); p.add_argument('--out', required=True); p.add_argument('--src', required=True)
    p.add_argument('--t', type=float, required=True); p.add_argument('--png', required=True)
    p = sub.add_parser('status'); p.add_argument('--out', required=True)
    p = sub.add_parser('_warp'); p.add_argument('--map'); p.add_argument('--w', type=int, required=True)
    p.add_argument('--h', type=int, required=True); p.add_argument('--bits', type=int, default=8); p.add_argument('--rect')
    p.add_argument('--mosaic'); p.add_argument('--src0', type=float, default=0.0); p.add_argument('--speed', type=float, default=1.0)
    a = ap.parse_args()
    dict(prepare=cmd_prepare, run=cmd_run, audio=cmd_audio, finish=cmd_finish, verify=cmd_verify, still=cmd_still,
         status=cmd_status, _warp=cmd_warp)[a.cmd](a)
