# ep13 「투자 기초 : ETF」 — preview feedback log

Portrait off-camera talk (host asks, 정우 explains), a freestyle take with no script: 299 s → **117 s**, 41 segments,
68 KR+EN captions, 8 small source/notice lines (`notes`), 1080p master. Finance topic (정보형), so the finance guard ran
at the cut, the captions, the final preview and the Instagram caption. Every line below is his feedback and what changed.

| Stage | His feedback | Change | Rule it became |
|---|---|---|---|
| cut v1 → v2 | "51초에 '아니지 다른 것도 있지' 딱 깔끔하게 끝내, 속도 조금만 줄이자" | the end of the host's line moved to the energy dip after it; speeds 1.22/1.29 → 1.18/1.25 | default speeds asker 1.18 · explainer 1.25 · mixed 1.21 |
| cut v2 | "말을 끝내고 0.1초 쉬고 진행해야지, 컷마다 틈이 없어서 어색해" | every same-speaker cut gets ≥ 0.10 s of silence (quiet extension, else a muted pre-roll ≤ 0.30 s) | `cut_gap` 0.10 in build_edl (speaker changes stay 0.20 s) |
| cut v2 | "멘트를 아예 삭제해버리면 흐름이 어색해져, 통으로 날린 거 또 있어?" | the last line (dropped for a finance-guard 위험) came back; it is now covered by a 소자막 notice | a 위험 line that carries the flow is fixed with a notice, not a cut; gate 1 lists every whole-content drop |
| cut v2 → v3 | "'이런 뉴스가 터져' 하고 '근데 내 과일바구니에' 이러면 흐름이 어색하잖아. 어색하다면 안 빼는 게 나아, 다시 검증해봐" | re-read every drop as "line before ‖ line after": restored the news itself, the analogy's payoff, the other person's short replies and the bridge words ("그 다음에", "그래서", "예를 들어서") — 97 s → 116 s, "훨씬 좋다" | **flow check** before gate 1; flow beats length |
| subs | (approved) | KR one clause ≤ 16 chars, EN translated from the final KR | — |
| notes | "소자막은 어떤 식으로 넣게? 사진으로 보여줘" → "조금 더 작게" | mock-up stills first; Pretendard 44 px in a dark 72 % box under the captions, ≥ 2 s, one at a time | `notes` module for sources/definitions/risk notices |
| final | "정우 캐릭터를 좀 더 가운데로, 자막이 캐릭터 위에" | character centre x 1828 → 1620; captions drawn on top | new default |
| final | "투자 기초 : ETF로 바꾸자, 'ETF는 과일바구니' 별론데" | hook = a topic label instead of a quoted line | hook style note in the format reference |
| final | (QA) black header unreadable on dark hair/blinds | white 6 px outline | default header outline |
| final | "말을 끝까지 끝내고 정우가 말하는 걸로 해야지, 많이 피드백했던 것 같은데" | the host's rising "있지?" was cut 0.15 s early on an inner dip; ended on the dip after the tail | **speaker change = the outgoing line finishes first**; `check_tails.py` flags MID/TAIL ends (it catches this case) |
| final | "팩 바르는 타이밍에 머리에 작게 (편하게 듣는 힐링 토크쇼), 다 붙이고 (ㅎㅎ)" | small "( … )" asides on the hair, 62 px, placed from mock-up stills | `texts` module |
| final | "마지막에 너무 그냥 끝내는 느낌" | kept the closing "좋다" from the end of the take + 0.5 s tail | never end on a bare answer |
| master | "1080p로 뽑아보자 … 생각보다 화질 괜찮게 나와서 이대로 가도 될 것 같은데? 4K 랜더링 너무 오래 걸리니까" | 1080x1920 master: lanczos once from the 4K source before the overlays, 10-bit HEVC, x265 medium crf 14, ~18 Mbps, ~3 fps on the Mac | 1080p is the default master; 4K on request |
| caption | "본문도 짧게 임팩트 있게 친근하게 3개" | 3 Instagram caption options (question / number / mood hook), guard-checked, one recommended | stage 6 in SKILL.md |

QA round 1 (independent subagent): 0 blocker / 4 major / 10 minor → majors fixed (a residual "용과도" syllable, a chopped
"가능한 거지", the header contrast; the host leaving the frame mid-line was accepted as source). The automatic pass's
5 caption-mismatch blockers were all STT windows clipping a word at speaker changes (now listed as a known false
positive in reels-qa).
