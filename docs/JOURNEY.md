# How this skill was built — and why it looks the way it does

English | [한국어](JOURNEY.ko.md)

## 0. The problem

My channel [@geono_x](https://www.instagram.com/geono_x/) is a talk format: one static iPhone on me (I ask), my friend
정우 off camera across the table (he explains), a cartoon character of him on screen while he talks, Korean
captions plus a small English line. A 3–5 minute take becomes a ~90 s Reel.

Planning and shooting are quick. The editing is slow, and almost all of it goes to **cutting** (finding where
every sentence really starts and ends, removing fillers and false starts, tightening the turns) and **captions**
(one clause at a time, then the English line).

The reference for "my style" is ep9, 「트럼프 전쟁」 — [the reel I edited myself in CapCut](https://www.instagram.com/reel/DeIZ4g9J8vI/).
CapCut stores a project as a plaintext JSON draft, so instead of eyeballing it I could read the exact segment
boundaries, speed per segment, caption font/size/position/colour and character timing out of it. That became
`ref/style_spec.md` and the ground truth `ref/gt9.json`.

## 1. v1 — a tournament between three agent teams (2026-10-21)

The first idea was to let agents compete: three teams got the same brief (my words, the measured style spec, a
retention-research note, ep9 raw + my final, ep10 raw) and each built a full skill. Scoring:

1. **ep9 auto score** (`ref/evaluate.py`, max 95) against my own edit: cut agreement (source-timeline F1, no cuts
   inside speech), pace, caption text and form, speaker/character accuracy, render conformance, loudness.
2. **ep10 judge score**: a judge agent watched each team's ep10 render (same composition, new content) for caption
   correctness, cut quality, style fidelity, retention devices, retouch and audio.
3. **Skill quality**: could another agent actually follow the SKILL.md?

Two rounds (round 2 = each team saw its scores and improved). Round 1: C 82.1, A 80.4, B 78.7. Final: **C 83.5** vs A 81.3.
On ep9 the winning skill scored 75.7; my own edit scores 93.9 on the same evaluator (caption text is low by design —
I paraphrase when I caption).

That v1 did *everything* from the raw iPhone HLG file: a colour grade, skin smoothing, face slimming, a voice chain,
zoom punch-ins, flash transitions, cards and the character.

## 2. What went wrong — my feedback on v1

I watched the previews and gave notes one by one (quotes are mine, translated from Korean).

### 2a. Face retouch: every fix moved the problem somewhere else

My first ask was modest: *"a bit of face colour correction and light retouching, make the face just a little
smaller."* v1 did it the way you would in ffmpeg — a colour grade, bilateral skin smoothing inside a face mask, and
a face-slimming warp around the jaw and cheeks.

| Round | What I said | What was going on | What changed |
|---|---|---|---|
| 1 | *"Retouch the face just 5 % more."* | the effect was too subtle to see | stronger smoothing and slimming |
| 2 | *"The frame feels more zoomed in than the original — Instagram crops it again, so a zoomed-in base looks bad."* | the base framing had been cropped tighter than the source | base framing back to the full source frame; zoom only as an occasional punch-in |
| 3 | *"The face retouch here looks unnatural. Just shrink the whole head a bit."* (with screenshots) | the per-region slim bent the jawline and cheeks differently, so the face shape looked off | slimming removed; one uniform 3.5 % head shrink |
| 4 | *"Skin smoothing at 0.60 is fine."* | — | smoothing blend 0.60 |
| 5 | *"When there's no zoom and 정우 is talking, my neck looks broken. Why?"* | ffmpeg 4.4's `remap` only does nearest-neighbour sampling, and the warp went through 4:2:0 ↔ 4:4:4 conversions, so the edge of the warped area tore at the neck | warp moved to a bilinear `cv2.remap` in a pipe |

Each round fixed what I pointed at, but a hand-built retouch has no face model: it doesn't know where the jaw, the
neck or the hair is, so any geometric warp risks tearing a boundary somewhere, and smoothing that's strong enough to
see starts to look waxy. CapCut's beauty tools are face-aware.

### 2b. Voice: louder also meant noisier

The raw takes were very quiet (≈ −41 LUFS on a lav mic), and I asked *"can you make just our voices a bit louder?"*.
v1 used a classic voice chain — high-pass 80 Hz, FFT denoise, EQ (−2 dB at 300 Hz, +2 dB at 3 kHz), a 3:1
compressor — then about +30 dB of gain and a limiter.

- With one mic, "only our voices" is not something you can isolate. Pushing the level pushed the room too, and
  정우 is off-mic across the table, so his voice comes with more room sound than mine.
- The denoise and compressor change the voice's texture; at this much gain the processing becomes audible.
- Tight cuts with fully muted pre-roll left digital-silence dropouts in the room tone; they had to become 3 %
  instead of 0 %.

It got loud enough and it passed the loudness meter, but it didn't sound like CapCut's voice enhance on the same
clip.

### 2c. Editing rhythm

| Feedback | Cause | Fix (now a rule) |
|---|---|---|
| "Slightly too fast; slow it down just a touch" | avg 1.33× | host 1.20 / guest 1.30 / mixed 1.25, cap 1.32 |
| "The gap between 정우 and me is too short — keep at least ~0.1 s" | turns butted together at ~0.05 s | 0.20 s silence at every speaker change (natural turn-taking gap ≈ 200 ms) |
| "The zoom-ins feel awkward — only zoom when the black caption (my line) appears" | punch-ins mid-shot, also on 정우's lines | 1.08× only as a hard cut exactly where *my* line starts, out at the next cut, ≤ 1 per 8 s |
| "Put 'can't the Claude I use already do that? what's different if I pay more?' up front as the hook, with a transition feel" | — | multi-span cold open; a plain hard cut into the episode (flash + whoosh looked cheap → only on request) |
| "The cut around 'one date changed, is that so big?' feels awkward" | the cut into that line landed awkwardly | re-cut with `retime` in the plan; edges follow the RMS envelope, not STT word times |
| "English subtitles have to be based on the Korean ones" | EN was written from the audio and drifted from the caption | EN = 1:1 translation of the *final* Korean caption, same timing |

### 2d. The verdict

After all of that I ran a full test and the answer was still: **it looks awkward.** Each fix was right on its own,
but a stack of small automated "improvements" — grade, smoothing, warp, voice chain, zooms, flashes — didn't add up
to something that looked like my edit. Meanwhile, doing voice, face, colour and sharpness in CapCut took me about
two minutes and looked better. That is what led to v2.

## 3. v2 — redesign around the bottleneck (2026-10-22)

Three observations changed the design:

1. **CapCut's look pass is fast and better.** Voice cleanup, face, colour and sharpening take ~2 minutes with
   CapCut's tools. I measured how close a rebuild could get: a 3D LUT fitted on 25 raw→export frame pairs brought
   background colour error from 8.8 to 2.75 /255, and face tone from 10.6 to 6.1 /255 — about 85–90 % of CapCut.
   Close, but CapCut's face-shape tools aren't reproducible, and 2 minutes isn't a bottleneck. So the input is now
   **my CapCut-corrected export**, used as-is (no re-grade, audio level only). Rebuilding the look from the raw
   file stays as an *optional* stage R.
2. **Use AI only where the time goes**: cuts, then captions. Everything else is optional and must be invisible.
3. **Gates instead of one big run.** I'd rather approve a cut than fix a finished video. Each preview carries a
   running timecode so "37초 컷 어색해" maps straight back to a source time.

Result: a staged workflow, **one agent following it in order**. (Multi-agent was great for *building* — the
tournament surfaced good rules fast — but for *running*, one agent with a clear procedure is more reliable.)

```
0 intake → 1 CUT ─gate→ 2 SUBS (KR → EN) ─gate→ 3 ENHANCE (optional) → 4 QA subagent → 5 4K master
```

### Why an independent QA agent

The editing agent believes its own plan. The QA agent gets only the rendered video and the EDL timecodes, and:
re-transcribes the *output* audio, diffs every caption against what is heard, checks every English line against
its Korean line (numbers especially), extracts frames at every cut/zoom/card, scans frame-difference and phase
correlation for jumps and shake, looks for clicks at cuts, dead air, loudness, black/frozen frames and overlaps.
On ep10, round 1 found a wrong English number ("move the wedding up a year" when the story was 3 years → next year),
a cut 0.1 s into the next word, 25 ms residual syllables after tight cuts and 0.84 s of dead air — none of which
I'd spotted in the plan. Round 2: 0 blockers. See [`examples/ep10/qa_round1_findings.json`](../examples/ep10/qa_round1_findings.json).

## 4. Where the numbers come from

| Rule | Source |
|---|---|
| Caption form (≤ 16 chars, one clause, ≥ 0.45 s, ≤ 13 cps), box sizes and positions | measured from my ep9 CapCut draft |
| Speed 1.2–1.32 | my ep9 (1.2–1.4) + feedback "slightly slower" |
| Turn gap 0.20 s | conversation-analysis turn-taking gap (~200 ms) + feedback |
| Cut only inside quiet ≥ 0.28 s, pads 0.09 / 0.12 s, 12 ms fades | avoids clipped consonants and clicks (checked by QA) |
| Punch-in ≤ 1 per 8–10 s, hard cuts only, no flash/whoosh | retention research ([`ref/retention_research.md`](../skills/reels-talk-edit/ref/retention_research.md)) + feedback |
| Cards ≤ 1 per 15–20 s, only numbers said on tape | research + "no fake facts on screen" |
| No karaoke captions, no emoji | my style + research on readability |

## 5. Testing

- **ep9 (my own edit)** = the regression test. Any rule change → re-plan ep9 → `ref/evaluate.py`; a drop of more
  than 1 point is a regression.
- **ep10** = same day, same framing, different content (GPT-6). 283.5 s → 97.3 s, 34 segments, 58 KR/EN captions,
  cold-open hook "AI 전문가인 척하기". The full plan is in [`examples/ep10/plan.json`](../examples/ep10/plan.json).
- **Next**: different framings — other seating, a second camera angle — to see which rules are format-specific.

## 6. What I'd tell someone adapting it

- Measure your own finished edit first (CapCut drafts are JSON). Rules from your own work beat generic advice.
- Let Claude make the editorial calls in a plan file; keep scripts deterministic. Every fix becomes a one-line edit.
- Put a gate after the cut. It is the decision that matters most and the cheapest one to change.
- Have a second agent that doesn't trust the first one listen to the output.
