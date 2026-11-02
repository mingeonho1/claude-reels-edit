---
name: reels-talk-edit
description: "@geono_x 릴스를 촬영본에서 편집한다: 2인 토크(세로·가로 투샷 90° 회전 업로드)와 컨퍼런스 객석 영상 후기 몽타주(기획 서브에이전트+심사 먼저). 컷 미리보기·승인 → 한국어+영어 자막·승인 → 연출(선택) → 독립 검수 → Mac 1080p 마스터 → 인스타 본문 3안. '릴스 편집', 'N번 컷편집/자막', '컨퍼런스 다녀온 릴스'에 사용."
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
- [ ] 1 CUT → cut_preview.mp4 + cutlist.md → flow check → gate 1 (approval)
- [ ] 2 SUBS: Korean, then English translated from the final Korean → subs/final preview → gate 2
- [ ] 3 ENHANCE (optional modules from the format reference)
- [ ] 4 QA: fresh subagent with the reels-qa skill → fix every blocker/major → re-check
- [ ] 5 1080p master on the Mac → verify.json all true → stills
- [ ] 6 Instagram 본문 3안 (guard-checked) → claude/instagram_caption.md
```
Gates: show the preview and wait for "ㅇㅋ/괜찮아". "자동 승인 / 질문하지 말고 끝까지" (or `auto_approve`) → don't
wait, but still look at stills yourself. Feedback comes as "37초 컷이 어색해": every preview has a running timecode
(top-left); map it through the EDL, edit the plan, re-render, re-show.

Hard rules: never degrade the source beyond the one master downscale (master = **1080x1920** by default, 2026-11-03
"1080p로 해도 되겠다, 4K 렌더링 너무 오래 걸려": lanczos once from the 4K source, source fps, 10-bit; 4K only when he
asks; overlays on top, never upscale or re-grade); the corrected input is
not re-graded; 반말 captions, no emoji; nothing on screen that wasn't said (cards, numbers) — except `notes` 소자막
(sources, dates, definitions, risk notices) and asides he asks for (`texts`); the user's instruction
beats any planning doc they share as reference. **Finance/investing topic** (stocks, ETF, 실적, 금리, 연금, 투자 판단) →
also use the `finance-reels-guard` skill at the plan, at gate 2 and before the master; its 위험 items are blockers.

## Files
Bundle (Mac `~/capcut/reels-talk-edit/`, or the repo `skills/reels-talk-edit/`): `scripts/` (run them, don't
re-implement), `assets/` (fonts, character GIF, his_look.cube, yunet.onnx), `references/`, `eval/` (ep9 ground truth).
Cowork: pull once per session — `device_bash: cd $HOME/mnt/capcut/reels-talk-edit && tar czf ../_bundle.tgz --exclude='*.tgz' .`
→ `device_stage_files ~/capcut/_bundle.tgz` → `mkdir -p ~/rte && tar xzf /mnt/user-data/uploads/capcut/_bundle.tgz -C ~/rte`;
`S=~/rte/scripts`. Models once (GitHub releases only; HuggingFace is blocked): `bash $S/fetch_assets.sh` (repo) or
the sherpa-onnx whisper-turbo + zipformer-korean + silero_vad + ERes2Net downloads,
then `make_hex_tokens.py` (sherpa's whisper decoder drops multi-byte Hangul tokens without it).
Device limits (Mac VM): ffmpeg 4.4, 4 CPU, 3 GB RAM, **one call ≤ the device_bash timeout (45–180 s, varies by session:
keep `--budget` ≤ timeout − 25 s), background jobs die**, no deletes without
permission. Cloud: 2 CPU, ffmpeg 6.1.
**Disk rule** (2026-10-25: ep10–12 left 5.6 GB of proxies, 4K pieces, `video_only.mp4`, wavs and old render versions in
his folders, ~1.9 GB per episode): every scratch file goes to the VM scratch `$HOME/rte_work/<NN>/` (outside `mnt/`,
~8 GB free, gone with the session). His folders receive only (a) the final `<NN>_final_1080p.mp4`, (b) `<episode>/claude/`
= `plan.json` / `edl_final.json` / `cutlist.md` / `verify.json` / `instagram_caption.md` (< 5 MB), (c) the reused transfer slot
`~/capcut/_claude_stage/` (`proxy<k>.mp4/.wav`, `pkg.tgz`), overwritten every episode. One render version: re-render
into the same `r1080`, never `vN/` copies. Previews: one file name per stage (`preview.mp4`), not v1…v10.

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
- Logic: hook question → explanation → example → payoff → close. Aim ≤ 100 s, but **flow beats length** (ep13
  2026-11-02: 97 s with gaps in the logic → 116 s restored, "훨씬 좋다"). When a take has two threads, keep one as the
  spine and only the part of the other that explains it.
- **Flow check — every drop, before gate 1** (his rule: "빼려면 어색하지 않게 빼야 해, 어색하면 안 빼는 게 낫다").
  Read each cut as "last line before ‖ first line after" and restore (the whole span, or just its bridge word) when:
  1. the next line points at removed content ("이런 뉴스가 터져" ‖ "근데 내 바구니에…" with the news itself cut);
  2. a question/listing loses its answer or an answer loses its question; a 맞장구 ("엄청 높네") is followed by a
     line that ignores it — keep the other person's short reply ("그치.") before the next point;
  3. an analogy/example loses its payoff (the "그래서 다른 과일은 괜찮으니까" line);
  4. the topic jumps with no bridge — keep "그 다음에 / 그래서 / 예를 들어서 / 근데" that open the next point;
  5. a list is cut off mid-intonation — end it at its natural end ("…, 뭐 QQQ.").
  Clean drops: repeats of a sentence just said, restarts, echoes of the other speaker, fillers, side remarks whose
  neighbours still connect. A finance-guard 위험 line is fixed with a 소자막/caption disclaimer when cutting it breaks
  the flow (ep13 "방어율이 좋다라는 거네" stayed). Gate-1 report lists every whole-content drop in one line each
  (원본 시간 · 누가 · 무슨 말 · 왜) so he can veto, and asks.
- Drop: greetings before the first real question, filler-only runs, false starts of a turn, recaps, side branches,
  trailing words, a turn-opening "아" + its pause. Keep in-sentence restarts (captions clean them).
- Pauses: cut only inside verified quiet (RMS ≤ floor + 6 dB, ≥ 0.28 s); pads 0.09 s in / 0.12 s out; 12 ms fades.
  Dead air that never measures as quiet (room noise): `cut: [[s0, s1]]` forces it.
- **Every cut keeps ≥ 0.10 s silence in the output** (`cut_gap` 0.10, 2026-11-01: "말 끝내고 0.1초 쉬고 진행해야지,
  컷마다 틈이 없어서 어색해"); speaker turns **0.20 s** (> 0.5 s reads as dead air). build_edl adds it by extending
  through quiet, else a ≤ 0.30 s muted pre-roll. A segment ends after the last syllable's decay (energy dip), never
  mid-syllable — check tight ends in the 10 ms RMS and `retime` the word end until `src_end` lands on the dip.
- **Speaker change = the outgoing line finishes first** (repeated feedback; ep13 0:57 "아니, 다른 것도 있지" lost its
  rising "지?" because the cut sat on an inner dip 0.15 s before the real end): at every turn, check the outgoing
  speaker's last 0.3 s — host: mouth logit still > 1 after `src_end`; anyone: a burst > floor + 20 dB before the other
  voice, or whisper on `[end-0.9, end+0.2]` hearing more (있지 → 있지?) — and `retime` the last word so `src_end`
  lands on the dip after the tail, even if it sits 0.03 s before the other voice; trim the incoming speaker's onset
  (`mute_extra`), never the outgoing tail. `check_tails.py` lists suspects (it caught the ep13 case: TAIL 70 ms,
  host mouth 1.02); `src_end` moves in output-frame steps (speed/30 s), so try 2–4 `retime` values and re-check.
- Speed (pitch kept): asker (host) 1.21 / explainer (guest) 1.18 / mixed 1.20, cap 1.32 — the explainer carries
  the content, so he is the slowest; if it still feels fast, lower the explainer to 1.15 first. Set
  `target_out` above the expected length: when over target, build_edl raises every speed up to 1.40 by itself.
- Close: never end on a bare answer — keep a short closing reaction from the tape ("좋다", "고마워", ep13 "너무 그냥
  끝내는 느낌") with ~0.5 s tail (`retime` its end later).
- Cold open (optional): `cold_open.spans` = one strong later line (2–5 s) first, then a **plain hard cut**.
- Edges: `retime` word times (trust the RMS envelope over STT), `mute_extra` for residual syllables; ≤ 12 tight cuts.
```
python3 $S/build_edl.py --plan plan.json --words words.json --rms stt_rms10ms.npy --face face.npz --out edl_cut.json
python3 $S/check_tails.py --edl edl_cut.json --rms stt_rms10ms.npy --face face.npz   # MID / TAIL flags -> listen, retime
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
Known false positives: whisper loops ("Q. Q. Q."), removed fillers, frame jumps that are fast hand gestures,
caption_mismatch at turns where the STT window clips a word (re-check with a narrow `retranscribe.py` window), muted
pre-roll frames at cuts (`cut_gap`), `notes`/`texts` overlays (not speech). Tell the QA agent these are intentional.

## 5. Master on the Mac (1080p default)
Package `scripts/` + `edl_final.json` (+ any track file the EDL names, e.g. `guest_face.npz`) → commit to the slot
`~/capcut/_claude_stage/pkg_<stamp>.tgz` (a re-commit of the same name can be skipped; `cat > pkg.tgz` it afterwards
so one copy remains) → extract into `$HOME/rte_work/<NN>/` (VM scratch), copy the bundle's assets there.
```
E=$HOME/mnt/capcut/me/<episode>; cd $HOME/rte_work/<NN>
export REELS_X265_PRESET=medium REELS_X265_CRF=14            # 1080p: slower preset is affordable, looks cleaner
python3 scripts/render.py prepare --edl edl_final.json --out r1080 --height 1920 --mode final --input sdr|hlg   # landscape: 1080
python3 scripts/render.py run --out r1080 --src $E/소스/<input>.mov --threads 4 --budget 150   # repeat until ALL_DONE
python3 scripts/render.py audio --out r1080 --audio $E/소스/<input>.mov
python3 scripts/render.py finish --out r1080 --dest $E/<NN>_final_1080p.mp4                    # verify.json all true
mkdir -p $E/claude && cp edl_final.json r1080/verify.json $E/claude/                          # + plan.json, cutlist.md
```
1080p (ep13, he uploads 1080p and liked the result): the 4K source is downscaled once (lanczos, before overlays,
10-bit HEVC) → ~3 fps on the Mac, 117 s ≈ 9 calls of `--budget 150`, ~18 Mbps. 4K on request: `--height 3840|2160`,
`r4k`, `<NN>_final_4k.mp4`, x265 superfast crf 15, 1.6–3 fps → a 95 s reel ≈ 8–14 calls.
If the session ends mid-render the scratch is gone: re-run from `prepare`. Then stills from the master → look →
report the path.

## 6. Instagram 본문 — 3 options with every final master
Write `<episode>/claude/instagram_caption.md` with **3 options** (A 질문 훅 · B 숫자 훅 · C 분위기/장면 훅; mark one
추천). His style (2026-11-03, reference: big finance creators): short, punchy, friendly 해요체; line 1 = a hook ≤ 25 자
with at most one emoji; 2–4 short lines that retell the reel's one idea (the analogy, one number that was said);
1 closing line; then the finance block; 5 hashtags. Emoji ≤ 3 in total (the no-emoji rule is for on-video captions).
Finance reels: never "투자에 참고하세요 / 사세요 / 담아요" (권유), only numbers that are on tape or in the 소자막 with
the same source; the block = `※ 투자 권유 아님 · <상품>도 원금 손실 가능 · 과거 수익률은 미래를 보장하지 않아요` +
`출처: …`; an ambassador company named anywhere → first line starts with `[광고]`. Run the 3 options through
finance-reels-guard (checkpoint C covers the caption) before handing them over; ep13 guard notes: say 명목 next to a
long-run return, give a period + basis for every recovery number, no "이거면 끝" over-claims, and recommend the option
that states the downside.

## Regression check (after changing any rule or script)
Re-plan ep9 (`eval/gt9.json` = his own CapCut edit), render 720p, `python3 eval/evaluate.py --edl edl9.json --video out9.mp4`
(max 95; skill 75.7, his edit 93.9). A drop > 1 point is a regression.

## Plan keys
Full list with defaults: [references/plan-keys.md](references/plan-keys.md).
