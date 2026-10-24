# ep12 「대체 안 되는 AX 인재」 — preview feedback log (v1 → v10)

DMI 2027 (2026-10-13) recap made from 5 audience-view clips. No conversation take, no extra shooting; his narration
is recorded later over the panel blocks. Every line below is his feedback on a preview and what changed.

| Ver | His feedback | Change | Rule it became |
|---|---|---|---|
| v1→v2 | "5초에 할루시네이션에서 너무 확 끊긴다" | the last word was clipped: STT ended the line at 19.07 s, the sentence ran to 20.75 s | verify each speech span with RMS + trial `retranscribe.py` windows |
| v1→v2 | "발표에서 나온대로 쓰는 게 더 와닿는다" (ladder labels "물어보면 답") | Notion deck wording: "1단계 사고 파트너 / 물어보면 답해 준다" … | quote the source's words, don't shorten them |
| v1→v2 | "너는 어디야? 보다는 자가진단" | title "AI 활용 자가진단 4단계" | action-inviting titles |
| v1→v2 | "AX 인재 = 밑에 빨간 글씨 → 오른쪽" | new panel row `eq` (left term, right lines) | — |
| v2→v4 | "나레이션 자리에 자막 넣지 마, 이상해" | no caption row for his VO; the panel carries it | VO gets no captions in recap montage |
| v4→v5 | "할루시네이션에서 확대가 두 번 되는 게 어색", "8초 확대 별로" | one 1.2x framing for the whole 3025 speech run; dropped the 1.6x punch into a slide box | one framing per sentence run; ≤ 1.35x on slides |
| v5→v6 | "1단계 2단계 나오는 게 조금 느려" | step reveals 1.8 → 1.4 s apart | — |
| v6→v7 | "장면만 스위칭하면 흐름이 더 맞는다" | A → speaker "AI를 두려워하는 건 도태된 생각이다" → question panel → hallucination lines | follow the speaker's own sequence when it carries the argument |
| v7→v8 | "오버레이가 전체적으로 느리다" | question 7.0→3.8 s, ladder 14.1→8.0 s, checklist 6.5→3.6 s, note 9.0→4.2 s; enter 8→6 f, fades 6→4 f, bar fill 0.5→0.35 s | **overlay pacing rule** (SKILL.md §3, format-recap-montage.md) |
| v8→v9 | "AX 인재하고 빨간 글씨는 너무 빨리 나온다, 0.3초 뜸" | definition at 1.2 s, right side at 1.9 s | +0.3 s beat before the key line |
| v9→v10 | "마케팅만 AX로 바꾸자" | header line 2 "마케팅 컨퍼런스 DMI 2027" → "AX 컨퍼런스 DMI 2027" | — |

Planning (before v1): 4 planner subagents, 1 judge with a timecode-checking rubric (see `plan_judge.md`): P2 78,
P1 77, P4 75, P3 74 → he picked the judge's P1+P2 merge, no extra shooting, hook "대체 안 되는 AX 인재, / 질문부터 다르다".
`build_ep12.py` is the hand-built EDL over the concatenated IMG_3025+IMG_3026 source.
