# Format: landscape two-shot, both on camera (ep11)

16:9 take (ffprobe `width > height`), host and guest both in frame. Canvas 3840x2160 (`--height 720` proxy /
`2160` master), plan `"orientation": "landscape"`.

## Upload as "tilt your phone" vertical
`"rotate": "clock"` turns every finished frame 90° clockwise → 2160x3840. The image's top lands on the phone's right
edge and the text reads top-to-bottom, so a viewer tilts the phone to the left and watches it full-screen (the format
the user pointed at, 2026-10-23). This is an occasional format, not the default.
- Previews: cut/subs in landscape (easier to judge); the final preview with `render.py prepare … --rotate`.
- Master: `prepare --height 2160 --mode final` rotates inside each piece — no extra encode. verify.json expects 2160x3840.
- `"rotate": "cclock"` exists but is the wrong way for this format.

## Layout (LANDSCAPE_STYLE in overlays.py; px at 4K)
- Captions centred (cx 1920): host row top 1330 (black), guest row top 1550 (navy), max width 2600; English under the box.
  Kept off the bottom 15 %.
- Header and hook left of centre at the top (`style.header.cx` 1350, `style.hook.cx` ≈ 1180) so they clear the host's
  head on the right; after a clockwise turn the top edge sits above Instagram's right-hand buttons.
- `hook.keep_captions: true` — the title sits above the caption rows, so the first lines keep their captions.
- Header text per guest: `style.header.line1` ("01년생 AI 3년차 개발자와 중등 특수교사"), `line2` as the user wants
  (ep11: "저품격 힐링 토크쇼" instead of 고품격).

## Modules
- `character`: **off** (the guest is visible). `zoom`: off by default. `cards`: allowed, same rules as portrait.
- Guest face mosaic: **off — rejected on ep11.** `track_guest.py` + plan `"mosaic": {"track": …, "block", "blend",
  "soften", "feather", "pad"}` exist, but the result shimmered and looked broken whenever the guest moved (the block
  grid follows the tracked box, block size follows face width per frame, the track is from the 720p proxy with 0.4 s
  smoothing). Only use it if the user asks again, and fix that first: grid anchored to the frame, one block size per
  take, heavy temporal smoothing (or a soft blur instead of blocks). Judge it on moving video, never on stills.

## Speakers
One mic, two voices: diarization collapses (ep11: 617 vs 62 windows). Assign speakers from the content and the
host's mouth logit (guest lines show logits below ≈ +0.8) with `words_patch.json` `set_spk`. Name them in
`plan.names` (`{"host":"건호","guest":"친구"}`) so the cut list reads right. Speed by role: explainer 1.27, asker 1.22.

## QA brief for the subagent
"Landscape two-shot: both on camera; host right (black upper row), guest left (navy lower row); no character GIF and
no zoom by design. Review the unrotated landscape preview."
