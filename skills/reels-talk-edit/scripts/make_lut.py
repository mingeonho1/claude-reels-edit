#!/usr/bin/env python3
"""Build the colour LUT (.cube, 33^3) used by render.py: iPhone HLG/BT.2020 -> SDR BT.709 + channel look.

usage: make_lut.py OUT.cube [--params grade.json] [--input hlg|sdr]
Grade params (all optional, defaults = calibrated to Geonho's ep9 CapCut export, see SKILL.md):
  exposure  linear gain applied after HLG OOTF (1.0 = 203 nit reference white -> SDR 100%)
  sys_gamma HLG system gamma (1.2 nominal)
  gain      [r,g,b] per-channel linear gains (white balance / 'temperature')
  sat       saturation in linear light around luma (1.0 = none)
  knee      highlight soft-clip start (0..1, SDR linear)
  out_gamma display encoding exponent (2.4 = BT.1886)
  contrast  S-curve strength on encoded signal (0 = none)
numpy only (runs on the device too). The cube maps full-range R'G'B' in -> full-range R'G'B' out.
"""
import argparse, json
import numpy as np

A, B, C = 0.17883277, 0.28466892, 0.55991073
M2020_709 = np.array([[1.6605, -0.5876, -0.0728],
                      [-0.1246, 1.1329, -0.0083],
                      [-0.0182, -0.1006, 1.1187]])
# calibrated (least squares on static background patches) so that iPhone HLG ep9 matches his CapCut BT.709 export
DEFAULT = dict(exposure=0.25, sys_gamma=1.0, gain=[1.0, 1.0619, 1.2129], sat=1.10, knee=0.5, out_gamma=2.471, contrast=0.0)
PHYSICAL = dict(exposure=1.0, sys_gamma=1.2, gain=[1.0, 1.0, 1.0], sat=1.0, knee=0.8, out_gamma=2.4, contrast=0.0)


def hlg_inv_oetf(e):
    e = np.clip(e, 0, 1)
    return np.where(e <= 0.5, e * e / 3.0, (np.exp((e - C) / A) + B) / 12.0)


def softclip(x, knee):
    # identity below knee, smooth asymptote to 1.0 above
    k = knee
    over = np.maximum(x - k, 0)
    return np.where(x <= k, x, k + (1 - k) * (1 - np.exp(-over / (1 - k))))


def convert(rgb, P, inp='hlg'):
    """rgb: (...,3) full-range signal in [0,1] -> (...,3) SDR BT.709 signal in [0,1]."""
    P = {**DEFAULT, **(P or {})}
    if inp == 'hlg':
        E = hlg_inv_oetf(rgb)                      # scene linear, 0..1
        Ys = E @ np.array([0.2627, 0.6780, 0.0593])
        F = E * np.power(np.maximum(Ys, 1e-6), P['sys_gamma'] - 1)[..., None]  # display linear rel. to 1000 nit
        F = F * (1000.0 / 203.0) * P['exposure']   # 203 nit ref white -> 1.0
        L = F @ M2020_709.T
    else:  # SDR bt709 input
        L = np.power(np.clip(rgb, 0, 1), 2.4) * P['exposure']
    L = L * np.array(P['gain'])
    Y = L @ np.array([0.2126, 0.7152, 0.0722])
    L = Y[..., None] + (L - Y[..., None]) * P['sat']
    L = np.clip(L, 0, None)
    L = softclip(L, P['knee'])
    V = np.power(np.clip(L, 0, 1), 1.0 / P['out_gamma'])
    if P['contrast']:
        c = P['contrast']
        V = V + c * (V - 0.5) * V * (1 - V) * 4  # gentle S-curve around mid grey
    return np.clip(V, 0, 1)


def write_cube(path, P, inp='hlg', n=33):
    g = np.linspace(0, 1, n)
    # .cube order: R fastest
    b, gg, r = np.meshgrid(g, g, g, indexing='ij')
    rgb = np.stack([r, gg, b], -1).reshape(-1, 3)
    out = convert(rgb, P, inp)
    with open(path, 'w') as f:
        f.write(f'TITLE "reels-talk-edit {inp}->709"\nLUT_3D_SIZE {n}\nDOMAIN_MIN 0 0 0\nDOMAIN_MAX 1 1 1\n')
        for v in out:
            f.write(f'{v[0]:.6f} {v[1]:.6f} {v[2]:.6f}\n')


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('--params')
    ap.add_argument('--input', default='hlg', choices=['hlg', 'sdr'])
    a = ap.parse_args()
    P = json.load(open(a.params)) if a.params else {}
    P = P.get('lut', P)
    write_cube(a.out, P, a.input)
    print('wrote', a.out, {**DEFAULT, **P})
