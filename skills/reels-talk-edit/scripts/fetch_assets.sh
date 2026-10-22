#!/usr/bin/env bash
# Downloads the third-party assets and speech models this skill needs (not stored in the repo).
#   fonts  -> skills/reels-talk-edit/assets/ (Do Hyeon, Pretendard ExtraBold — both SIL OFL 1.1)
#   face   -> skills/reels-talk-edit/assets/yunet.onnx (OpenCV Zoo YuNet)
#   models -> $REELS_MODELS (default ~/reels_models): sherpa-onnx whisper-turbo, zipformer-korean, silero VAD, ERes2Net
# usage: bash scripts/fetch_assets.sh [--no-models]
set -euo pipefail
HERE="$(cd "$(dirname "$0")/.." && pwd)"
A="$HERE/assets"; mkdir -p "$A"

get() { [ -s "$2" ] && { echo "ok   $(basename "$2")"; return; }; echo "get  $(basename "$2")"; curl -fL --retry 3 -o "$2" "$1"; }

get https://raw.githubusercontent.com/google/fonts/main/ofl/dohyeon/DoHyeon-Regular.ttf "$A/DoHyeon-Regular.ttf"
get https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/public/static/Pretendard-ExtraBold.otf "$A/Pretendard-ExtraBold.otf" || {
  T="$(mktemp -d)"; curl -fL -o "$T/p.zip" https://github.com/orioncactus/pretendard/releases/download/v1.3.9/Pretendard-1.3.9.zip
  unzip -j -o "$T/p.zip" public/static/Pretendard-ExtraBold.otf -d "$A"; rm -rf "$T"; }
get https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx "$A/yunet.onnx"
[ -f "$A/character.gif" ] || echo "note assets/character.gif missing — add your guest character (transparent GIF) or turn modules.character off"

[ "${1:-}" = "--no-models" ] && exit 0
M="${REELS_MODELS:-$HOME/reels_models}"; mkdir -p "$M"; cd "$M"
R=https://github.com/k2-fsa/sherpa-onnx/releases/download
[ -d sherpa-onnx-whisper-turbo ] || curl -fL $R/asr-models/sherpa-onnx-whisper-turbo.tar.bz2 | tar xj
[ -d sherpa-onnx-zipformer-korean-2024-06-24 ] || curl -fL $R/asr-models/sherpa-onnx-zipformer-korean-2024-06-24.tar.bz2 | tar xj
get $R/asr-models/silero_vad.onnx "$M/silero_vad.onnx"
get $R/speaker-recongition-models/3dspeaker_speech_eres2net_base_sv_zh-cn_3dspeaker_16k.onnx "$M/3dspeaker_speech_eres2net_base_sv_zh-cn_3dspeaker_16k.onnx"
# whisper's token file drops multi-byte Hangul pieces; a hex-encoded copy fixes Korean decoding
python3 "$HERE/scripts/make_hex_tokens.py" sherpa-onnx-whisper-turbo/turbo-tokens.txt sherpa-onnx-whisper-turbo/turbo-tokens-hex.txt
echo "models in $M"
