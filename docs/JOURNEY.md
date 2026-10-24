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
`references/style_spec.md` and the ground truth `eval/gt9.json`.

## 1. v1 — a tournament between three agent teams (2026-10-21)

The first idea was to let agents compete: three teams got the same brief (my words, the measured style spec, a
retention-research note, ep9 raw + my final, ep10 raw) and each built a full skill. Scoring:

1. **ep9 auto score** (`eval/evaluate.py`, max 95) against my own edit: cut agreement (source-timeline F1, no cuts
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
| Punch-in ≤ 1 per 8–10 s, hard cuts only, no flash/whoosh | retention research ([`references/retention_research.md`](../skills/reels-talk-edit/references/retention_research.md)) + feedback |
| Cards ≤ 1 per 15–20 s, only numbers said on tape | research + "no fake facts on screen" |
| No karaoke captions, no emoji | my style + research on readability |

## 5. Testing

- **ep9 (my own edit)** = the regression test. Any rule change → re-plan ep9 → `eval/evaluate.py`; a drop of more
  than 1 point is a regression.
- **ep10** = same day, same framing, different content (GPT-6). 283.5 s → 97.3 s, 34 segments, 58 KR/EN captions,
  cold-open hook "AI 전문가인 척하기". The full plan is in [`examples/ep10/plan.json`](../examples/ep10/plan.json).
- **ep11** = a different framing (case 2, below).
- **Next**: two cameras, standing or walking shots.

## 6. What I'd tell someone adapting it

- Measure your own finished edit first (CapCut drafts are JSON). Rules from your own work beat generic advice.
- Let Claude make the editorial calls in a plan file; keep scripts deterministic. Every fix becomes a one-line edit.
- Put a gate after the cut. It is the decision that matters most and the cheapest one to change.
- Have a second agent that doesn't trust the first one listen to the output.

## 7. Case 2 — a different framing (ep11)

![ep11: the clockwise-rotated upload (left) and the landscape edit (right); the guest's face is mosaicked only in this still](img/ep11_frames.jpg)

ep11 「AI 빈부격차」 broke three assumptions at once: the take is **landscape** (3840x2160), **both people are on
camera**, and the guest is **not 정우** but a friend who teaches special education at a middle school. I also wanted
to try a format that's common right now: post the landscape video **turned 90° clockwise** so it fills a vertical
screen and the viewer tilts the phone to watch it. The guest is a friend, not a regular, so I first had his face **softly
mosaicked** (it didn't survive review — see below), and the show tagline became 저품격 ("low-class") 힐링 토크쇼.

What had to change, and why:

| Problem | What happened | Change |
|---|---|---|
| Proxy squashed the frame | the proxy step forced 720x1280 | scale by orientation (1280x720 for landscape) — never stretch |
| Layout was portrait-only | caption rows, header and hook were measured on a 2160x3840 frame | `orientation: landscape` = a 3840x2160 canvas with its own layout; captions centred above the bottom 15 % (after rotation that edge sits under Instagram's right-hand buttons), header/hook left of centre to clear my head |
| Rotation | my first try (`cclock`) put the image's top on the left; the reference reel I showed has it on the right | `rotate: clock` turns each finished frame inside the render, so the 4K master comes out 2160x3840 with no extra encode |
| Guest privacy | — | tried: `track_guest.py` follows the guest's face and the render pixelates it (block 10 → 12 % of face width), softens the blocks and feathers an ellipse. **Dropped** — see below |
| Guest character | 정우's GIF makes no sense when the guest is on screen | character module off |
| Who is speaking | diarization collapsed (617 vs 62 windows): two voices on one mic | speakers assigned from the content + my mouth motion (guest lines have low host logits), written into `words_patch.json` |
| Hook covered the first lines | the hook used to replace captions during its 3.4 s | `hook.keep_captions` — the title sits above the caption rows |
| Dead air that wasn't "quiet" | 0.8 s between two speakers read as room noise, so no cut | `plan.cut` forces a cut through a source span |

The take itself felt a bit stiff, so the cut is aggressive: 219.5 s → 94.1 s. Two threads were in the take — a
personal tip (lower your reasoning level, you're burning tokens) and the news (China may allow some Nvidia chips; AI
compute is scarce). I kept the tip as the spine, kept the news only where it explains *why* limits exist, dropped the
operating-cost and pricing loops, and ended on the tip again.

The QA agent found 0 blockers and 2 majors on round 1: 0.8 s of dead air after "쓰지" (the STT had the word 0.5 s too
early, so the cut sat in the wrong place) and a double jump cut around a lone "그치". Both were fixed in the plan;
the rest were English polish and caption timing. See [`examples/ep11`](../examples/ep11).

### The face mosaic that didn't make it

On stills the mosaic looked right ("은은하게 보일듯말듯" — the face shape there, features unreadable). In motion it
didn't: **whenever he moved, the mosaic shimmered and looked like it was breaking up.** Why, looking at the code:

- the block grid was anchored to the tracked face box, so every time the box moved a few pixels every block
  re-sampled a different patch of skin → the whole patch "boils";
- the block size followed the face width frame by frame, so the grid also changed scale;
- the track came from the 720p proxy (1 px there = 3 px at 4K), detected every 2nd frame and smoothed over only
  0.4 s, so small tracking noise turned into visible wobble; the 1.26× speed-up made it faster.

Making the blocks stronger (10 % → 12 %) only made the shimmer easier to see. The final 4K ships **without a mosaic**;
the code stays in the repo but off by default. If it comes back, it needs a grid fixed to the frame, one block size
per take and much heavier temporal smoothing — or a plain soft blur instead of blocks — and it has to be judged on
moving video, not stills.

The 4K master renders at ~3 fps on the Mac: 2822 frames, 94.1 s, 2160x3840 HEVC 10-bit, −10.5 LUFS.

What I learned about the skill itself: a new framing should not be a new skill. The workflow didn't change at all;
only layout, speakers and upload format did. So the skill now keeps the workflow in SKILL.md and moves each format
into its own reference file (see the README's *Skill design* section).


## 8. Case 3 — a conference recap with no conversation take (ep12)

A reel from 5 clips I filmed in the audience at DMI 2027. There was no conversation to cut, so this one started with **planning**.

- **Planning:** the 6 decks and the transcripts of all 5 clips went into one brief. 4 planner subagents each wrote a plan from a different angle (AX-talent definition / numbers + self-check / developer's take / Adobe's rebuttal). A judge agent scored them and checked every quoted speaker timecode against the audio (78 / 77 / 75 / 74). I took the judge's merge of #1 and #2, with no extra shooting; my narration gets recorded later.
- **Editing:** two clips were concatenated without re-encoding into one source, with a hand-built EDL ([`examples/ep12/build_ep12.py`](../examples/ep12/build_ep12.py)). The speaker's own lines alternate with full-width info panels whose rows reveal on a schedule.
- **Dark stage:** the default black header disappeared against the ceiling, so it became white with a black outline.

Every piece of feedback from preview v1 to v9 is logged in [`examples/ep12/feedback.md`](../examples/ep12/feedback.md). What went into the skill:

| My feedback | Rule in the skill |
|---|---|
| "the hallucination line cuts off" | STT ended the sentence 1.7 s early → confirm speech spans with RMS + re-transcription windows |
| "the deck's own words land better" | panel text quotes the source, no shortening |
| "no captions on my narration" | recap format: narration gets no caption row |
| "it zooms twice" | one framing per sentence run, ≤ 1.35x on slides |
| "the overlays are slow" | **every card/panel:** first row ≤ 0.5 s, rows 0.5–0.8 s apart, +0.3 s before the key line, hold 1.5–2 s, ≤ 8 s per panel |

The overlay pacing rule isn't specific to this episode: it's now a common rule in step 3 of SKILL.md.


### Disk rule (found while tidying up ep10–12)

After ep10–12 my `claude/` folders held 5.6 GB of work files (~1.9 GB per episode): 4K render pieces, an audio-less intermediate (`video_only.mp4`), wavs, proxies and leftover render versions (v2/v3/v4…). The only things worth keeping were a few MB of plan/EDL. Now every work file is made in the Mac VM's scratch space (`$HOME/rte_work`, gone when the session ends), and my folders get only the final 4K, a small record in `claude/` (< 5 MB) and a transfer slot that is overwritten every episode (`~/capcut/_claude_stage`).
