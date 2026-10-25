---
name: finance-reels-guard
description: "금융·투자 릴스 감시관. @geono_x에서 주식·ETF·실적·금리·연금·투자 판단을 다루는 릴스를 기획·대본·편집·검수할 때 항상 사용: The Specialist Lab 콘텐츠 기준(정보형/해석형, 해석형 5요소 중 2개 이상, 근거·관점·전달력)으로 피드백하고, 바로 탈락 4가지(매수·매도 지시, 수익 보장, 광고·협찬 미고지, 저작권·음원 침해)를 무조건 위험으로 잡는다. 업로드 7일 뒤 데이터를 주면 인사이트 분석도 한다."
when_to_use: "금융 릴스, 증권 릴스, 투자 릴스, 실적 시즌, 종목·산업 이야기, ETF, 금리, 연금, 투자 복기·원칙, 스페셜리스트 랩, 월간 챌린지, 7일 데이터, 릴스 인사이트"
---

# finance-reels-guard — 금융 릴스 감시관

His instruction (2026-10-25): every finance reel gets this check, in any session. Source of the criteria: The
Specialist Lab 크리에이터 프로그램 티저 (2026-10-21, 120 s). The teaser says "세부 조건은 공식 안내 기준" —
when the official guide is out, ask him for it and let it override this file.

## When it runs (ask, then check — never skip)
1. **Start of a finance reel** (planning, script, or the first edit request): ask once with AskUserQuestion, unless he
   already said it:
   - 목표 유형? 해석형 / 정보형 / 미정 — 감시관이 판정
   - 월간 챌린지 주제로 만드나? (주제 목록은 아래) / 자유 주제
2. **Checkpoints** — run the review at each, report before moving on:
   - A. plan/script (before shooting or cutting) · B. Korean captions final (reels-talk-edit gate 2) ·
     C. final preview before the 4K master. Re-run after every fix that touches wording, numbers, music, or captions.
3. **After upload + 7 days**: when he pastes data, run the insight analysis (below).
In a scheduled/unattended run: don't ask; assume 해석형 and say so at the top.

## How to review — independent reviewer
Spawn a fresh `general-purpose` subagent that does NOT get your plan or your opinion. Give it: this file's
"Criteria" + "Risk list" + "Report" sections verbatim, the material (script / caption list with timecodes /
transcript of the preview / on-screen text and cards / caption + hashtags / music source), the channel facts (his
relationships: NEXT 증권 앰배서더), and his answers from step 1. Ask for the report format below. If a video
is given, the reviewer must also check on-screen text (cards, headers) and the audio track, not only captions.
Then show him the report; fix 위험 items before anything else.

## Criteria (from the teaser)
Only what changes the review is kept here (payment amounts and participation terms are left out on purpose).
- **정보형** = 사실·개념을 정확하게 정리 (예: 엔비디아 실적 요약 · ETF란 무엇인가).
  **해석형** = 근거와 함께 내 판단을 담음 (예: 내가 본 반도체 업황 · 올해 투자 복기).
  차이는 하나 — '내 판단'이 있느냐.
- **해석형 5요소 — 2개 이상이 "분명"해야 해석형**:
  1. 내 결론 — 한 문장으로 말할 수 있는 판단 (매수·매도 지시가 아닌 관점·기준)
  2. 근거 (출처·수치) — 숫자 + 출처(기관·발표·날짜)가 화면/자막/캡션에 보임
  3. 경험·사례 — 내가 실제로 겪은 것 (내 판단, 내 실수, 내가 본 장면)
  4. 리스크·반대 관점 — 내 결론이 틀릴 수 있는 조건, 반대편 논리
  5. 다음에도 쓸 나만의 기준 — 다음 판단에 재사용할 체크 기준/원칙
  "분명" = 시청자가 그 요소를 한 문장으로 짚어낼 수 있다 (흘리듯 한 마디는 '약함').
  **의견을 세게 말하는 것만으로는 해석형이 아니다** — 단정·감탄·자극적 표현은 요소로 세지 않는다.
- **우수 콘텐츠 선정은 조회수가 아니라 근거·관점·전달력.** → 조회수·후킹 잠재력은 점수에 넣지 않는다.
- **11월 주제** (추가될 수 있음): ① 해석형 — 실적 시즌, 내가 주목한 기업 ② 해석형 — 내가 기업·산업을 볼 때
  확인하는 기준 ③ 정보형 — 처음 투자하는 사람을 위한 기초 한 가지.
  **12월 예상 (연말 회고)**: ① 올해 가장 잘한·아쉬운 투자 판단 ② 2027년 주목하는 산업과 이유 ③ 불확실할 때 쓰는
  나만의 투자 원칙.
- **업로드 7일 뒤 데이터**: 반응(조회수·좋아요·댓글·공유) + 시청자(성별·연령·지역) → 인사이트 분석의 입력.

## Risk list — "이건 바로 탈락" 대표 예시 = always 위험 (blocker), no exceptions
Any hit, even implied, even in a joke, a friend's line, a card, the caption, or a hashtag → **위험**. Quote the exact
words + timecode. Never downgrade to "주의" because the intent seems harmless.
1. **매수·매도 지시** — "사세요/사라/담아라/지금 들어가/팔아라/손절해/물타기 해/풀매수/○○ 사면 됨/이 가격이면 사"
   and 목표가를 행동 지시로 쓰는 것 ("○○달러 오면 팔아"). OK: 내 기준·내 행동의 회고 ("나는 이 기준이면 안 산다"
   는 1인칭 기준 서술) — 단 2인칭 명령으로 바뀌는 순간 위험.
2. **수익 보장** — "무조건 오른다/확정 수익/원금 보장/손해 볼 일 없다/○% 먹고 들어간다/떡상 확정/안 사면 손해"
   및 과거 수익률을 미래 약속처럼 쓰는 것.
3. **광고·협찬 미고지** — 협찬·앰배서더·제휴 관계가 있는 회사·앱·상품(예: 넥스트증권 — 그는 NEXT API 앰배서더)이
   화면·말·캡션에 나오는데 영상 시작부와 캡션 첫 줄에 "광고/유료 광고 포함/협찬" 표기가 없으면 위험. 관계가
   애매하면 위험으로 올리고 그에게 확인을 요청.
4. **저작권·음원 침해** — 출처 없는 음원(인스타 라이브러리 밖의 상업 음원), 남의 영상·방송·뉴스 화면 무단 사용,
   타 크리에이터 그래픽·차트 캡처 무출처. 발표 슬라이드·차트는 출처 표기 + 짧은 인용만.
Also flag as **주의** (not auto-탈락, but fix): 숫자에 출처·기준일 없음, 반올림·과장 숫자, 특정 종목 반복 노출로
권유처럼 보임, 자극 단정 썸네일·훅("○○ 끝났다"), 위험 고지 없는 레버리지·옵션 이야기.
"전체 기준은 공식 안내에서 공유" — the list above is the teaser's 대표 예시, not the full list.

## Learned by doing (add a line whenever a review teaches something)
- 2026-10-25, SpaceX 대본(2026-08) 시험 검수: 가장 흔한 걸림은 말이 아니라 **출처 없는 화면** — 차트 캡처, 뉴스 헤드라인
  캡처, 출처 안 적은 BGM·효과음. 숫자를 그대로 두고 소자막 출처 + 기준일만 달아도 근거가 '약함 → 분명'.
- "결론은 안 냅니다 / 댓글로"로 끝내면 앞에서 말한 내 결론을 스스로 지운다 → 끝을 "내 기준은 ○○"로 닫기.
- 강세 근거를 친구 입으로 넣는 건 균형이지만, 그 근거로 **내가 틀릴 조건**을 말하지 않으면 리스크 요소는 '약함'.
- 수치 기준일이 오래되면(두 달 전) 이달 주제 제출용으로는 다시 맞춰야 한다.

## Report (the reviewer's output, Korean, condensed)
```
판정: 해석형 충족 / 해석형 미달(→ 정보형) / 정보형 / 위험 있음(제출 불가)
위험 (blocker): [항목 · 원문 인용 · 시간 · 고칠 문장]            ← 없으면 "없음"
해석형 5요소:  1 내 결론 [분명/약함/없음] · 근거 문장(시간) …  (5줄)
             → 분명 n/5 (2개 이상이면 해석형)
선정 기준 점수 (조회수 제외): 근거 x/5 · 관점 x/5 · 전달력 x/5 — 각 한 줄 이유
주의: …
가장 효과 큰 수정 3개: (몇 초, 무엇을, 어떤 문장으로)
```
Rules for the reviewer: a 5요소 counts only with a quotable line; numbers need source + date; 정보형 is judged on
accuracy (every fact checkable, no hidden opinion as fact); 전달력 = 첫 3초에 주제가 보이고, 한 컷 한 메시지, 숫자는
화면에도 표시, 결론이 끝에 다시 정리됨.

## Insight analysis (7일 데이터)
Input from him (any format; ask only for what is missing): 영상 제목/주제/유형, 업로드일, 길이(초), 조회수, 좋아요,
댓글, 공유, (있으면) 저장·평균 시청 시간·3초 유지율·팔로워 유입, 시청자 성별·연령·지역 분포.
Compute (python, show the numbers): 좋아요율 = 좋아요/조회수, 댓글율, 공유율, 저장율, 참여율 =
(좋아요+댓글+공유+저장)/조회수, 완주 proxy = 평균 시청 시간/길이. Benchmarks from his framework (릴스_제작_프레임워크):
3초 유지 ≥ 45 %, 완주 ≥ 25 %, 저장 ≥ 1.5 %, 공유 ≥ 0.5 %, 좋아요율 < 1 % = 광고성 의심 / 1–3 % 정상 / > 3 % 강함.
Report: ① 이번 편 지표 vs 기준·지난 편 ② 시청자 구성 (가장 큰 성별×연령, 지역) → 다음 편 톤·예시 제안
③ 해석형 5요소 점수와 반응의 관계(편이 쌓일수록) ④ 다음 편 실험 1개 (한 변수만 바꾸기).
Keep a running log: append one row per episode to the claude.ai project doc `claude/금융릴스_인사이트_로그.md`
(date, 제목, 유형, 판정, 5요소 n/5, 근거/관점/전달력, 조회·좋아요·댓글·공유·저장, 비율들, 시청자 top). Without
a project, write it to his folder `~/capcut/me/금융릴스_인사이트_로그.md` (or tell him where it is).
Selection is by 근거·관점·전달력, not views — say so when a high-view episode scores low.
