# @geono_x 편집 스타일 스펙 (정답 = 9번 「트럼프 전쟁」 본인 CapCut 편집에서 실측)

All pixel values are for the 2160x3840 (4K portrait) canvas. Scale linearly for proxies (720x1280 = /3).
CapCut transform y (−1..1, + = up) → pixel center y = 1920 − y·1920.

## Format
- Source: iPhone 4K HEVC Main10, stored 3840x2160 with rotation=90 → displayed 2160x3840, 30fps, mono AAC (very quiet: avg −41 LUFS).
- Output: 2160x3840, 30fps, HEVC Main10 10-bit bt709 (CapCut export ≈ 20–30 Mbps), AAC stereo 48k.
- One static camera. On camera = **host (Geonho, 질문하는 사람)**. Off camera, sitting across = **guest (정우, Sydney Uni 금융, 설명하는 사람)**. The guest talks ~75% of the time.

## Cut + speed (episode 9: 171.5 s source → 88.3 s output, 30 segments)
- Kept 105.4 s of source (61%). Removed gaps between kept pieces: median ≈ 0.8 s, min 0.26 s; also dropped whole off-topic stretches (one 9.3 s, and the last ~28 s).
- Speed per segment: 1.1 default, 1.2–1.4 on long guest explanations. **User now wants 1.2–1.4 overall** (pitch preserved).
- Median shot 2.2 s (output time). Video scale 100% (no zoom) in his CapCut edit; an earlier automated pass added 110% hard-cut zoom on host-question segments (approved by user).
- Audio: CapCut volume ×10 on every segment + loudness target. His export measures −8.9 LUFS / +0.1 dBTP (too hot). Target for us: **−11 LUFS integrated, ≤ −1.0 dBTP**, voice cleaned (HPF, light denoise, gentle compression).

## Retouch (applied to every segment in CapCut, values 0..1)
- Color: temperature −0.198 (slightly cooler), sharpen 0.077, clarity 0.099, color_correct 0.077.
- Beauty: smooth 0.10, whitening 0.08, blemish 0.06, wrinkle 0.15, even 0.06, dark-circle 0.07, bright-eyes 0.04.
- Face reshape: small face 0.08, slim 0.05, V-line 0.07, chin 0.04, cheekbone 0.03, jaw(하관) 0.04, nose 0.05–0.09.
- User request (2026-10-21): "얼굴 색 보정 + 약간의 보정, 얼굴 크기 아주 조금 보정". Keep it subtle — must not look warped (background lines near the face must stay straight).

## Captions (font: Do Hyeon / 도현, DoHyeon-Regular.ttf)
- One caption = one short phrase (median 12 chars incl. spaces, max 21), shown 0.8–4.3 s (median 1.7 s), one line only. Text is cleaned speech: fillers (음, 어, 뭐, 그) dropped, stutters/repeats collapsed, meaning kept, spoken 반말 kept. No emoji.
- Box: solid white #FFFFFF rounded rectangle, height 175 px, corner radius ≈ 35 px, horizontal padding ≈ 24 px each side, centered at x = 1080. Glyph height of Hangul ≈ 97 px (Do Hyeon ≈ 110 px font size).
- **Host** (on-camera, Geonho): text #000000, box top y = 2146 (center y 2233 = 58.15% H).
- **Guest** (정우): text navy #252973 (37,41,115), box top y = 2373 (center y 2461 = 64.09% H).
- If both talk at once (e.g., guest 맞장구 "그치그치" under a host question), both boxes show at their own rows.
- Optional English sub (earlier automated pass): Do Hyeon 68 px, (236,236,236), soft shadow, centered, 6 px under the Korean box.

## Character (guest avatar)
- `assets/character.gif` (1024x1024, 40 frames × 80 ms loop, transparent) shown **while the guest is the one explaining**; hidden on host-only stretches. In ep.9 the GIF was on for 4 long blocks (5.1–16.3, 19.2–42.6, 45.3–54.7, 59.1–88.3 s): it stays on through short host 맞장구 inside a guest explanation and only drops for a real host question.
- Placement: width ≈ 1041 px, center (1828, 2375) → right edge bleeds off-frame, sits beside/over the guest caption row. Why a character at all: in a two-person talk format an empty side of the conversation reads worse than a drawn stand-in for the off-camera friend, so his character (`assets/character.gif`, not in the repo) speaks for him on screen.

## Header / hook
- 0 – 2.83 s (hook): big topic question top-center ("이란 전쟁 또?", Do Hyeon bold, black with white outline, ~260 px glyphs, center y ≈ 708, "flying line up" in-animation 1.0 s) + intro block mid-frame ("AI 3년차 개발자와 Sydney Uni 금융 경제" / "고품격 힐링 토크쇼", white with black outline, centers y ≈ 2239 / 2438) + a topic cut-out sticker bottom-center (episode specific, optional).
- 2.83 s → end (persistent header, black, no box, centered):
  - line 1 "01년생 AI 3년차 개발자와 Sydney Uni 금융 경제": glyph height 77 px, y 533–610, spans x 342–1815.
  - line 2 "고품격 힐링 토크쇼" (bold): glyph height 117 px, y 649–766, spans x 590–1569.
- First spoken line of the video is a host question hooking the topic (e.g., "끝난다더니 또 공격했다던데?").

## Info cards (earlier automated pass, user-approved)
- White rounded card r=40, soft shadow, title Do Hyeon 64 navy (38,42,120), red accent (214,58,58), top-right empty area clear of the face, ≥130 px right margin, enter 8 frames easeOutBack 0.9→1 + fade, exit 6-frame fade. Used where one speaker talks > 20 s with no visual change. Numbers must be source-checked.

## Things NOT to do (user rules)
- Never distort or degrade source footage beyond the requested subtle retouch; keep resolution/fps/10-bit at the final render.
- No emoji in captions. 반말 tone.
- Always preview at 720p + stills before the 30-min 4K render.
