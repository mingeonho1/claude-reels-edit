# plan.json keys (all optional except `captions`)

| Key | Meaning / default |
|---|---|
| `stage` | `cut` (no overlays) · `subs` (captions + English) · `final` (modules) |
| `orientation` / `rotate` | `portrait` (default) · `landscape`; `rotate`: `clock` (tilt-your-phone upload) · `cclock` |
| `start_word` / `end_word` | source seconds of the first / last kept word |
| `drop[]` | `{t:[s0,s1], why}` or `{w:[i0,i1], why}` — words whose midpoint falls inside are removed |
| `cut[]` | `[[s0,s1]]` force a cut through a span that never measures as quiet |
| `retime[]` | `{i, src:[s0,s1]}` corrected word times |
| `mute_extra[]` | `{src: seg_start, add: 0.06}` mute a residual syllable after a tight in-point |
| `speed` / `speed_cap` | `{host, guest, mixed}` 1.21 / 1.18 / 1.20 · cap 1.32 (explainer slowest; guest 1.15 if still fast) |
| `turn_gap` / `cut_gap` / `pause_cut` / `pad_in` / `pad_out` | 0.20 (speaker change) / 0.10 (same speaker, output s) / 0.32 / 0.09 / 0.12 s |
| `target_out` | output length limit (s); build_edl fails above ×1.05 |
| `cold_open` | `{spans:[[s0,s1]], captions:[…], transition:'cut', whoosh:false}` |
| `hook` | `{text, until_t, min_dur 2.4, max_dur 3.4, keep_captions, intro}`; `\n` in `text` = two stacked lines |
| `captions[]` | `{t:[s0,s1] \| w:[i0,i1] (+src), speaker: host\|guest, text, en}` |
| `cards[]` | `{at_t, dur, title, lines[], accent, dir}`; or `layout:"panel"` + `items[]` (title/text/big/strike/bar/check/eq/src/gap, each with `at` reveal time) — full-width reveal panel, see format-recap-montage.md |
| `notes[]` | 소자막 `{t:[s0,s1], lines:[1-2], min_dur 2.0}` — small source/disclaimer box under the captions (Pretendard 44 px, top 2770, dark 72 %); one at a time (ep13) |
| `texts[]` | free text sticker `{t:[s0,s1], text, cx, cy, size 72, fill, stroke 5, stroke_fill}` (4K coords; Do Hyeon white + dark outline), e.g. a small aside on the host's hair (ep13 "편하게 듣는 힐링 토크쇼", "ㅎㅎ") |
| `voice_over[]` | `{file, out_start, src_start, src_end, rel_db 3}` narration recorded afterwards, leveled to the cut and mixed before the voice chain |
| `modules` | `{header, hook, character, zoom, cards}` |
| `zoom_mode` / `zoom` | `host_cut` · `{host_cut 1.08, min_zoom 1.5, min_gap 8}` |
| `style` | overrides merged into the layout (`header.line1/line2`, `hook.cx`, caption rows …); dark footage: `header.color [255,255,255]` + `header.outline {width 6, color [10,10,10]}`, `hook.fill` white + `hook.stroke_fill` black |
| `names` | `{host, guest}` labels for the cut list |
| `grade` | `{mode none\|his_look\|param, sharpen}` |
| `retouch` | `{off}` or `{smooth, head_shrink, lift, …}` |
| `audio` | `{mode passthrough\|voice_chain, target_lufs −10.5 corrected / −9.5 raw, host_gain_db}` |
| `preview_timecode` | running timecode on proxies (default on before `final`) |
