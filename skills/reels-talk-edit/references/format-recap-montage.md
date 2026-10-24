# Format: recap montage — audience-view clips of talks, no conversation take (ep12)

Input: several iPhone clips filmed from the audience (slides + a speaker on stage), raw HLG, PA sound picked up by the
phone (−30 … −33 LUFS, room echo, STT drops words). There is no host/guest take: the reel is built from the speakers'
own lines + information panels, optionally with his narration recorded afterwards.

## Planning comes first (ep12 flow, user-approved)
1. Materials: decks (Drive PDFs → Chrome `get_page_text`), event facts (web), STT of every clip, a frame sheet per clip.
   Write `materials/brief.md` (clip-by-clip transcript with timecodes + slide text, deck digests, channel, constraints).
2. 4 planner subagents (one angle each) → 1 judge subagent with a 100-point rubric that **checks every quoted
   timecode against the audio** → show the top 1–2 (+ the judge's merge proposal) → the user picks.
3. Timecodes from STT are often wrong by 0.5–1.5 s and sentences run past the last recognised word. Before cutting,
   confirm each speech span with the 10 ms RMS envelope and `retranscribe.py` on trial windows (ep12: the
   "할루시네이션" line ran to 20.75 s, STT said 19.07; "도태된 생각" was recognised as "두 팀에 생각한다").

## Build
- Concatenate the needed clips with stream copy (`-f concat -c copy`, same codec) → one source; audio = each clip's
  wav padded to its video length, then concatenated. Offsets = frame counts / 30. On the Mac do the same with the
  4K MOVs (no re-encode).
- Hand-built EDL (example: `examples/ep12/build_ep12.py`): blocks of `{clip, s, e, speed, gain, zooms, caps, panel}`.
  Speech blocks: speed 1.1–1.2, navy captions. B-roll blocks: `gain_db −20` (speaker murmur under a panel / his VO).
  A long pause inside one sentence: split the block into two sub-spans with the **same zoom** (a zoom change at an
  inner cut read as "zoomed twice", 2026-10-24).
- Zoom: one framing per sentence run. 1.2–1.35 on the slide title is fine; 1.6 into a slide box looked bad.
- Captions: speakers only. **No caption row for his narration** — the panel already carries it (VO captions looked
  odd, 2026-10-24).

## Layout on stage footage (2160x3840 px)
- Slide sits at y ≈ 0.40–0.70 of the frame, audience below, dark ceiling above.
- Header and hook: **white text with a 6–9 px black outline** (`style.header.color/outline`, `style.hook.fill/stroke_fill`)
  — the default black header vanished on the dark ceiling. Header l1/l2 top 430/546, hook cy 760, two-line hook via `\n`.
- Captions: one row at top 2930 (below the slide, above Instagram's bottom 15 %).
- Panels (`cards[].layout = "panel"`): full width 1940, top 1000–1300, bottom must stay above 2900.

## Panels — pacing rule (user feedback 2026-10-24, applies to every card/panel in every format)
| What | Number |
|---|---|
| first row after the panel appears | ≤ 0.5 s |
| between rows / list items / checkmarks | 0.5–0.8 s (strike-through 0.5 s after its row) |
| the key line (definition, punchline) | +0.3 s beat before it (his note: "AX 인재 =" felt rushed at 0.4 s) |
| hold after the last row | 1.5–2.0 s |
| one panel on screen | ≤ 8 s (ep12 ladder 14 → 8 s, checklist 6.5 → 3.6 s, question 7 → 3.8 s) |
| motion | enter 6 frames, row fade 4 frames, bar fill 0.35 s, exit 5 frames |
Wording: use the source's own words (Notion deck: "1단계 사고 파트너 / 물어보면 답해 준다"), not shortened paraphrases
("물어보면 답" read flat). Titles that invite action ("자가진단") beat "너는 어디야?".

## Narration (optional)
Script per panel block sized to the panel (≈ 7 syllables/s), one continuous take from his phone, blocks separated by
2 s. Split by STT, place at the block start, panel reveal times follow his words; the block length follows the take.
