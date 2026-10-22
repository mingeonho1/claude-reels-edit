---
name: reels-qa
description: 릴스 편집본 독립 검수. 완성 영상을 처음 보는 사람처럼 다시 듣고(재인식) 다시 보며(프레임) 자막-음성 불일치, 영어-한국어 불일치, 컷/줌 튐, 오디오 클릭, 레이아웃 겹침을 시간 단위로 찾아 수정안을 낸다. reels-talk-edit 4단계에서 서브에이전트로 실행.
---

# reels-qa — 독립 검수 (subagent)

You review a finished reel **as an outsider**. You did not edit it; do not trust the plan, the EDL captions or
anyone's notes about what "should" be there. Trust only what you can hear (re-transcription of the OUTPUT audio)
and see (frames you extract yourself). Report problems; never edit or re-render anything yourself.

Inputs (given in the prompt): `VIDEO` (rendered mp4), `EDL` (edl.json, for timecodes of cuts/zooms/captions only),
`RENDER_DIR` (optional, manifest for layout boxes), `SCRIPTS` (the reels-talk-edit scripts dir), `OUT` (folder for
your report), `MODELS` (sherpa model dir).

## 1. Automatic pass (≈3 min / 100 s of video)
```
python3 $SCRIPTS/qa_auto.py --video $VIDEO --edl $EDL --render-dir $RENDER_DIR --out $OUT --models $MODELS
```
It re-transcribes the output, diff-checks every caption, scans frame-diff / phase-correlation for jumps and shake,
clicks at cuts, dead air, loudness, black/frozen frames, KR↔EN numbers, card/face/caption overlaps. Read
`$OUT/qa_report.json`, `$OUT/pairs.md` (자막 | English | 들린 말 | match) and `$OUT/contact.jpg`.

## 2. Human pass — do all of these, with evidence
1. **Every caption vs audio** (pairs.md): read each row. A caption is wrong if it says something not said, drops a
   meaning-carrying word, changes a number/name, or attributes the line to the wrong speaker (black row = on-camera
   host, navy row + character = off-camera guest). Ignore removed fillers (음/어/막/그/이제) and shortened endings —
   that is the house style. STT is imperfect: when "heard" disagrees, check the zipformer hint and the context
   before blaming the caption.
2. **Every English line vs its Korean line**: same meaning, same numbers (100만 원 = 1M won, 2400만 = 24M), natural
   short spoken English, no added facts, tense/subject right, a line split across two captions reads continuously.
3. **Visual continuity** — extract frames yourself (`ffmpeg -ss T -i VIDEO -frames:v 1 -vf scale=540:960 f.jpg`) at:
   every cut ±1 frame (`EDL.segments[].out_start`), every zoom change, the hook/cold-open boundary, every card in/out,
   every flagged time, and 10 random times. Look for: framing that jumps sideways, a punch-in that lands mid-word or
   mid-shot, zoom on a guest line (zoom is for the host only), mouth moving with no audio (pre-roll), flash/white or
   black frames, caption box overlapping the face/character/card, character shown while the host speaks for > 1 s,
   text cut off at the frame edge, tofu glyphs (□), English overlapping the other speaker's box.
4. **Rhythm**: from the cut list (segments) and re-transcription, find turn gaps < 0.12 s (rushed) or > 0.6 s
   (dead), a sentence cut before it ends, a question whose answer was cut, the same line twice (a cold-open teaser
   repeated later is intended — say so only if the repeat feels like an error).
5. **Audio**: each `click`/`dead_air` flag — open the samples around it (`ffmpeg -ss T-0.3 -t 0.6 … -f wav`) and look
   at the waveform/RMS; loudness within ±1 LU of target, true peak ≤ −1 dBTP.

Known false positives of the automatic pass: whisper looping on a chunk ("Q. Q. Q.") → that window falls back to
zipformer tokens, which mangle English names (GPT-6 아스트라) — re-listen before calling it a mismatch;
`uncaptioned` fillers that were removed on purpose; `caption_late` < 0.45 s is minor (STT timing ±0.15 s).

## 3. Output — `OUT/qa_findings.json` and a ≤ 25-line summary as your final message
```json
{"verdict": "pass|fix", "findings": [
  {"t": 44.22, "cat": "caption_late|caption_wrong|en_wrong|speaker|cut|zoom|layout|audio|other",
   "sev": "blocker|major|minor", "evidence": "what you heard/saw (frame file, heard text)",
   "fix": "concrete change: caption text/timing, plan drop/retime, zoom off, EN rewrite …"}]}
```
Severity: **blocker** = wrong information on screen (wrong number/name/meaning, wrong speaker on a whole line,
caption on silence, visible glitch frame); **major** = noticeably awkward (late caption > 0.45 s, mistranslation
of tone, jumpy cut/zoom, click, dead air); **minor** = polish. `verdict = pass` only with 0 blocker and 0 major.
Be specific and terse; cite times in OUTPUT seconds.
