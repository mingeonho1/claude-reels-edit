#!/usr/bin/env python3
"""Create turbo-tokens-hex.txt from sherpa-onnx whisper turbo-tokens.txt.
Each base64 token's raw bytes are wrapped as '§<hex>§' so partial UTF-8 byte tokens (Korean) survive the
recognizer's string join; analyze_audio.py/retranscribe.py decode the §hex§ runs back to UTF-8.
usage: make_hex_tokens.py turbo-tokens.txt turbo-tokens-hex.txt
"""
import base64, sys
src, dst = sys.argv[1], sys.argv[2]
with open(src) as f, open(dst, 'w') as g:
    for line in f:
        parts = line.rstrip('\n').split(' ')
        if len(parts) != 2:
            continue
        b64, idx = parts
        raw = base64.b64decode(b64)
        g.write(base64.b64encode(('§' + raw.hex() + '§').encode('utf-8')).decode() + ' ' + idx + '\n')
