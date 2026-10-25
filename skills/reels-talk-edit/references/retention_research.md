# Retention research: @geono_x 2-person econ talk Reels (60–100 s)
Research date 2026-10-22. Format: 1 static vertical cam (host), off-cam friend shown as sticker, Do Hyeon captions plus EN subtitle.
Source quality: [R] = research/standard, [E] = editor/tool guide (a vendor blog; numbers are rules of thumb), [J] = my judgment where no source gives a number.
Bottom line: most sources agree that the effect that hides an edit is the good one. Every effect the viewer notices costs trust, and auto-editors fire effects on a timer instead of on content.

## 1. Jump cuts and punch-ins (single static cam)
- Punch-in is a HARD scale change at a cut point. It is not an animated zoom inside a shot. Scale to 110–120%, on every 2nd–3rd cut, alternating wide→punch→wide→punch. https://1of10.com/blog/what-is-a-jump-cut/
- Keep the subject's eyes in the same screen position in both framings. A mismatch is what "makes the punch-in look like an edit". → Anchor the scale on the face/eye-line, not on the frame centre. https://krock.io/blog/video-editing-tricks/
- Animated zooms: linear motion is "the giveaway of an amateur zoom". A slow push uses ≤ +15% (100→115%) over ≥10 s with Sine/Quad easing. If it still feels mechanical, halve the scale change. https://echowave.io/tools/zoom-video/
- Start a framing change only at the start of a sentence, and hold each framing "for a long stretch". When auto-tools cycle punch-ins too fast, the fix is "far fewer framing changes". https://agent.vizard.ai/how-to/stop-the-punch-ins-cycling-too-fast-in-a-talking-head-edit.html
- Visual change every 3–7 s is a long-form YouTube norm. It does not have to be a zoom: a caption, sticker, or speaker swap also counts. Simple talking-head shots can cut after 1–2 s. Complex visuals (cards) hold ≥3 s. https://subscribr.ai/p/editing-talking-head-videos-engaging
- Overusing jump cuts makes the frame look unstable ("화면이 불안정해 보일 수 있습니다"). Avoid cutting where gaze or expression jumps sharply. https://tilnote.io/pages/6a0acee7feaf255d209877c2
- The 30-degree rule: a cut between two shots of the same subject reads as a "jump" unless the angle changes ≥30°. With 1 cam, a size change of ≥10% is the only substitute. https://1of10.com/blog/what-is-a-jump-cut/
- 4K source → 1080×1920 output: crop headroom is about 2× (the image stays sharp to about 130–200%). For 4K delivery there is no headroom, and each +10% costs about 10% resolution. https://echowave.io/tools/zoom-video/ , https://krock.io/blog/video-editing-tricks/
- **Rule set [J, derived from the above]:** punch only on a hard cut. Use 2 sizes only (100% / 112%), no third size. Hold each ≥3 s. Allow ≤1 punch per 8–10 s, so ≤8 per 80 s. Punch on the host's question start or the friend's key number/punchline, never mid-word. Use zero animated zooms. Never punch twice in a row.

## 2. Turn-taking (host ↔ off-cam friend)
- Natural turn gap across 10 languages (Korean included) is about 200 ms. Language means stay within ±250 ms (Japanese 7 ms, Danish 469 ms). A gap >500 ms reads as hesitation or a dispreferred answer. https://languagehat.com/the-universal-gap/ , https://altalang.com/beyond-words/taking-turns-in-conversation/ , https://emcawiki.net/Stivers-etal2009
- Answers and agreements come faster than non-answers and disagreements. A reply that lands fast sounds confident. https://altalang.com/beyond-words/taking-turns-in-conversation/
- Silence trimming: cut within-speaker silences >0.5 s. Cut right after a word ends, not on the breath. Put a 2-frame audio crossfade (~67 ms @30fps) on every cut. https://1of10.com/blog/what-is-a-jump-cut/
- Keep brief pauses after key lines or punchlines. Over-trimmed conversation "sounds mechanical". https://tilnote.io/pages/6a0acee7feaf255d209877c2 , https://1of10.com/blog/what-is-a-jump-cut/
- J-cut (next speaker's audio leads the picture) hides the edit. Plain cuts where audio and video switch together make every splice visible. https://krock.io/blog/video-editing-tricks/ , https://www.techsmith.com/blog/how-to-edit-videos-l-cuts-and-j-cuts/
- Keep a reaction only if it occurred in that order and adds meaning. Do not re-time reactions. Cut to the host for a question, interruption, or meaningful reaction, not because "a few seconds passed". https://www.capcut.com/create/podcast-clips-for-social-media-long-form-editing
- **Rule set [J]:** speaker-switch gap 150–300 ms (target 200). Within-speaker pause: cut if >400 ms, but keep 300–500 ms after a punchline. Sticker IN 2–4 frames BEFORE the friend's first syllable (visual J-cut) and OUT ≥200 ms after his last syllable (L-cut). Keep backchannels ("응", "그치", "오") that are ≤600 ms and overlap or sit in a gap. Drop backchannels that create a >300 ms pause. Never delete a laugh that a punchline depends on.

## 3. Captions as retention
- Chunking: 1–3 words per chunk (short-form) to 2–5 words/screen. Max 2 lines. Break where the speaker pauses, not mid-phrase. https://kineclip.com/blog/caption-readability-checklist-short-videos-2026/ , https://viralday.app/en/blog/6-caption-styles-beyond-hormozi-that-retain-high-attention
- Line length: ≤32 chars per line on mobile (EN). Korean guides give no fixed number; check 1–2 lines on a real phone. https://www.opus.pro/blog/video-captions-for-maximum-readability , https://filmora.wondershare.kr/answers/korean-subtitle-line-break-rules.html
- Timing: sync within ±200 ms of the audio. Show for ≥1.5 s (Instagram 2–4 s typical). Fade in/out 100–200 ms. Formula: 0.3 s/word + 0.5 s buffer. https://www.opus.pro/blog/video-captions-for-maximum-readability , https://www.opus.pro/blog/youtube-shorts-caption-subtitle-best-practices
- Contrast ≥4.5:1 (WCAG AA; 3:1 for large text). Test on the brightest and darkest frames. https://kineclip.com/blog/caption-readability-checklist-short-videos-2026/
- What looks cheap: unedited auto-caption errors, filler words transcribed verbatim, ≥3 stacked lines, decorative fonts, captions lagging speech, captions under the UI. https://www.opus.pro/blog/youtube-shorts-caption-subtitle-best-practices
- Hormozi-style word-by-word presets have become "digital background noise" and cause "caption blindness". One-word-at-a-time is "exhausting to read". (The page's claim of +34% swipe within 1.5 s is unverified.) https://viralday.app/en/blog/6-caption-styles-beyond-hormozi-that-retain-high-attention
- **Rule set [J]:** keep the current white-box style with no word-by-word karaoke. Use 1 accent colour per speaker (already black/navy) plus 1 highlight colour max. Highlight ≤1 keyword per caption and ≤1 per 5 s (≈12–20 per 80 s), reserved for numbers, tickers, and the punchline noun. Animation: one 100–150 ms fade or a ≤105% scale pop on entry, the same for every caption, with no bounce or shake. Zero emoji in captions. EN subtitle at ≤60% of the KR font size, the same timing as KR.

## 4. Hook / cold open (teaser from a later line)
- The hook must land within the first ~3 s. Open on the strongest clear statement, question, or tension. https://quso.ai/blog/how-to-edit-podcast-shorts-like-a-pro.html , https://www.capcut.com/create/podcast-clips-for-social-media-long-form-editing
- Default transitions (cut, fade, wipe) are overused by beginners. The "repetitive transition" tell applies to whooshes and flashes too. (The source's stats are unreliable.) https://resource.digen.ai/beginner-errors-ai-video-editing-fixes-2026/
- **Rule set [J; no source gives teaser seconds]:** teaser 2–5 s = one complete sentence from the friend's best line (a number or claim), cut on a word boundary. Transition into the episode with a HARD CUT plus 150–250 ms of room-tone or silence, OR a J-cut where the host's opening question audio leads by 2–4 frames. No flash, no whoosh, no rewind effect. Keep the teaser ≤8% of runtime. Re-use the exact same audio later (viewers recognize it, which pays off the hook).

## 5. B-roll / cards / stickers
- Cut to a visual when a concept, statistic, product, or place is mentioned. Complex visuals hold ≥3 s. Shots consistently <1–3 s overwhelm viewers. https://subscribr.ai/p/editing-talking-head-videos-engaging
- B-roll must match the spoken content. Mismatched or "filler" B-roll is a named mistake. https://tilnote.io/pages/6a0acee7feaf255d209877c2 , https://rizzle.com/blog/post/should-you-use-b-roll-in-your-podcast-shorts
- Over-editing with "too many effects, transitions, or gimmicks" is Storyblocks' mistake #2. https://www.storyblocks.com/resources/blog/editing-mistakes-beginners-make-with-video
- Keep text, faces, and logos in the centre safe area (about 950×980 px of 1080×1920). Top 14% (~270 px) and bottom 35% (~670 px) are covered by UI. The right ~21% (~230 px) is the action rail. Sides take 6% (~65 px). https://www.hopperhq.com/blog/instagram-reel-size/
- **Rule set [J]:** at most 1 info card per 15–20 s (3–5 per 80 s). Each card is triggered by a spoken number or term, holds 2.5–4 s, and stays ≥1 s past the spoken line. Cards sit in the upper-middle and never cover the host's eyes or the caption box. The friend sticker is a fixed position and size with the same entry anim every time. No stock-footage B-roll unless it shows the actual company or chart.

## 6. "AI slop" tells to AVOID (auto-edit fingerprints)
- Effects fire on a timer, not on content ("mathematically even cuts"). Test: if the interval std-dev is under 20% of the mean, it looks robotic. [J] Source on even pacing: https://resource.digen.ai/beginner-errors-ai-video-editing-fixes-2026/
- Punch-ins cycling too fast or mid-sentence. https://agent.vizard.ai/how-to/stop-the-punch-ins-cycling-too-fast-in-a-talking-head-edit.html
- Linear-speed zooms, or zooms on frame centre instead of the face. https://echowave.io/tools/zoom-video/
- Word-by-word Hormozi preset, emoji per line, random per-word colours. https://viralday.app/en/blog/6-caption-styles-beyond-hormozi-that-retain-high-attention
- Uncorrected auto-transcription, with misheard tickers or numbers. https://www.opus.pro/blog/youtube-shorts-caption-subtitle-best-practices
- AV sync drift (AI tools are cited at 83–217 ms; the source is unreliable). Keep within ±200 ms, ideally ≤1 frame. https://www.opus.pro/blog/video-captions-for-maximum-readability
- Face-warp or beauty retouch, and an over-polished look. Instagram's head says the polished aesthetic is fading toward a "more raw aesthetic" as AI floods feeds. https://www.techcentral.ie/instagram-chief-predicts-more-raw-aesthetics-as-ai-takes-over/
- Silence removed so hard the dialogue "sounds mechanical", with zero breathing room. https://tilnote.io/pages/6a0acee7feaf255d209877c2
- **Numeric caps [J]** per 80 s: whoosh/flash 0, SFX ≤3 (each motivated by an on-screen event), punch-ins ≤8, animated zooms 0, highlight colours ≤1, emoji 0, transitions other than a hard cut 0. Retouch: none. Colour grade: one global LUT/curve only.

## 7. Pre-post QA checklist
1. Loudness: integrated −14 LUFS (±1), true peak ≤ −1 dBTP. Instagram publishes no spec, so stay in the −14 to −16 safe band. https://openclip.app/learn/audio-normalization
   → Not what the skill ships: he wanted louder Reels, so `render.py audio` targets −10.5 LUFS (CapCut-corrected input) / −11 (raw), true peak ≤ −1 dBTP. The −14 band is the generic advice.
2. BGM (if any) at 10–20% of voice level, roughly −16 to −20 dB under dialogue. https://quso.ai/blog/how-to-edit-podcast-shorts-like-a-pro.html
3. Clicks and pops: every audio cut has a short crossfade (a few ms up to 2 frames) and sits near a zero crossing. Listen on headphones at each cut. https://descript.com/blog/article/crossfade-audio-what-crossfade-is-and-how-to-edit-it , https://1of10.com/blog/what-is-a-jump-cut/
4. Lip/caption sync ≤ ±200 ms. Spot-check 5 random points plus every speaker switch. https://www.opus.pro/blog/video-captions-for-maximum-readability
5. Caption proof: every number, ticker, company name, and EN translation checked against the script. No filler words. ≤2 lines. https://www.opus.pro/blog/youtube-shorts-caption-subtitle-best-practices
6. Jump artifacts: scrub each cut frame-by-frame for blinks, half-frames, head-position jumps >5% of frame width, and flashes. [J]
7. Safe zone overlay: top 270 / bottom 670 / right 230 / sides 65 px clear of captions, cards, and sticker. https://www.hopperhq.com/blog/instagram-reel-size/
8. Contrast ≥4.5:1 on the brightest frame behind every caption. https://kineclip.com/blog/caption-readability-checklist-short-videos-2026/
9. Export: H.264, AAC ≥128 kbps, ≥30 fps, 1080×1920 (or 2160×3840), ≤4 GB. https://www.hopperhq.com/blog/instagram-reel-size/
10. Fresh-eyes pass: watch once muted (are the captions alone enough?) and once from someone who hasn't seen it. https://www.storyblocks.com/resources/blog/editing-mistakes-beginners-make-with-video

## Gaps
- No credible source gives a numeric hook-teaser length or teaser→main transition. Section 4 is judgment.
- Korean editor sources found (kmong, tilnote, filmora.kr) are qualitative only. No numeric KR rules found.
- Many [E] pages are AI-tool vendor blogs. Treat their percentages as heuristics. Only the turn-gap data (Stivers 2009 PNAS) is peer-reviewed.
