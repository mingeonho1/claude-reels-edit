#!/usr/bin/env python3
"""Re-transcribe short ambiguous windows (whisper-turbo + zipformer) to settle caption wording.
usage: retranscribe.py AUDIO.wav T0-T1 [T0-T1 ...] [--models DIR]
Prints whisper text, zipformer text and zipformer token times for each window (window padded 0.15 s).
Use it for words flagged '!' in words.txt and for every number/proper noun that goes on screen.
"""
import sys, os, re, argparse, subprocess
import numpy as np
import sherpa_onnx

ap = argparse.ArgumentParser()
ap.add_argument('audio')
ap.add_argument('spans', nargs='+')
ap.add_argument('--models', default=os.environ.get('REELS_MODELS', os.path.expanduser('~/reels_models')))
a = ap.parse_args()
raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', a.audio, '-vn', '-ac', '1', '-ar', '16000', '-af',
                      'highpass=f=70,dynaudnorm=f=150:g=15:p=0.9:m=20', '-f', 'f32le', '-'],
                     capture_output=True, check=True).stdout
x = np.frombuffer(raw, np.float32)
M = a.models
Z = f'{M}/sherpa-onnx-zipformer-korean-2024-06-24'
zr = sherpa_onnx.OfflineRecognizer.from_transducer(encoder=f'{Z}/encoder-epoch-99-avg-1.int8.onnx', decoder=f'{Z}/decoder-epoch-99-avg-1.onnx',
                                                   joiner=f'{Z}/joiner-epoch-99-avg-1.int8.onnx', tokens=f'{Z}/tokens.txt', num_threads=2)
Wd = f'{M}/sherpa-onnx-whisper-turbo'
wr = sherpa_onnx.OfflineRecognizer.from_whisper(encoder=f'{Wd}/turbo-encoder.int8.onnx', decoder=f'{Wd}/turbo-decoder.int8.onnx',
                                                tokens=f'{Wd}/turbo-tokens-hex.txt', language='ko', task='transcribe', num_threads=2)
for sp in a.spans:
    t0, t1 = map(float, sp.split('-'))
    s0, s1 = int(max(0, t0 - 0.15) * 16000), int((t1 + 0.15) * 16000)
    ch = x[s0:s1]
    st = zr.create_stream(); st.accept_waveform(16000, ch); zr.decode_stream(st)
    sw = wr.create_stream(); sw.accept_waveform(16000, ch); wr.decode_stream(sw)
    wt = bytes().join(bytes.fromhex(h) for h in re.findall('§([0-9a-f]*)§', sw.result.text)).decode('utf-8', 'replace').strip()
    toks = ' '.join(f"{t.replace('▁', '_')}@{s0 / 16000 + ts:.2f}" for t, ts in zip(st.result.tokens, st.result.timestamps))
    print(f'[{t0:.2f}-{t1:.2f}] W: {wt}\n              Z: {st.result.text}\n              T: {toks}')
