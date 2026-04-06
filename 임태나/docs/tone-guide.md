# Boonz Streamlit 메시지 & 톤앤매너 가이드
# 이 파일의 메시지를 app.py에 적용해줘.

## 핵심 톤
- 관계: 나 ↔ 분즈 ↔ 식물, 3자 대화
- 셀프케어: 식물을 돌보는 시간 = 나를 돌보는 시간
- 모든 메시지에서 "너의 돌봄"을 인정해줘야 함

---

## 1. 온보딩 메시지

```python
# 첫 진입
title = "식물 별명을\n하나 지어줘."
subtitle = "이름을 부르면, 관계가 시작돼."
boonz_msg = "별명 하나만 알려줘. 내가 기억할게"

# 등록 완료
boonz_msg = f"{nickname}? 좋은 이름이다. 잘 부탁해"
```

---

## 2. 메인 화면 동적 인사

```python
# 시간별 (메인 타이틀)
hour = datetime.now().hour
if hour < 9:
    title = f"좋은 아침.\n{nickname} 오늘도 잘 있을까?"
elif hour < 13:
    title = f"오늘은 {nickname}한테\n뭐 해줄 거야?"
elif hour < 18:
    title = f"{nickname}한테\n잠깐 들러볼까?"
else:
    title = f"오늘 하루 수고했어.\n{nickname}도 잘 있었을까?"

# 돌봄 공백별 (분즈 메시지)
if gap == 0:
    boonz_msg = f"오늘도 {nickname} 챙겨주네. 이런 시간이 너한테도 좋은 거야"
elif gap == 1:
    last_action_label = ACTION_LABELS.get(last_action, "")
    boonz_msg = f"어제 {last_action_label} 해줬지? 꾸준한 거 좋다"
elif gap == 2:
    boonz_msg = f"이틀 만이네. {nickname} 보고 싶었을걸"
elif gap <= 5:
    boonz_msg = f"{gap}일 만이다. 바빴구나. {nickname}은 기다리고 있었어"
else:
    boonz_msg = f"{gap}일째야. 바쁜 거 알지만, {nickname} 좀 봐줘. 잠깐이면 돼"
```

---

## 3. 관계 성장 단계

```python
if days <= 7:
    status_emoji = "🌱"
    status_text = "새로운 만남"
    status_desc = "서로 알아가는 중이야. 자주 들러줘"
elif days <= 30:
    status_emoji = "🌿"
    status_text = "알아가는 중"
    status_desc = "돌봄이 습관이 되고 있어. 좋은 신호야"
elif days <= 90:
    status_emoji = "🪴"
    status_text = "함께하는 사이"
    status_desc = f"{nickname}가 너의 하루 일부가 됐네"
else:
    status_emoji = "🌳"
    status_text = "오랜 친구"
    status_desc = f"이쯤 되면 {nickname}가 너를 돌보는 거야"
```

---

## 4. 진단 결과 메시지

```python
# 병변% 별 분기
if ratio <= 5:
    mood = "happy"
    msg = f"{nickname}한테 물어봤는데, 요즘 컨디션 좋대. 네가 잘 돌봐준 거야"
    severity_text = "건강해 보여"
elif ratio <= 10:
    mood = "default"
    msg = f"{nickname}한테 물어봤는데, 살짝 신경 쓰이는 데가 있대. 크게 걱정할 건 아니야"
    severity_text = "초기 — 지금 잡으면 돼"
elif ratio <= 25:
    mood = "worried"
    msg = f"{nickname}가 좀 힘들다는데? 근데 너가 빨리 알아챈 거니까 괜찮아. 같이 돌보자"
    severity_text = "중기 — 관심이 필요해"
else:
    mood = "sad"
    msg = f"{nickname}가 많이 아프대... 빨리 도와줘야 할 거 같아. 네가 옆에 있어서 다행이야"
    severity_text = "후기 — 적극적인 케어 필요"

# 프로그레스 바 아래 텍스트
progress_text = f"병변 {ratio:.1f}% — {severity_text}"
```

---

## 5. 케어 가이드 메시지

```python
# 가이드 시작 (Ollama 프롬프트에 추가)
guide_prefix = f"{nickname}한테 물어봤는데,"

# 가이드 끝에 추가
guide_suffix = f"네가 이렇게 신경 써주는 거, {nickname}한테 큰 힘이 될 거야"
```

---

## 6. 원터치 케어 로그 메시지

```python
# 버튼 클릭 후 메시지 (랜덤 또는 상황별)
import random

care_responses = {
    "water": [
        f"{nickname}한테 전해놨어! 물 받아서 좋아하겠다",
        f"기록했어. 꾸준히 챙겨주는 너 멋있다",
        f"{nickname}이 시원하대. 고마워",
    ],
    "medicine": [
        f"{nickname}한테 전해놨어! 빨리 나을 거야",
        f"약 줬구나. 네가 옆에 있어서 {nickname}이 든든할 거야",
    ],
    "observe": [
        f"그냥 봐주는 것도 돌봄이야. {nickname}이 알고 있을 거야",
        f"가만히 지켜봐주는 것만으로도 충분할 때가 있어",
    ],
    "move": [
        f"{nickname}한테 전해놨어! 새 자리 마음에 들어하겠다",
    ],
    "prune": [
        f"정리해줬구나. {nickname}이 한결 가벼워졌을 거야",
    ],
    "repot": [
        f"분갈이까지! 너 진짜 잘 챙긴다. {nickname}이 좋아할 거야",
    ],
    "clean": [
        f"잎 닦아줬구나. {nickname}이 상쾌하대",
    ],
}

msg = random.choice(care_responses.get(action, [f"{nickname}한테 전해놨어!"]))
```

---

## 7. 통합 타임라인 (돌봄 일기)

```python
# 타임라인 섹션 제목
section_title = f"{nickname}와의 이야기"

# 병변 감소 시 코멘트
if log.get("lesion"):
    prev_lesion = previous_log_lesion  # 이전 진단 병변
    curr_lesion = log["lesion"]
    if prev_lesion and curr_lesion < prev_lesion:
        comment = "좋아지고 있어!"
    elif curr_lesion <= 0.05:
        comment = f"{nickname}가 많이 나아졌대"
    else:
        comment = "힘내자"
else:
    comment = ""

# 회복 여정 시각화 (이모지)
# 🥀 아픈 날 → 🌱 치료 시작 → 🌿 회복 중 → 🪴 거의 다 나음 → 🌳 건강
def get_recovery_emoji(lesion_ratio):
    if lesion_ratio > 0.2:
        return "🥀"
    elif lesion_ratio > 0.1:
        return "🌱"
    elif lesion_ratio > 0.05:
        return "🌿"
    elif lesion_ratio > 0.02:
        return "🪴"
    else:
        return "🌳"
```

---

## 8. 패턴 분석 메시지

```python
# Ollama 프롬프트 (pattern)
pattern_prompt = f"""너는 분즈야.

{nickname}의 돌봄 기록을 봤어:
{care_log_text}

이 기록을 보고 사용자의 돌봄 패턴을 분석해줘.

포함할 것:
1) 물 주기 패턴 — 간격이 규칙적인지
2) 진단 → 조치 → 회복 패턴 — 아플 때 어떻게 대응했는지
3) 잘하고 있는 점 — 구체적으로 칭찬해줘
4) 한 가지 팁 — 부드럽게 제안

톤: 
- "{nickname}가 그러는데," 로 시작해
- 데이터를 나열하지 말고, 사람한테 말하듯이
- 마지막에 "너의 돌봄이 {nickname}을 이만큼 성장시킨 거야" 느낌으로 마무리
- 식물을 돌보는 시간이 본인한테도 좋은 시간이라는 뉘앙스

예시:
"{nickname}가 그러는데, 너가 3~4일마다 물 주는 거 딱 좋대.
약 준 다음에 확실히 나아졌어. 빠른 대응이 좋았어.
잎 닦기를 좀 더 자주 하면 좋겠다고는 하더라.
솔직히 너 꽤 잘 키우는 듯. 이런 시간이 너한테도 의미 있을 거야."
"""
```

---

## 9. 돌봄 리포트 카드 (패턴 분석 상단)

```python
# 3가지 숫자
report = {
    "total": len(care_logs),          # "총 기록"
    "streak": streak,                  # "연속 돌봄"
    "recovery": f"-{lesion_decrease}%", # "병변 감소" (있으면)
}

# 분즈 리포트 한마디
if streak >= 7:
    report_msg = f"7일 연속이라니. {nickname}도 너도 대단해"
elif total >= 30:
    report_msg = f"30번이나 챙겼어. 이건 습관이 된 거야"
elif recovery:
    report_msg = f"봐봐, 너의 돌봄이 {nickname}을 이만큼 살린 거야"
else:
    report_msg = f"기록이 쌓이고 있어. 계속 가보자"
```

---

## 10. 이정표 메시지

```python
milestones = {
    1: f"{nickname}이랑 첫 기록이다! 여기서부터 시작이야",
    5: f"벌써 5번째. 슬슬 리듬이 생기고 있어",
    10: f"10번째 기록! {nickname}이 너한테 고마워하고 있을걸",
    20: f"20번이나 챙겼어. 너 이거 진심이구나",
    30: f"30번째... {nickname}이 많이 의지하고 있을 거야",
    50: f"50번째. 이쯤 되면 {nickname}가 너를 돌보는 거야",
    100: f"100번. 할 말 잃었어. 그냥 대단하다",
}
```

---

## 11. 에러 메시지 (셀프케어 톤 유지)

```python
error_messages = {
    "api_fail": "앗 나 잠깐 버그남. 근데 괜찮아, 다시 해볼게",
    "no_diagnosis": f"먼저 {nickname} 사진을 찍어줘. 뭐가 필요한지 알아야 도와줄 수 있어",
    "ollama_fail": "지금 좀 생각이 느려... 잠깐만 기다려줘",
    "tts_fail": "목소리가 안 나와. 글로 읽어줘",
    "upload_fail": "사진이 안 열려. 다른 사진으로 해볼래?",
}
```

---

## 12. 바텀 네비 + 빈 탭 메시지

```python
# 각 탭에 처음 진입했을 때 (아무 것도 안 했을 때)
tab_empty = {
    "tab1": (f"{nickname} 사진 줘. 내가 봐줌", "default"),
    "tab2": (f"뭐가 궁금해? 내가 {nickname}한테 물어볼게", "default"),
    "tab3": ("뭐 사왔어? 보여줘", "default"),
    "tab4_no_logs": (f"아직 {nickname}이랑 기록이 없네. 위에 버튼 눌러봐. 하나만 눌러도 시작이야", "default"),
    "tab4_has_logs": (f"오늘도 {nickname} 챙겨줄 거야?", "default"),
}
```

---

## 13. 관계 여정 화면 (시연용 — 탭4 하단)

```python
# 시연에서 보여줄 관계 여정 시각화
journey_stages = [
    {"emoji": "🌱", "title": "새로운 만남", "date": registered_date, "desc": f'"{nickname}? 잘 부탁해"'},
    {"emoji": "😟", "title": "아픈 날", "date": first_diagnosis_date, "desc": f"첫 진단. 같이 이겨내자"},
    {"emoji": "💊", "title": "함께 이겨내기", "date": treatment_period, "desc": f"15% → 8% → 5%"},
    {"emoji": "🌿", "title": "알아가는 중", "date": day30_date, "desc": f"돌봄이 습관이 되고 있어"},
    {"emoji": "🌳", "title": "거의 회복!", "date": recovery_date, "desc": f"봐봐, 너가 잘 돌봐준 거야"},
]

# 마무리 메시지
closing = "돌봄이 관계가 되고, 관계가 나를 비추는 거울이 됩니다"
```
