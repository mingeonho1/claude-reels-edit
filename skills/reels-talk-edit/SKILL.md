---
name: reels-talk-edit
description: "@geono_x 2인 경제토크 릴스 편집 워크플로우: CapCut 보정본(또는 아이폰 원본)을 받아 ①컷편집 미리보기→승인 ②한국어 자막+그걸 기반으로 영어 자막→승인 ③지루함 줄이는 연출(선택) ④독립 검수 서브에이전트 ⑤Mac에서 4K 마스터. '릴스 편집', 'N번 에피소드 컷편집/자막', '보정본 편집해줘'에 사용."
---

# reels-talk-edit — 단계형 워크플로우 (에이전트 1명이 순서대로 수행)

Format: one static vertical camera on Geonho (**host**, asks; black caption), friend 정우 off-camera (**guest**,
explains; navy caption + character GIF). Planning/script is out of scope — this starts from footage.
His time sinks (user, 2026-10-22): **cuts ≫ captions ≫ everything else**. So stages 1–2 are the core; 3 is optional.

```
INPUT ─► 0 intake ─► 1 CUT ──gate──► 2 SUBS (KR → EN) ──gate──► 3 ENHANCE (opt) ─► 4 QA subagent ─► 5 4K master
            (R) retouch only if the input is the raw iPhone file and the user asks for it
```
Gates: show the preview and wait for "ㅇㅋ/괜찮아". If the user said "자동 승인 / 질문하지 말고 끝까지" (or set
`auto_approve`), don't wait — still check stills yourself and continue. Feedback arrives as "37초 컷이 어색해":
every preview carries a running timecode (top-left) so map it via the EDL and edit the plan, re-render, re-show.

Hard rules: never degrade the source (master = source resolution/fps/10-bit; overlays on top); 반말 captions, no
emoji; no fake facts on screen (cards only state what was said); the user's corrected input is not re-graded.

## Files
Bundle on the Mac: `~/capcut/reels-talk-edit/` = this file, `scripts/`, `assets/` (Do Hyeon, Pretendard, character
GIF, his_look.cube, yunet.onnx), `ref/` (style_spec.md, retention_research.md, reels-qa-SKILL.md, gt9.json + evaluate.py).
Pull once per session: `device_bash: cd $HOME/mnt/capcut/reels-talk-edit && tar czf ../_bundle.tgz --exclude='*.tgz' .`
→ `device_stage_files ~/capcut/_bundle.tgz` → `mkdir -p ~/rte && tar xzf /mnt/user-data/uploads/capcut/_bundle.tgz -C ~/rte`;
`S=~/rte/scripts` in every command below.
Models (cloud, once): GitHub releases only (HuggingFace blocked):
```
M=~/reels_models; mkdir -p $M && cd $M; R=https://github.com/k2-fsa/sherpa-onnx/releases/download
curl -L $R/asr-models/sherpa-onnx-whisper-turbo.tar.bz2 | tar xj
curl -L $R/asr-models/sherpa-onnx-zipformer-korean-2024-06-24.tar.bz2 | tar xj
curl -LO $R/asr-models/silero_vad.onnx; curl -LO $R/speaker-recongition-models/3dspeaker_speech_eres2net_base_sv_zh-cn_3dspeaker_16k.onnx
pip install sherpa-onnx soundfile --break-system-packages
python3 ~/rte/scripts/make_hex_tokens.py sherpa-onnx-whisper-turbo/turbo-tokens.txt sherpa-onnx-whisper-turbo/turbo-tokens-hex.txt
```
Device limits (Mac VM via device_bash): ffmpeg 4.4, 4 CPU, 3 GB RAM, **≤150 s per call, background jobs die**,
no deletes without permission (put scratch in `<episode>/_reels_work/`). Cloud: 2 CPU, ffmpeg 6.1.

## 0. Intake (≈10 min for a 5-min take)
1. Find the input: `~/capcut/me/<NN_topic>/소스/`. **Corrected** = his CapCut export (`*보정*.mov`, SDR bt709,
   `color_transfer=bt709`) → `--input sdr`, `grade.mode none`, `audio.mode passthrough`, retouch off.
   **Raw** = `IMG_xxxx.MOV` (HLG `arib-std-b67`) → `--input hlg`; use stage R only if asked.
2. Device: `python3 ~/mnt/capcut/reels-talk-edit/scripts/device_proxy.py <MOV> <episode>/_reels_work/prx --budget 140`
   (repeat until `PROXY_DONE`), stage `src_720.mp4` + `src.wav`.
3. Cloud: `analyze_audio.py src.wav stt.json` → `diarize.py src.wav diar.json` → `face_track.py src_720.mp4 face.npz`
   → `build_words.py … --out words.json --transcript words.txt` (speaker = 1.6·diar + 0.9·mouth; bigger cluster
   with less mouth motion = guest). Read words.txt end to end (`i start-end H/G(logit) word [zipformer] !`).
4. STT gaps: any pause > 1.5 s inside talk, `!`-flagged words, numbers/proper nouns →
   `python3 $S/retranscribe.py src.wav T0-T1 --models ~/reels_models`. Whisper-turbo sometimes drops whole sentences
   (ep10 117–128 s) or keeps only the louder on-mic voice in overlaps: add missing words with zipformer times to
   `words_patch.json` (`{"add":[{w,start,end,spk}], "set_spk":[[t0,t1,"host|guest"]]}`), re-run build_words `--patch`,
   and decide the speaker by on-camera mouth motion (logit sign), not diarization alone.

## 1. CUT — the main job (gate 1)
Plan (`plan.json`, `"stage":"cut"`). Rules, numbers first:
- Keep the conversation's logic: hook question → explanation → example → payoff → open question. Target ≤ 96–100 s.
- Drop: greetings/small talk before the first real question, filler-only runs (음/어/뭐), false starts of a *turn*,
  recaps that repeat a point, side branches, trailing words after a sentence ends, a turn-opening "근데/아" + its
  pause when the line really starts after it. Keep in-sentence restarts in the audio (he does; caption cleans them).
- Pauses: cut only inside verified quiet (RMS ≤ floor+6 dB, ≥ 0.28 s); pads 0.09 s in / 0.12 s out; 12 ms fades.
- Speaker turns: **0.20 s** of silence in the output (natural turn gap ≈ 200 ms; > 0.5 s = dead air). build_edl
  extends into source quiet, else pre-rolls the next shot with audio at 3 % (`mute_lead`).
- Speed (pitch kept): host 1.20 / guest 1.30 / mixed 1.25, cap 1.32 (avg ≈ 1.25; 1.33 felt fast).
- Cold open (optional, recommended): `cold_open.spans` = one strong later line of 2–5 s (ep10: guest "지금 쓰는
  클로드도 할 수 있지 않나? / 비싼 거 쓰면 뭐가 다른데?") played first, then a **plain hard cut** into the episode.
- Fix edges with `retime` (word edge seconds; trust the RMS envelope over STT word times) and `mute_extra` (`{"src": seg_start, "add": 0.06}` mutes a
  residual syllable after a tight in-point). Keep tight cuts ≤ 12.
```
python3 $S/build_edl.py --plan plan.json --words words.json --rms stt_rms10ms.npy --face face.npz --out edl_cut.json
python3 $S/render.py prepare --edl edl_cut.json --out rcut --height 1280 --mode proxy --input sdr|hlg
python3 $S/render.py run --out rcut --src prx/src_720.mp4 --threads 2 --budget 100000
python3 $S/render.py audio --out rcut --audio prx/src.wav && python3 $S/render.py finish --out rcut --dest cut_preview.mp4
python3 $S/cutlist.py --edl edl_cut.json --words words.json --plan plan.json --out cutlist.md
```
Show `cut_preview.mp4` (re-encode ≤ 30 MB: `-b:v 2000k`) + `cutlist.md` (kept lines with timecodes, dropped lines
with reasons). Wait for approval (gate 1) unless auto-approve.

## 2. SUBS — Korean, then English from the Korean (gate 2)
Set `"stage":"subs"`. Write every caption yourself into `plan.captions[]` (`t` = source seconds range,
`speaker`, `text`, `en`) and `cold_open.captions[]`.
- **Korean** (his house style, measured on ep9): one line, ≤ 16 chars w/o spaces (≤ 21 with), ≥ 0.45 s, ≤ 13
  chars/s; one clause per caption, never merge two clauses; drop fillers (음 어 막 그 이제 좀 약간 이렇게 그냥),
  clause glue (근데/그래서/아) unless meaningful, quotative tails; collapse restarts; keep numbers/names exact
  (2400만 원, GPT-6 아스트라); fix STT mishears from context + the `[zip]` column; 맞장구 gets its own caption.
- **English = translation of the final Korean caption, 1:1, same timing** (writing EN from the audio drifts —
  user). Short spoken English, same numbers (100만 원 = 1M won, 2400만 = 24M won), a sentence split over two
  Korean captions reads as one sentence over two English lines (keep KR word order where possible: "Your loan limit
  doesn't grow / just because the wedding moves up"). No added facts, no emoji.
- Look: KR = Do Hyeon 110 px in a white box h175 r35 (host top 2146 black / guest top 2373 navy #252973 @4K);
  EN = Do Hyeon 68 px (236,236,236) with a 3 px dark outline + soft shadow, 6 px under its box; above the box only
  when both speakers' boxes are on screen for > 40 % of the caption. Speaker hand-overs < 0.3 s are trimmed.
Render as in stage 1 into `rsubs` → `subs_preview.mp4`; show; wait (gate 2).

## 3. ENHANCE — optional modules, natural only (`"stage":"final"`, `"modules":{…}`)
Evidence + user feedback (ref/retention_research.md). Defaults ON unless noted:
- `header`: two fixed lines on top after the hook ("01년생 AI 3년차 개발자와 Sydney Uni 금융 경제 / 고품격 힐링 토크쇼").
- `hook`: title (≤ 10 Hangul, e.g. "AI 전문가인 척하기") over the cold open; intro block only without a cold open.
- `character`: guest GIF (1041 px, centre 1828,2375 @4K) while the guest explains; stays through ≤ 1.3 s host
  맞장구, leaves on a real host question; blocks < 1.5 s dropped.
- `zoom` (`zoom_mode: host_cut`): punch-in 1.08 **only as a hard cut where the host's black caption starts**
  (±0.45 s), out at the next cut near the guest's first caption (else exactly at it); ≥ 1.5 s on screen; ≤ 1 start
  per 8 s; one fixed centre. Never zoom mid-sentence or on guest lines; never animate.
- `cards`: ≤ 1 per 15–20 s, 2.5–6 s, triggered by a spoken number, only facts said on tape (build_edl warns on
  numbers not in the transcript; no "다음 편"/CTA cards), title ≤ 9 Hangul, 1–4 lines ≤ 9 Hangul, optional accent
  number; arrow follows the sign (`dir` down/부족/감소 → blue ▼, up → red ▲). White r40 card, Do Hyeon 104/92/128.
- Transition into the episode: `cut` (default). `soft_flash` / `flash` + `whoosh` exist but read as cheap — only on request.
- Never: face warping beyond `head_shrink` 0.035, word-by-word karaoke captions, emoji, random colours, SFX spam.
Render `rfinal` → `final_preview.mp4`.

## 4. QA — independent subagent (loop ≤ 3 rounds)
Spawn a fresh `general-purpose` Agent (it must NOT get your plan or reasoning) with:
"Use the reels-qa skill (or read ~/rte/ref/reels-qa-SKILL.md). VIDEO=…/final_preview.mp4 EDL=…/edl_final.json RENDER_DIR=…/rfinal SCRIPTS=~/rte/scripts
OUT=…/qa_rN MODELS=~/reels_models". It runs `qa_auto.py` (re-transcribes the OUTPUT, caption↔audio match, KR↔EN
numbers, frame-diff/phase-correlation jumps & shake, clicks at cuts, dead air > 0.7 s, loudness, black/frozen frames,
card overlaps) and a human pass (every caption + every English line, frames at every cut/zoom/card, waveforms at
flags) and returns `qa_findings.json` with time · severity · evidence · fix.
Apply every blocker/major fix in the plan (`retime`, `mute_extra`, `drop`, caption `text`/`en`/`t`, modules),
rebuild, re-render, re-run `qa_auto.py` (auto pass is enough for round 2+ if the fixes are mechanical). Known
false positives: whisper looping ("Q. Q. Q.") → zipformer-only evidence; "uncaptioned" fillers you removed on purpose.
Ship only with 0 blocker / 0 major (or the user accepts them). Show the user the final preview + a 3-line QA summary.
(ep10 round 1 caught: an EN number error, a cut 0.1 s into the next word, 25 ms residual syllables after tight
cuts, 0.84 s dead air, zoom held over guest lines — all fixed in round 2.)

## 5. 4K master on the device
Package: `tar czf /mnt/user-data/outputs/job.tgz -C ~/rte scripts assets` + `edl_final.json` → `device_commit_files`
to `<episode>/_reels_work/` → `tar xzf … --overwrite` (if a file is read-only, extract to a new dir).
```
python3 scripts/render.py prepare --edl edl.json --out r4k --height 3840 --mode final --input sdr|hlg
python3 scripts/render.py run --out r4k --src ../소스/<input>.mov --threads 4 --budget 150     # repeat until ALL_DONE
python3 scripts/render.py audio --out r4k --audio ../소스/<input>.mov
python3 scripts/render.py finish --out r4k --dest ../<NN>_final_4k.mp4                        # verify.json all true
```
x265 superfast crf 15 (`REELS_X265_PRESET/CRF` to override): ≈ 1.6 fps → 100 s reel ≈ 14 calls ≈ 28 min.
Heads-up: corrected inputs skip LUT/retouch so they render faster. Then stills from the 4K file → look → report path.

## R. Retouch from raw (optional, only for the raw iPhone file)
Matches his CapCut 1022 settings (sharpen .05, clarity .10, temp −.10, smart colour .30, denoise, smooth .10,
whitening .08, small face .10, slim .05 …):
- `grade.mode his_look` = 3D LUT fitted on 25 frame pairs raw→his export (background MAE 2.8/255 held-out; old
  parametric look 8.8).
- retouch defaults: skin bilateral blended 60 %, face lift ×1.14 +2.5 %, V −0.8 % (warmer), `head_shrink` 0.035
  (bilinear cv2 warp in a pipe; ffmpeg 4.4 `remap` is nearest-only and breaks the neck). Inner-face MAE to his
  export 6.1/255 (was 10.6). Whole frame 7.4/255.
- audio `voice_chain`: HPF 80, afftdn, EQ −2 dB@300 / +2 dB@3 k, comp 3:1 → loudness target.
It is ~85–90 % of his CapCut look; CapCut's face-shape tools (eyes, nose, jaw) are not reproduced. If he can
spend 2 minutes in CapCut, the corrected input is better — default to that.

## Look reference (2160x3840; measured from his ep9 CapCut edit — ref/style_spec.md)
caption: Do Hyeon 110 px (Pretendard fallback for missing glyphs like '·'), white box h175 r35 pad 26, centre x 1080,
host top 2146 black, guest top 2373 navy #252973 · header: line1 1473 px wide at y 533, line2 979 px at y 649, black ·
hook: Do Hyeon 260 px black + 7 px white outline, centre y 708, fly-up · character GIF 1041 px, centre (1828, 2375).

## Regression check (after changing any rule/script)
`ref/gt9.json` = his own ep9 edit (segments, captions, character blocks) from CapCut draft `1005`. Re-plan ep9 with
the changed rules, render 720p, `python3 ref/evaluate.py --edl edl9.json --video out9.mp4` (max 95). Reference: skill
75.7, his own edit 93.9 (caption_text is low by design — he paraphrases). A drop > 1 point is a regression.

## Plan keys (all optional except captions)
`stage` cut|subs|final · `start_word`/`end_word` (src s) · `drop[] {t:[s0,s1],why}` · `retime[] {i,src}` ·
`mute_extra[] {src,add}` · `speed {host,guest,mixed}` `speed_cap` `target_out` · `turn_gap` 0.20 ·
`cold_open {spans,captions,transition,whoosh}` · `hook {text,until_t}` · `captions[] {t,speaker,text,en}` ·
`cards[] {at_t,dur,title,lines,accent,dir}` · `modules {header,hook,character,zoom,cards}` · `zoom_mode` host_cut ·
`zoom {host_cut,min_zoom,min_gap}` · `grade {mode none|his_look|param, sharpen}` · `retouch {off|smooth,head_shrink,lift,…}` ·
`audio {mode passthrough|voice_chain, target_lufs (−10.5 corrected / −9.5 raw), host_gain_db}` · `preview_timecode`.
