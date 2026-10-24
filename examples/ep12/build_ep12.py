#!/usr/bin/env python3
"""ep12 (DMI 2027 recap, no talk take): hand-built EDL over the concatenated source IMG_3025 + IMG_3026.
Speech segments = speaker's own words (navy captions); B-roll segments = ambient at -20 dB under a reveal panel.
Usage: build_ep12.py <stage: cut|subs|final> <out edl.json>"""
import json, sys

FPS = 30
OFF = {'3025': 0.0, '3026': 1582 / 30.0}        # 3025 = 1582 frames
stage = sys.argv[1]
VO_CAPS = False
out = sys.argv[2]

# zoom helper: centre (fx, fy) in frame fractions at scale z -> render.py anchor (cx, cy)
def zc(fx, fy, z):
    r = 1 - 1 / z
    return dict(scale=z, cx=min(1, max(0, (fx - 0.5 / z) / r)), cy=min(1, max(0, (fy - 0.5 / z) / r)))

SRC = '#5c6bc0'
# timeline -------------------------------------------------------------------------------------------
T = [
    # A hook: speaker opens, "AI를 두려워하는 것은 이미 지난 생각입니다" slide appears at src 2.0
    dict(id='A', clip='3026', s=0.50, e=6.15, speed=1.2,
         zooms=[(0.50, 2.05, None), (2.05, 6.15, (0.30, 0.55, 1.35))],
         caps=[(0.55, 3.20, '두려워하지 말고 뛰어들어야 하는 상황입니다', "We have to stop fearing it and dive in"),
               (3.30, 6.10, '그래서 저는 과감하게 이런 말씀들을 드립니다', "So I'll say this boldly")]),
    # B1 (v7) speaker continues straight from A: "AI를 두려워하는 건 [0.6 s pause] 도태된 생각이다" (pause -> 0.15 s)
    dict(id='B1', clip='3026', s=6.35, e=10.05, speed=1.1,
         zooms=[(6.35, 8.40, (0.30, 0.55, 1.35)), (9.00, 10.05, (0.30, 0.55, 1.35))],
         caps=[(6.40, 10.00, 'AI를 두려워하는 건 도태된 생각이다', "Fearing AI is outdated thinking")]),
    # B the question flips (v8 pacing: reveals 0.5 s apart, 3.8 s total)
    dict(id='B', clip='3026', s=10.05, e=13.85, speed=1.0, gain=-20, zooms=[(10.05, 13.85, (0.30, 0.55, 1.35))],
         vo=[(0.1, 1.0, '질문을 바꾸래', ''), (1.0, 2.0, "'내가 대체될까?'가 아니라", ''), (2.0, 3.7, "'무엇을 맡기고, 어디로 올라갈까?'", '')],
         panel=dict(top=1040, items=[
             dict(t='title', text='그래서 질문을 바꾸래'),
             dict(t='gap', h=10),
             dict(t='strike', text='"내가 대체될까?"', size=112, at=0.3, strike_at=0.8, color=[110, 110, 110]),
             dict(t='big', text='"무엇을 맡기고,', size=118, at=1.3, color=[38, 42, 120], align='left'),
             dict(t='big', text='나는 어디로 올라갈까?"', size=118, at=1.3, color=[38, 42, 120], align='left'),
             dict(t='gap', h=10),
             dict(t='src', text='데이터라이즈 박민성 CSO 발표 슬라이드 · DMI 2027'),
         ])),
    # C context: hallucination isn't even mentioned anymore / AI is just beside us (v2: full word tails + 0.3 s breath)
    # the sentence runs to 20.75: "이제는 [1 s pause] 할루시네이션이란 단어는 언급도 되지 않죠" -> pause cut to ~0.15 s
    dict(id='C1', clip='3025', s=16.80, e=20.75, speed=1.1, zooms=[(16.80, 17.55, (0.45, 0.56, 1.2)), (18.40, 20.75, (0.45, 0.56, 1.2))],
         caps=[(16.85, 20.70, '이제는 할루시네이션이라는 단어는 언급도 되지 않죠', "Nobody even mentions 'hallucination' anymore")]),
    dict(id='C2', clip='3025', s=21.45, e=24.72, speed=1.1, zooms=[(21.45, 24.72, (0.45, 0.56, 1.2))],
         caps=[(21.45, 24.70, '이제 AI는 그냥 우리 옆에 있는 존재가 되었습니다', "AI is now simply something right beside us")]),
    # D self-check ladder (Notion deck wording; v8 pacing: steps 0.8 s apart, 8.0 s total)
    dict(id='D', clip='3025', s=25.50, e=33.50, speed=1.0, gain=-20, zooms=[(25.5, 33.5, None)],
         vo=[(0.1, 0.6, '노션 6,118명 조사', ''), (0.6, 1.5, '1단계 물어보면 답해 주고', ''), (1.5, 2.4, '2단계 시키면 만들어 주고', ''),
             (2.4, 3.3, '3단계 안 시켜도 끝내 놓고', ''), (3.3, 4.5, '4단계 에이전트끼리 굴러가', ''),
             (4.5, 5.8, '88%가 아직 1·2단계', ''), (5.8, 7.8, '마케팅은 3단계 이상이 12%', '')],
         panel=dict(top=1000, items=[
             dict(t='title', text='AI 활용 자가진단 4단계'),
             dict(t='src', text='노션 글로벌 AI 전환 조사 2026 · 6,118명'),
             dict(t='gap', h=12),
             dict(t='bar', label='1단계 사고 파트너', sub='물어보면 답해 준다', pct=57, at=0.5, hi_at=4.4, hi_color=[150, 150, 150]),
             dict(t='bar', label='2단계 비서', sub='시키면 만들어 준다', pct=31, at=1.3, hi_at=4.4, hi_color=[150, 150, 150]),
             dict(t='bar', label='3단계 팀원', sub='시키지 않아도 끝내 놓는다', pct=10, at=2.1, hi_at=4.4, hi_color=[214, 58, 58]),
             dict(t='bar', label='4단계 시스템', sub='여러 에이전트가 리서치→성과분석', pct=2, at=2.9, hi_at=4.4, hi_color=[214, 58, 58]),
             dict(t='gap', h=6),
             dict(t='text', text='→ 88%는 아직 1·2단계', at=4.4, size=88, color=[60, 60, 60]),
             dict(t='text', text='→ 마케팅 직무 3·4단계는 12%', at=5.6, size=88, color=[214, 58, 58]),
         ])),
    # E answer: execution to AI, people up to judgment (speaker)
    dict(id='E', clip='3026', s=41.85, e=57.52, speed=1.2,
         zooms=[(41.85, 44.16, (0.30, 0.55, 1.6)), (44.16, 48.31, (0.80, 0.55, 1.6)), (48.31, 52.13, None),
                (52.13, 57.52, (0.50, 0.53, 1.25))],
         caps=[(41.95, 44.15, '그래서 실행은 AI에게 맡기고', "So leave execution to AI"),
               (44.16, 46.23, '이제는 너무 당연하게 사람이', "and, quite naturally, people"),
               (46.24, 48.31, '판단하는 자리로 올라가야 되고', "must move up to where judgment happens"),
               (48.32, 50.22, '그 판단을 하는 과정에서', "and in making those calls,"),
               (50.23, 52.13, '내 머릿속에 있는 암묵지를', "the tacit know-how in your head"),
               (52.14, 54.46, '계속해서 실행해줄 AI에게', "to the AI that keeps executing it"),
               (54.47, 55.36, '줄 수 있는 변화의 흐름을', "you need to be able to hand over"),
               (55.37, 57.50, '진행하셔야 된다는 거고요', "that's the shift you have to make")]),
    # F checklist (v8: checks 0.5 s apart, 3.6 s)
    dict(id='F', clip='3025', s=42.50, e=46.10, speed=1.0, gain=-20, zooms=[(42.5, 46.1, None)],
         vo=[(0.1, 0.8, '그럼 뭐부터 맡기냐면', ''), (0.8, 3.5, '매주 반복, 툴 3개 이상, 판단보다 옮기는 일', '')],
         panel=dict(top=1180, items=[
             dict(t='title', text='AI한테 처음 넘길 일 고르는 법'),
             dict(t='gap', h=10),
             dict(t='check', text='매주 반복되는 일', at=0.1, check_at=0.6),
             dict(t='check', text='툴 3개 이상을 오가는 일', at=0.1, check_at=1.1),
             dict(t='check', text="판단보다 '옮기는' 일", at=0.1, check_at=1.6),
             dict(t='gap', h=6),
             dict(t='src', text='노션 채지선 발표 · DMI 2027'),
         ])),
    # G definition (his note; v8: 4.2 s)
    dict(id='G', clip='3026', s=65.0, e=69.8, speed=1.0, gain=-20, zooms=[(65.0, 69.8, None)],
         vo=[(0.1, 1.6, '코드는 AI가 짜도 배포 버튼은 내가 눌러', ''), (1.6, 4.1, 'AX 인재는 맡길 일을 정하고 책임지는 사람', '')],
         panel=dict(top=1120, items=[
             dict(t='title', text='01년생 AI 3년차 개발자 메모'),
             dict(t='text', text='코드는 AI가 짜도, 배포 버튼은 내가 누른다', at=0.1),
             dict(t='gap', h=24),
             dict(t='eq', left='AX 인재 =', right=['AI한테 뭘 맡길지 정하고,', '결과에 책임지는 사람'], at=1.2, right_at=1.9,
                  left_size=124, size=104),
         ])),
    dict(id='H', clip='3026', s=69.8, e=72.4, speed=1.0, gain=-20, zooms=[(69.8, 72.4, None)],
         vo=[(0.1, 2.5, '우리는 몇 단계일까? 판단해보는 시간이 됐으면 좋겠어', '')],
         panel=dict(top=1300, items=[
             dict(t='big', text='우리는 몇 단계일까?', size=124),
             dict(t='text', text='판단해보는 시간이 되었으면', align='center', size=88),
         ])),
]

segs, caps, zooms, cards = [], [], [], []
t_out = 0.0
f_out = 0
for b in T:
    off = OFF[b['clip']]
    # split into sub-segments at zoom boundaries (frames are integral per sub-segment)
    for (z0, z1, zz) in b['zooms']:
        n = int(round((z1 - z0) / b['speed'] * FPS))
        o0 = f_out / FPS
        o1 = (f_out + n) / FPS
        segs.append(dict(src_start=round(off + z0, 4), src_end=round(off + z1, 4), speed=b['speed'], frames=n,
                         out_start=round(o0, 4), out_end=round(o1, 4), zoom=1.0, face=None, face_stable=False,
                         host_frac=0.0, tight=[False, False], words=[0, 0], mute_lead=0.0,
                         gain_db=b.get('gain', 0.0), cold=False, block=b['id']))
        z = dict(scale=1.0, cx=0.5, cy=0.5) if zz is None else zc(*zz)
        zooms.append(dict(out_start=round(o0, 4), out_end=round(o1, 4), **z))
        f_out += n
    blk = [s for s in segs if s['block'] == b['id']]
    b0, b1 = blk[0]['out_start'], blk[-1]['out_end']

    def m(t):                        # source (clip-local) -> output seconds
        for s in blk:
            if s['src_start'] - 1e-6 <= off + t <= s['src_end'] + 1e-6:
                return min(s['out_end'], s['out_start'] + (off + t - s['src_start']) / s['speed'])
        return b1
    for (c0, c1, tx, en) in b.get('caps', []):
        caps.append(dict(text=tx, speaker='guest', out_start=round(max(b0, m(c0)), 4), out_end=round(min(b1, m(c1)), 4),
                         en=en, en_above=False))
    # his narration gets NO caption row: the panel already shows it (user 2026-10-24: VO captions looked odd)
    for (v0, v1, tx, en) in (b.get('vo', []) if VO_CAPS else []):
        caps.append(dict(text=tx, speaker='host', out_start=round(b0 + v0, 4), out_end=round(min(b1, b0 + v1), 4),
                         en=en, en_above=False))
    if b.get('panel'):
        p = dict(b['panel'])
        cards.append(dict(layout='panel', out_start=round(b0, 4), out_end=round(b1, 4), **p))

# captions: close tiny gaps inside a speech block (no flicker), keep >= 0.6 s
for a, c in zip(caps, caps[1:]):
    if 0 < c['out_start'] - a['out_end'] < 0.25:
        a['out_end'] = c['out_start']
total = f_out / FPS
hook_end = 3.4
E = dict(source='IMG_3025+IMG_3026 (concat)', fps=FPS, out_frames=f_out, out_duration=round(total, 4), segments=segs,
         captions=caps if stage != 'cut' else [], layers=dict(captions=stage != 'cut', english=stage != 'cut', header=True,
                                                                  hook=True, cards=True, character=False),
         stage=stage, preview_timecode=stage != 'final', character=[],
         hook=dict(text='대체 안 되는 AX 인재,\n질문부터 다르다', out_start=0.0, out_end=hook_end, sub=None, intro=False),
         transitions=[], header=dict(out_start=hook_end, out_end=round(total, 4)), zooms=zooms, cards=cards,
         grade=dict(mode='his_look'), retouch=dict(off=True),
         audio=dict(target_lufs=-11.0, true_peak=-1.5, fade_ms=12, mode='voice_chain'),
         style={"header": {"line1": "01년생 AI 3년차 개발자가 다녀온", "line2": "AX 컨퍼런스 DMI 2027",
                           "l1_top": 430, "l2_top": 546, "l1_w": 1180, "l2_w": 1100,
                           "color": [255, 255, 255], "l2_bold": 0, "outline": {"width": 6, "color": [10, 10, 10]}},
                "hook": {"cy": 760, "max_w": 1900, "glyph_h": 230, "fill": [255, 255, 255], "stroke": 9,
                         "stroke_fill": [10, 10, 10]},
                "panel": {"enter_frames": 6, "reveal_frames": 4},
                "caption": {"guest": {"top": 2930, "color": [37, 41, 115]}, "host": {"top": 2930, "color": [0, 0, 0]}}},
         warnings=[], orientation='portrait', rotate=None, mosaic=None, form_violations=[])
json.dump(E, open(out, 'w'), ensure_ascii=False, indent=1)
print(f'{len(segs)} segs, {len(caps)} caps, {len(cards)} panels, {total:.2f}s')
for b in T:
    blk = [s for s in segs if s['block'] == b['id']]
    print(f"  {b['id']:3s} {blk[0]['out_start']:6.2f}-{blk[-1]['out_end']:6.2f}  {b['clip']} {b['s']}-{b['e']} x{b['speed']} gain {b.get('gain', 0)}")
