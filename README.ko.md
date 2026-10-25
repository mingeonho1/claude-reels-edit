# claude-reels-edit 🎬

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

[English](README.md) | 한국어

**2인 토크 릴스를 컷편집하고 자막까지 달아주는 Claude 스킬.** 촬영과 CapCut 2분 보정은 내가 하고,
제일 오래 걸리는 컷편집과 한국어·영어 자막은 Claude가 해. 단계마다 미리보기를 보여주고, 독립 검수 에이전트가
결과를 확인한 다음 4K로 뽑아.

> 인스타 [@geono_x](https://www.instagram.com/geono_x/)(친구 정우랑 대화하면서 경제·AI를 쉽게 풀어주는 채널)에
> 실제로 쓰는 워크플로우를 그대로 공개한 거야. 내 포맷과 내 편집 스타일에 맞춰져 있고, 규칙 하나하나가 왜
> 그렇게 정해졌는지는 [제작 과정](docs/JOURNEY.ko.md)에 다 적어놨으니 각자 포맷에 맞게 고쳐 쓰면 돼.

![스킬로 편집한 10번: 훅 타이틀, 헤더, 한국어 자막 + 영어 한 줄, 정우 캐릭터](docs/img/ep10_frames.jpg)

![두 번째 케이스 11번: 가로 투샷을 시계 방향 90°로 돌린 업로드본(왼쪽, 폰을 눕혀서 봄)과 가로 편집본(오른쪽). 친구 얼굴 모자이크는 이 이미지에만 넣었고 최종 영상엔 없음](docs/img/ep11_frames.jpg)

---

## 왜 만들었나

CapCut으로 편집할 때 시간을 잡아먹는 건 딱 두 가지였어. **컷편집 ≫ 자막 ≫ 나머지.**

첫 버전은 보정까지 전부 하려고 했어. 다섯 번을 피드백해도 얼굴 보정은 계속 어색했고(슬림 워프가 턱을 휘게
만들더니, 그다음엔 목이 깨졌어), 보이스 체인은 소리는 키웠지만 처리한 티가 났어. 반면 CapCut은 음성, 얼굴, 색,
선명도 보정을 2분 만에 끝냈고 결과도 더 좋았어([자세한 과정](docs/JOURNEY.ko.md#2-뭐가-문제였나--v1에-대한-내-피드백)).
그래서 AI는 **병목에만** 쓰고, 화질에 민감한 보정은 CapCut에 맡겨서 퀄리티를 최대한 지키도록 했어.

| 단계 | 누가 | 이유 |
|---|---|---|
| 보정(음성, 얼굴, 색, 선명도) | **나, CapCut** (~2분) | CapCut 툴이 재현 파이프라인보다 좋음. 소스는 다시 색보정하지 않음 |
| ① 컷편집 | **Claude** → 미리보기 → 승인 | 가장 오래 걸리던 작업 |
| ② 한국어 자막 → 그걸 번역한 영어 자막 | **Claude** → 미리보기 → 승인 | 두 번째 병목. 확정된 한국어에서 번역해야 영어가 안 어긋남 |
| ③ 이탈 방지 연출(줌, 캐릭터, 헤더, 카드) | Claude, 선택 | 리서치 + 내 피드백으로 검증된 것만 |
| ④ 검수 | **독립 서브에이전트** | 편집 계획을 안 믿고 결과물을 다시 듣고 다시 봄 |
| ⑤ 4K 마스터 | 내 Mac | 원본 해상도 그대로, 오버레이만 올림 |

## 지금까지 검증

| 에피소드 | 내용 | 결과 |
|---|---|---|
| **9번 「트럼프 전쟁」** — [내가 직접 CapCut으로 편집한 릴스](https://www.instagram.com/reel/DeIZ4g9J8vI/) | 기준 정답. CapCut 드래프트 JSON에서 컷, 배속, 자막 스타일, 캐릭터 타이밍을 그대로 읽음 | 스타일 스펙 + 자동 채점기 (`eval/gt9.json`, `eval/evaluate.py`) |
| **10번 「GPT-6」** — 같은 날, 같은 구도, 다른 내용 | 283.5초 원본 → **97.3초**, 34컷, 한·영 자막 58개, 콜드오픈 훅 | 검수 1라운드 blocker 1 / major 3 / minor 11 → 2라운드 blocker 0 ([검수 결과](examples/ep10/qa_round1_findings.json)) |
| **11번 「AI 빈부격차」** — 다른 구도: 가로 투샷, 게스트도 화면에 나옴(정우가 아니라 중등 특수교사 친구) | 219.5초 원본 → **94.1초**, 25컷, 한·영 자막 56개, 가로 편집본을 시계 방향 90°로 돌려 업로드(보는 사람이 폰을 눕힘). 얼굴 모자이크는 움직일 때 흔들리고 깨져 보여서 최종본에선 뺌 | 검수 1라운드 blocker 0 / major 2 / minor 12 → major 전부 수정 ([두 번째 케이스](docs/JOURNEY.ko.md#7-두-번째-케이스--다른-구도-11번)) |
| **12번 「대체 안 되는 AX 인재」** — 컨퍼런스 후기: 객석 영상 5개, 대화 촬영본 없음, 기획부터(플래너 서브에이전트 4개 + 심사) | 클립 2개를 이어 붙인 원본에 손으로 짠 EDL, 연사 육성 + 패널, 약 49초. 미리보기 피드백 9번 → 오버레이 속도 규칙 | [피드백 기록](examples/ep12/feedback.md) |
| 더 다른 구도 | 다음 테스트: 카메라 2대, 서서/걸으면서 찍은 영상 | 예정 |

---

## 구성

| 경로 | 내용 |
|---|---|
| [`skills/reels-talk-edit/`](skills/reels-talk-edit/SKILL.md) | 메인 스킬. 에이전트 하나가 순서대로 따라가는 단계형 워크플로우 (인테이크 → 컷 → 자막 → 연출 → 검수 → 4K) |
| [`skills/reels-qa/`](skills/reels-qa/SKILL.md) | 검수 스킬. 편집 계획을 모르는 새 서브에이전트가 실행 |
| [`skills/finance-reels-guard/`](skills/finance-reels-guard/SKILL.md) | 선택: 금융·투자 릴스 감시관 — 정보형/해석형 판정(5요소 중 2개 이상), 조회수 대신 근거·관점·전달력 점수, 바로 탈락 4가지(매수·매도 지시, 수익 보장, 광고 미고지, 저작권·음원), 업로드 7일 뒤 인사이트 분석. 직접 검수해보며 배운 점 포함 |
| `skills/reels-talk-edit/scripts/` | Claude가 호출하는 결정적 도구: STT + 단어 정렬, 화자 분리, 얼굴 추적, EDL 빌더, 렌더러, 컷 리스트, 자동 검수 |
| `skills/reels-talk-edit/references/` | 필요할 때만 읽는 문서: 구도별 파일(세로·게스트 화면 밖 / 가로 투샷 / 컨퍼런스 후기 몽타주), 원본 보정 재현, plan 키, 내 편집에서 측정한 스타일 스펙, 이탈 방지 리서치 |
| `skills/reels-talk-edit/eval/` | 9번 정답 + 채점기 (회귀 테스트) |
| [`examples/ep10/`](examples/ep10), [`ep11/`](examples/ep11) | 실제 `plan.json`(편집 결정 전부 + 한·영 자막), 컷 리스트, 검수 리포트 — 참고용 예시이고 스킬이 적용하는 설정이 아님 |
| [`examples/ep12/`](examples/ep12) | 컨퍼런스 후기: 손으로 짠 EDL 스크립트와 미리보기별 피드백 기록 |
| [`docs/JOURNEY.ko.md`](docs/JOURNEY.ko.md) | 왜 이렇게 만들었고 어떤 과정을 거쳤는지 (대결, 피드백, 재설계) |

역할 분담: **편집 판단은 전부 Claude가 `plan.json`에** 적어(뭘 자를지, 문장이 어디서 끝나는지, 자막, 영어, 훅).
스크립트는 정렬, 타이밍, 렌더, 측정 같은 기계적인 일만 해. 그래서 결과가 재현되고, 수정은 plan 한 줄이면 돼.

---

## 🚀 Claude로 설치

```bash
git clone https://github.com/mingeonho1/claude-reels-edit.git ~/claude-reels-edit && cd ~/claude-reels-edit && claude "INSTALL.md 읽고 릴스 스킬 설치해줘"
```

Claude(Cowork / claude.ai)에서는 `skills/reels-talk-edit`과 `skills/reels-qa`를 스킬로 추가하고(폴더를 zip으로
올리거나, 이 레포를 주고 스킬로 제안해달라고 하면 됨), 세션에서 `scripts/fetch_assets.sh`를 한 번 돌리면 돼.

## 🛠 직접 설치

```bash
git clone https://github.com/mingeonho1/claude-reels-edit.git ~/claude-reels-edit
cd ~/claude-reels-edit
pip install -r requirements.txt            # numpy, opencv-python, pillow, scipy, sherpa-onnx, soundfile
bash skills/reels-talk-edit/scripts/fetch_assets.sh   # 폰트, YuNet, 음성 모델(~1.4 GB) → ~/reels_models
mkdir -p ~/.claude/skills && cp -R skills/reels-talk-edit skills/reels-qa ~/.claude/skills/
```

필요한 것: Python 3.10+, libx265가 들어간 ffmpeg 4.4 이상, 모델용 디스크 ~2 GB. 게스트 캐릭터 GIF는 포함하지
않았어. 투명 GIF를 `skills/reels-talk-edit/assets/character.gif`에 넣거나 캐릭터 모듈을 꺼.
(캐릭터를 쓰는 이유: 대화 형식에서 상대방 자리가 비어 있는 것보다, 화면 밖 친구 대신 캐릭터를 만들어 두는 게 더 나았어.)
`skills/finance-reels-guard`는 선택이야. 금융·투자 릴스를 만들면 같이 복사해.

---

## 🧩 스킬 구조 (스킬 하나 + 참고 문서로 나눈 이유)

[Claude 스킬 작성 가이드](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices),
[Claude Code 스킬 문서](https://code.claude.com/docs/en/skills), [Codex 스킬 문서](https://developers.openai.com/codex/skills)를 보고 정했어.

| 가이드 | 이 레포에서는 |
|---|---|
| Codex: 스킬 하나는 한 가지 일만 | `reels-talk-edit` = 촬영본 → 완성 릴스. `reels-qa` = 완성본 검수(다른 일) |
| Claude: SKILL.md는 500줄 이하, 자세한 내용은 필요할 때만 읽는 파일로, 한 단계 깊이, 변형별로 정리 | SKILL.md엔 워크플로우만(약 130줄). 구도는 파일 하나씩(`format-portrait-offcam.md`, `format-landscape-twoshot.md`, `format-recap-montage.md`)이고 Claude는 그중 하나만 읽어. 원본 보정 재현, plan 키 전체도 참고 문서 |
| Claude: 여러 단계 작업엔 체크리스트 + 검증 루프 | 6단계 체크리스트, 승인 2번, 검수 → 수정 → 재검수(blocker·major 0까지) |
| Claude: 결정적인 일은 스크립트로 | 편집 판단은 Claude가 `plan.json`에, 타이밍·렌더·측정은 스크립트가 |
| Claude Code: `context: fork`로 격리된 서브에이전트 실행 | `reels-qa`에 `context: fork`를 넣어서 편집 계획을 아예 못 보게 함 |

그래서 새 구도(11번 가로 투샷)는 새 스킬이 아니라 참고 문서 하나가 늘어나는 거야. 내가 원하는 워크플로우(컷 → 승인 →
한국어 → 그걸 번역한 영어 → 승인 → 선택 연출 → 독립 검수 → 4K)는 한 곳에 그대로 있어. 두 스킬 다 공통 SKILL.md
형식이라 Codex(`~/.agents/skills/`)에서도 돌아가.

---

## 🧭 사용법

CapCut 보정본을 원본 옆에 두고(예: `~/capcut/me/10_ai_gpt6/소스/1차_보정.mov`) 이렇게 말하면 돼.

> 10번 릴스 편집해줘 — 보정본은 소스/1차_보정.mov

Claude가 하는 일:

1. **인테이크**: 프록시와 오디오를 뽑고, STT(whisper-turbo + 단어 타이밍용 한국어 zipformer), 화자 판별(목소리
   클러스터 + 화면 속 입 움직임)을 한 뒤 단어 목록을 처음부터 끝까지 읽어.
2. **컷 → 1차 승인**: 타임코드가 찍힌 `cut_preview.mp4`와 `cutlist.md`(남긴 문장, 자른 문장과 이유)를 보여줘.
   "ㅇㅋ"나 "37초 컷 어색해"라고 답하면 타임코드를 역추적해서 다시 잘라.
3. **자막 → 2차 승인**: 내 스타일대로 한국어 자막을 달고, 확정된 한국어를 1:1로 번역해서 영어 자막을 달아.
4. **연출**(선택): 콜드오픈 위 훅 타이틀, 헤더, 정우 캐릭터, 내가 말할 때만 들어가는 줌, 카드.
5. **검수**: 새 서브에이전트가 `qa_auto.py`와 사람 눈 검수를 해. blocker·major는 고치고 다시 확인해.
6. **4K**: Mac에서 150초 단위로 나눠 렌더해(끊겨도 이어서 진행). 음량까지 검증해.

"자동 승인"이라고 하면 승인 단계를 건너뛰어(스틸 컷 확인은 Claude가 직접 함).

주요 수치 (근거는 [제작 과정](docs/JOURNEY.ko.md)에):

| 규칙 | 값 |
|---|---|
| 배속(음정 유지) | 나 1.20 · 정우 1.30 · 섞임 1.25, 최대 1.32 |
| 화자 전환 간격 | 무음 0.20초 (0.5초 넘으면 끊긴 느낌) |
| 컷 여유 | 앞 0.09초 / 뒤 0.12초, 12ms 페이드, 확인된 무음 구간에서만 자름 |
| 자막 | 한 절, 공백 빼고 16자 이하, 0.45초 이상, 초당 13자 이하, 이모지 없음 |
| 줌 | 1.08배, 하드컷으로만, 내 대사가 시작되는 컷에서만, 8초에 1번 이하 |
| 카드 | 15–20초에 1개 이하, 실제로 말한 숫자만 |
| 음량 | −10.5 LUFS(보정본 입력), 트루피크 −1 dBTP 이하 |

## 🏗 동작 구조

```
CapCut 보정본 .mov ──► device_proxy.py ──► src_720.mp4 + src.wav
                                │
  analyze_audio.py (whisper-turbo + zipformer-ko + VAD) ─┐
  diarize.py (ERes2Net + 2-클러스터) ────────────────────┼─► build_words.py ─► words.json / words.txt
  face_track.py (YuNet 입 움직임) ───────────────────────┘                          │
                                                          Claude가 plan.json 작성 (자를 곳, 자막, 영어, 훅…)
                                                                                    ▼
                                    build_edl.py ─► edl.json (컷, 배속, 턴 간격, 자막, 레이어)
                                                                                    ▼
                         render.py prepare / run / audio / finish  (분할·이어하기, x265 10-bit)
                                                                                    ▼
                         qa_auto.py + reels-qa 서브에이전트 ─► qa_findings.json ─► plan 수정 ─► 4K 마스터
```

**Claude Cowork** 기준으로 만들었어(클라우드 샌드박스 + 내 Mac 연결: STT는 클라우드에서, 4K 렌더는 Mac의 원본
옆에서). `SKILL.md` 경로는 내 폴더 구조(`~/capcut/me/<번호_주제>/소스/`)를 따라. 한 컴퓨터에서 Claude Code로
쓰면 전부 로컬에서 돌아가니까 파일 위치만 알려주면 돼.

## 선택: 아이폰 원본에서 보정 재현

CapCut을 안 거치면 R 단계가 내 CapCut 보정을 대부분 재현해. 원본→보정본 25프레임 쌍으로 학습한 3D LUT
(`assets/his_look.cube`, 배경 오차 8.8 → 2.75 /255), 약한 피부 보정, 머리 크기 균일 3.5% 축소, 음성 체인.
CapCut 결과의 85–90% 정도라서 기본은 꺼져 있어.

## 📄 라이선스 · 크레딧

- 코드와 문서: [MIT](LICENSE). 서드파티 에셋은 재배포하지 않고 `fetch_assets.sh`로 받아. [NOTICE](NOTICE) 참고.
- `examples/`와 `eval/gt9.json`에는 내가 공개한 에피소드의 대본이 들어 있어. 테스트 용도로만 써줘.
- 개인 프로젝트이고 Anthropic, Instagram, CapCut과는 관계없어.
