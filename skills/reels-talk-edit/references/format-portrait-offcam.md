# Format: portrait, guest off camera (default — ep9, ep10)

One static vertical iPhone on Geonho (**host**, asks; black caption row). 정우 sits across the table off camera
(**guest**, explains; navy caption row + his character GIF). Canvas 2160x3840 (`--height 1280` proxy / `3840` master).

## Layout (measured from his ep9 CapCut edit — style_spec.md)
- Caption: Do Hyeon 110 px in a white box h175 r35 pad 26, centre x 1080; host top 2146 black, guest top 2373 navy
  #252973. Pretendard fallback for glyphs Do Hyeon lacks ('·').
- English: Do Hyeon 68 px (236,236,236), 3 px dark outline + soft shadow, 6 px under its box; above the box only when
  both speakers' boxes are on screen for > 40 % of the caption. Speaker hand-overs < 0.3 s are trimmed.
- Header: "01년생 AI 3년차 개발자와 Sydney Uni 금융 경제 / 고품격 힐링 토크쇼", line 1 1473 px wide at y 533, line 2 979 px at y 649;
  black + **white 6 px outline** by default (ep13: plain black vanished on his hair / the navy blinds). Line 2 may be
  re-worded per episode (`style.header.line2`, keep the width ∝ characters: ep13 "뷰티 힐링 토크쇼" → `l2_w` 870).
- Hook: Do Hyeon 260 px black + 7 px white outline, centre y 708, fly-up; ≤ 10 Hangul ("AI 전문가인 척하기"). He prefers a
  topic label ("투자 기초 : ETF") over a quoted line from the talk ("ETF는 과일바구니" → "별론데"); without a cold open use
  `hook: {text, intro: false, keep_captions: true}` so the first question keeps its caption.

## Modules (defaults ON)
- `header`: the two lines above, from the end of the hook.
- `hook`: title over the cold open; the intro block only without a cold open.
- `character`: guest GIF (1041 px, centre **1620**,2375 — ep13 "좀 더 가운데로"; captions and English are drawn on top of it) while the guest explains; stays through ≤ 1.3 s host 맞장구, leaves
  on a real host question; blocks < 1.5 s dropped (`char_merge_gap` 3.0).
- `zoom` (`zoom_mode: host_cut`): punch-in 1.08 **only as a hard cut where the host's black caption starts** (±0.45 s),
  out at the next cut near the guest's first caption; ≥ 1.5 s on screen; ≤ 1 per 8 s; one fixed centre. Never mid-
  sentence, never on guest lines, never animated (user: mid-shot zooms looked awkward).
- `cards`: ≤ 1 per 15–20 s, 2.5–6 s, triggered by a spoken number, only facts said on tape; title ≤ 9 Hangul, 1–4
  lines ≤ 9 Hangul, optional accent number; arrow follows the sign (부족/감소 → blue ▼, up → red ▲); no CTA cards.

- `notes` (소자막, finance reels): sources, dates, definitions and risk notices the finance guard asks for — Pretendard 44 px,
  dark 72 % box, top 2770 (above Instagram's bottom UI), 1–2 lines ≤ 25 자, ≥ 2 s, one at a time, under the line they
  qualify; never on screen together with a spoken number they contradict (show "1928~2025" after the "1927년부터"
  caption). Prefix "※".
- `texts` (optional asides): small "( … )" lines on the host's hair for a visible action (ep13 팩 붙이는 동안
  "( 편하게 듣는 힐링 토크쇼 )", 다 붙이고 "( ㅎㅎ )"): Do Hyeon 62 px white + dark outline, ≈ (1320, 1000), clear of the header.
- Ending: never stop on a bare answer — keep a short closing reaction from the tape ("좋다", "고마워") + ~0.5 s tail.

## Speakers
Bigger diarization cluster with less on-camera mouth motion = guest. Speed: host 1.18 / guest 1.25 / mixed 1.21.

## QA brief for the subagent
"Portrait. Host on camera (black row), guest off camera (navy row + character GIF). Zoom is host-only by design."
