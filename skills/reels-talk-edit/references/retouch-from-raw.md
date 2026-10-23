# Add-on: retouch from the raw iPhone file (stage R, optional)

Use only when the input is the raw `IMG_xxxx.MOV` (HLG) **and** the user asks for retouching. Default is his CapCut
export: 2 minutes in CapCut beats this pipeline (it reaches ~85–90 % of his look; CapCut's face-shape tools — eyes,
nose, jaw — are not reproduced).

Matches his CapCut 1022 settings (sharpen .05, clarity .10, temp −.10, smart colour .30, denoise, smooth .10,
whitening .08, small face .10, slim .05 …):
- `grade.mode his_look` = 3D LUT (`assets/his_look.cube`) fitted on 25 raw→export frame pairs; background error
  2.8/255 held-out (the old parametric look: 8.8).
- `retouch` defaults: skin bilateral blended 60 %, face lift ×1.14 +2.5 %, V −0.8 % (warmer), `head_shrink` 0.035.
  Inner-face error vs his export 6.1/255 (was 10.6); whole frame 7.4/255.
- Head shrink runs as a bilinear `cv2.remap` in a pipe (`render.py _warp`): ffmpeg 4.4 `remap` is nearest-only and
  tore the neck. Never per-region slimming (bent the jaw — user feedback).
- `audio.mode voice_chain`: HPF 80, afftdn, EQ −2 dB@300 / +2 dB@3 k, comp 3:1 → loudness target −9.5 LUFS. One mic
  can't make "only our voices" louder: the room rises with them, and the processing becomes audible at +30 dB.
