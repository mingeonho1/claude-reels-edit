---
name: reels-talk-edit
description: "@geono_x 릴스를 촬영본에서 편집한다: 2인 토크(세로·가로 투샷 90° 회전 업로드)와 컨퍼런스 객석 영상 후기 몽타주(기획 서브에이전트+심사 먼저). 컷 미리보기·승인 → 한국어+영어 자막·승인 → 연출(선택) → 독립 검수 → Mac 4K. '릴스 편집', 'N번 컷편집/자막', '컨퍼런스 다녀온 릴스'에 사용."
---

# reels-talk-edit — one agent, one workflow, gated stages

Talk takes start from footage (no planning step); the recap-montage format starts with planning (subagent plans +
judge, see its reference). His time sinks (2026-10-22): **cuts ≫ captions ≫
everything else** → stages 1–2 are the core, 3 is optional. The workflow is the same for every format; only
layout details differ, and those live in a format reference (read exactly one):

| Input (ffprobe) | Format | Read |
|---|---|---|
| portrait 2160x3840, guest off camera (정우 + character GIF) | default | [references/format-portrait-offcam.md](references/format-portrait-offcam.md) |
| landscape 3840x2160, both people on camera | two-shot | [references/format-landscape-twoshot.md](references/format-landscape-twoshot.md) |
| several audience-view clips of talks (conference recap), no conversation take | recap montage (planning first) | [references/format-recap-montage.md](references/format-recap-montage.md) |
| raw iPhone file (HLG) and the user asks for retouching | add-on | [references/retouch-from-raw.md](references/retouch-from-raw.md) |

Copy this checklist into your task list and tick it off:
```
- [ ] 0 intake: proxy, STT, speakers, read words.txt end to end
- [ ] 1 CUT → cut_preview.mp4 + cutlist.md → gate 1 (approval)
- [ ] 2 SUBS: Korean, then English translated from the final Korean → subs/final preview → gate 2
- [ ] 3 ENHANCE (optional modules from the format reference)
- [ ] 4 QA: fresh subagent with the reels-qa skill → fix every blocker/major → re-check
- [ ] 5 4K master on the Mac → verify.json all true → stills
```
Gates: show the preview and wait for "ㅇㅋ/괜찮아". "자동 승인 / 질문하지 말고 끝까지" (or `auto_approve`) → don't
wait, but still look at stills yourself. Feedback comes as "37초 컷이 어색해": every preview has a running timecode
(top-left); map it through the EDL, edit the plan, re-render, re-show.

Hard rules: never degrade the source (master = source resolution/fps/10-bit; overlays on top); the corrected input is
not re-graded; 반말 captions, no emoji; nothing on screen that wasn't said (cards, numbers); the user's instruction
beats any planning doc they share as reference. **Finance/investing topic** (stocks, ETF, 실적, 금리, 연금, 투자 판단) →
also use the `finance-reels-guard` skill at the plan, at gate 2 and before the 4K master; its 위험 items are blockers.

## Files
Bundle (Mac `~/capcut/reels-talk-edit/`, or the repo `skills/reels-talk-edit/`): `scripts/` (run them, don't
re-implement), `assets/` (fonts, character GIF, his_look.cube, yunet.onnx), `references/`, `eval/` (ep9 ground truth).
Cowork: pull once per session — `device_bash: cd $HOME/mnt/capcut/reels-talk-edit && tar czf ../_bundle.tgz --exclude='*.tgz' .`
→ `device_stage_files ~/capcut/_bundle.tgz` → `mkdir -p ~/rte && tar xzf /mnt/user-data/uploads/capcut/_bundle.tgz -C ~/rte`;
`S=~/rte/scripts`. Models once (GitHub releases only; HuggingFace is blocked): `bash $S/fetch_assets.sh` (repo) or
the sherpa-onnx whisper-turbo + zipformer-korean + silero_vad + ERes2Net downloads, then `make_hex_tokens.py` (sherpa's
whisper decoder drops multi-byte Hangul tokens without it).
Device limits (Mac VM): ffmpeg 4.4, 4 CPU, 3 GB RAM, **≤ 150 s per call, background jobs die**, no deletes without
permission. Cloud: 2 CPU, ffmpeg 6.1.
**Disk rule** (2026-10-25: ep10–12 left 5.6 GB of proxies, 4K pieces, `video_only.mp4`, wavs and old render versions in
his folders, ~1.9 GB per episode): every scratch file goes to the VM scratch `$HOME/rte_work/<NN>/` (outside `mnt/`,
~8 GB free, gone with the session). His folders receive only (a) the final `<NN>_final_4k.mp4`, (b) `<episode>/claude/`
= `plan.json` / `edl_final.json` / `cutlist.md` / `verify.json` (< 5 MB), (c) the reused transfer slot
`~/capcut/_claude_stage/` (`proxy<k>.mp4/.wav`, `pkg.tgz`), overwritten every episode. One render version: re-render
into the same `r4k`, never `vN/` copies. Previews: one file name per stage (`preview.mp4`), not v1…v10.

## 0. Intake (≈ 10 min for a 5-min take)
1. Input: `~/capcut/me/<NN_topic>/소스/`. **Corrected** = his CapCut export (`*보정*.mov`, `color_transfer=bt709`) →
   `--input sdr`, `grade.mode none`, `audio.mode passthrough`, retouch off. **Raw** = `IMG_xxxx.MOV` (HLG) → `--input hlg`.
2. Device: `python3 …/scripts/device_proxy.py <MOV> $HOME/rte_work/<NN>/prx<k> --stage $HOME/mnt/capcut/_claude_stage
   --slot <k> --budget 140` until `PROXY_DONE` (keeps the aspect: 720x1280 or 1280x720); stage `proxy<k>.mp4/.wav`.
3. Cloud: `analyze_audio.py src.wav stt.json` → `diarize.py src.wav diar.json` → `face_track.py src_720.mp4 face.npz`
   → `build_words.py --stt stt.json --diar diar.json --face face.npz --out words.json --transcript words.txt`.
   Read words.txt end to end (`i start-end H/G(logit) word [zipformer] !`).
4. STT gaps (pauses > 1.5 s inside talk, `!` words, numbers, names): `retranscribe.py src.wav T0-T1`. Whisper drops
   sentences and overlapped voices: add words / fix speakers in `words_patch.json`
   (`{"add":[{w,start,end}], "set_spk":[[t0,t1,"host|guest"]]}`) and re-run build_words `--patch`. When diarization
   collapses (one mic, two voices) decide speakers from content + the host's mouth logit.

## 1. CUT — the main job (gate 1)
`plan.json` with `"stage":"cut"`. Rules, numbers first:
- Logic: hook question → explanation → example → payoff → close. Target ≤ 96–100 s. When a take has two threads,
  keep one as the spine and only the part of the other that explains it.
- Drop: greetings before the first real question, filler-only runs, false starts of a turn, recaps, side branches,
  trailing words, a turn-opening "근데/아/그래서" + its pause. Keep in-sentence restarts (captions clean them).
- Pauses: cut only inside verified quiet (RMS ≤ floor + 6 dB, ≥ 0.28 s); pads 0.09 s in / 0.12 s out; 12 ms fades.
  Dead air that never measures as quiet (room noise): `cut: [[s0, s1]]` forces it.
- Speaker turns: **0.20 s** of silence (> 0.5 s reads as dead air); else the next shot pre-rolls at 3 % volume.
- Speed (pitch kept): asker 1.20–1.22 / explainer 1.27–1.30 / mixed 1.25, cap 1.32 (1.33 felt fast).
- Cold open (optional): `cold_open.spans` = one strong later line (2–5 s) first, then a **plain hard cut**.
- Edges: `retime` word times (trust the RMS envelope over STT), `mute_extra` for residual syllables; ≤ 12 tight cuts.
```
python3 $S/build_edl.py --plan plan.json --words words.json --rms stt_rms10ms.npy --face face.npz --out edl_cut.json
python3 $S/render.py prepare --edl edl_cut.json --out rcut --height 1280|720 --mode proxy --input sdr|hlg
python3 $S/render.py run --out rcut --src prx/src_720.mp4 --threads 2 --budget 100000
python3 $S/render.py audio --out rcut --audio prx/src.wav && python3 $S/render.py finish --out rcut --dest cut_preview.mp4
python3 $S/cutlist.py --edl edl_cut.json --words words.json --plan plan.json --out cutlist.md
```
`--height` = proxy frame height (1280 portrait, 720 landscape). Show `cut_preview.mp4` (≤ 30 MB) + `cutlist.md`.

## 2. SUBS — Korean, then English from the Korean (gate 2)
`"stage":"subs"`; write every caption in `plan.captions[]` (`t` source range or `w` word indices [+ `src`],
`speaker`, `text`, `en`).
- **Korean** (his style, measured on ep9): one line, ≤ 16 chars w/o spaces (≤ 21 with), ≥ 0.45 s, ≤ 13 chars/s; one
  clause per caption; drop fillers (음 어 막 그 이제 좀 약간 이렇게 그냥) and glue (근데/그래서/아) unless meaningful;
  collapse restarts; numbers and names exact; fix mishears from context + `[zip]`; 맞장구 gets its own caption.
- **English = translation of the final Korean caption, 1:1, same timing** (EN written from the audio drifts). Short
  spoken English, same numbers (100만 원 = 1M won), one sentence split over two KR captions reads as one sentence
  over two EN lines, no added facts. Check spans and quantities ("3년 뒤 → 내년" is not "up a year").
build_edl refuses captions over the limits; fix the plan, don't `--force` a final.

## 3. ENHANCE — optional, natural only (`"stage":"final"`, `"modules":{…}`)
Modules and their numbers are format-specific → the format reference. Overlay pacing (all cards/panels, 2026-10-24
"오버레이가 느리다"): first row ≤ 0.5 s after the card appears, rows 0.5–0.8 s apart, +0.3 s beat before the key line,
hold 1.5–2.0 s after the last row, ≤ 8 s per card; enter 6 frames, fades 4–5 frames. Always: transition = plain cut (flash/whoosh
read as cheap — only on request); never karaoke captions, emoji, random colours, SFX spam, face warps beyond
`head_shrink` 0.035. Evidence: [references/retention_research.md](references/retention_research.md).

## 4. QA — independent subagent (≤ 3 rounds)
Spawn a fresh `general-purpose` agent that does NOT get your plan or reasoning: "Use the reels-qa skill (repo:
skills/reels-qa/SKILL.md). VIDEO=… EDL=… RENDER_DIR=… SCRIPTS=… OUT=…/qa_rN MODELS=…" plus 3–4 lines on the format
(who is on camera, which modules are intentionally off). Give it the unrotated preview. Apply every blocker/major in
the plan, rebuild, re-render, re-run `qa_auto.py`. Ship with 0 blocker / 0 major (or the user accepts them).
Known false positives: whisper loops ("Q. Q. Q."), removed fillers, frame jumps that are fast hand gestures.

## 5. 4K master on the Mac
Package `scripts/` + `edl_final.json` (+ any track file the EDL names, e.g. `guest_face.npz`) → commit to the slot
`~/capcut/_claude_stage/pkg_<stamp>.tgz` (a re-commit of the same name can be skipped; `cat > pkg.tgz` it afterwards
so one copy remains) → extract into `$HOME/rte_work/<NN>/` (VM scratch), copy the bundle's assets there.
```
E=$HOME/mnt/capcut/me/<episode>; cd $HOME/rte_work/<NN>
python3 scripts/render.py prepare --edl edl_final.json --out r4k --height 3840|2160 --mode final --input sdr|hlg
python3 scripts/render.py run --out r4k --src $E/소스/<input>.mov --threads 4 --budget 150   # repeat until ALL_DONE
python3 scripts/render.py audio --out r4k --audio $E/소스/<input>.mov
python3 scripts/render.py finish --out r4k --dest $E/<NN>_final_4k.mp4                      # verify.json all true
mkdir -p $E/claude && cp edl_final.json r4k/verify.json $E/claude/                            # + plan.json, cutlist.md
```
If the session ends mid-render the scratch is gone: re-run from `prepare` (≈ 10–15 min for a 50–95 s reel).
x265 superfast crf 15: 1.6–3 fps → a 95 s reel ≈ 8–14 calls. Then stills from the 4K file → look → report the path.

## Regression check (after changing any rule or script)
Re-plan ep9 (`eval/gt9.json` = his own CapCut edit), render 720p, `python3 eval/evaluate.py --edl edl9.json --video out9.mp4`
(max 95; skill 75.7, his edit 93.9). A drop > 1 point is a regression.

## Plan keys
Full list with defaults: [references/plan-keys.md](references/plan-keys.md).
