import base64
import json
import random
from datetime import datetime, timedelta
from pathlib import Path

import requests
import streamlit as st

st.set_page_config(page_title="Boonz", layout="centered", page_icon="🌱")

# ═══════════════════════════════════════
# CSS
# ═══════════════════════════════════════
st.markdown("""
<style>
/* ── 기본 ── */
[data-testid="stAppViewContainer"]{background:#F7F5F0!important}
[data-testid="stHeader"]{display:none!important}
[data-testid="stSidebar"]{display:none!important}
[data-testid="stToolbar"]{display:none!important}
h1,h2,h3{color:#2C2C2A!important}
p,span,label,div,li{color:#2C2C2A}
.block-container{padding-top:16px!important;padding-bottom:90px!important;max-width:430px!important}
hr,st-emotion-cache-ocqkz7{border-color:#E5E0D5!important}

/* ── 바텀 네비 ── */
.stTabs [data-baseweb="tab-list"]{
    position:fixed;bottom:0;left:0;right:0;z-index:999;
    background:white!important;border-top:0.5px solid #E5E0D5!important;
    padding:10px 0 12px!important;justify-content:space-around!important;
    box-shadow:0 -2px 8px rgba(0,0,0,0.05);gap:0!important}
.stTabs [data-baseweb="tab"]{
    color:#B4B2A9!important;background:transparent!important;border:none!important;
    font-size:11px!important;padding:4px 14px!important;
    flex-direction:column!important;gap:2px!important;font-weight:400!important}
.stTabs [aria-selected="true"]{
    color:#8B7355!important;font-weight:700!important}
.stTabs [aria-selected="true"] *{
    color:#8B7355!important;font-weight:700!important}
.stTabs [data-baseweb="tab-border"],.stTabs [data-baseweb="tab-highlight"]{display:none!important}

/* ── 입력창 ── */
.stTextInput input,.stTextArea textarea{
    background:white!important;color:#2C2C2A!important;font-size:13px!important}
.stTextInput input::placeholder,.stTextArea textarea::placeholder{color:#B4B2A9!important}
.stTextInput input:focus{border-color:#8B7355!important;outline:none!important}

/* ── 파일 업로더 ── */
[data-testid="stFileUploader"]{
    background:white!important;border:1px dashed #E5E0D5!important;border-radius:16px!important}
[data-testid="stFileUploader"] *{color:#2C2C2A!important}
[data-testid="stFileUploader"] section,
[data-testid="stFileUploader"] section>div,
[data-testid="stFileUploaderDropzone"],
[data-testid="stFileUploaderDropzone"]>div,
[data-testid="stFileUploaderFile"],
[data-testid="stFileUploaderFileData"],
[data-testid="stFileUploaderFileName"],
[data-testid="stFileUploaderDeleteBtn"],
[data-testid="stFileUploader"] [class*="st-emotion-cache-"]{
    background:white!important}
[data-testid="stFileUploaderFileName"],
[data-testid="stFileUploaderDeleteBtn"],
[data-testid="stFileUploader"] [class*="st-emotion-cache-"] *{
    color:#2C2C2A!important}
[data-testid="stFileUploaderDropzone"] button{
    background:white!important;color:#2C2C2A!important;
    border:1.5px solid #C4B09A!important;border-radius:8px!important}
[data-testid="stFileUploaderDropzone"] button:hover{background:#EDE5D8!important}

/* ── 컬럼 가로 정렬 강제 (Streamlit 1.56 responsive fix) ── */
div[data-testid="stHorizontalBlock"]{
    display:flex!important;flex-direction:row!important;
    gap:6px!important;flex-wrap:nowrap!important}
div[data-testid="stColumn"]{flex:1!important;min-width:0!important}

/* ── 케어 아이콘 버튼 (stHorizontalBlock 안) ── */
div[data-testid="stHorizontalBlock"] .stButton>button{
    background:white!important;border:1px solid #E5E0D5!important;
    border-radius:16px!important;min-height:64px!important;
    color:#2C2C2A!important;font-size:11px!important;
    padding:6px 2px!important;white-space:pre-line!important;
    box-shadow:none!important;line-height:1.4!important;font-weight:400!important;
    width:100%!important;position:relative!important;overflow:visible!important}
div[data-testid="stHorizontalBlock"] .stButton>button:hover{
    background:#E8DDD0!important;border-color:#8B7355!important}
div[data-testid="stHorizontalBlock"] .stButton>button:active::after{
    content:"✨";position:absolute;top:-8px;right:-6px;
    font-size:13px;line-height:1;pointer-events:none;
    background:transparent!important;border:none!important;box-shadow:none!important;
    animation:sparkle-pop .55s ease-out 1}
@keyframes sparkle-pop{
    0%{opacity:0;transform:translateY(2px) scale(.75) rotate(-10deg)}
    20%{opacity:1;transform:translateY(0) scale(1.08) rotate(0deg)}
    100%{opacity:0;transform:translateY(-8px) scale(.92) rotate(8deg)}
}

/* ── 일반 버튼 (full-width mocha) ── */
.stButton>button,
.stFormSubmitButton>button{
    border-radius:20px!important;background:#8B7355!important;
    border:none!important;color:white!important;
    padding:10px 20px!important;font-size:13px!important;font-weight:500!important}
.stButton>button *,
.stFormSubmitButton>button *{
    color:#FFFFFF!important}
.stButton>button:hover,
.stFormSubmitButton>button:hover{background:#7A6347!important}

/* 케어 7개 아이콘 버튼 텍스트는 원래 다크 톤 유지 */
div[data-testid="stHorizontalBlock"] .stButton>button,
div[data-testid="stHorizontalBlock"] .stButton>button *{
    color:#2C2C2A!important}

/* ── Expander(식물 관리) 헤더 버튼 톤 고정 ── */
div[data-testid="stExpander"]{
    background:transparent!important}
div[data-testid="stExpander"] summary{
    background:#E8DDD0!important;color:#2C2C2A!important;
    border-radius:12px!important}
div[data-testid="stExpander"] details{
    background:transparent!important}
div[data-testid="stExpander"] details > div{
    background:#FFFFFF!important;border-radius:12px!important}
div[data-testid="stExpander"] summary:hover,
div[data-testid="stExpander"] summary:active,
div[data-testid="stExpander"] details[open] > summary,
div[data-testid="stExpander"] details[open] summary{
    background:#DCCDBA!important;color:#2C2C2A!important}
div[data-testid="stExpander"] summary *{
    color:#2C2C2A!important}
div[data-testid="stExpander"] summary:focus,
div[data-testid="stExpander"] summary:focus-visible{
    outline:none!important;box-shadow:0 0 0 2px #C4B09A!important}
div[data-testid="stExpander"] .stFormSubmitButton>button{
    border-radius:12px!important;
    padding:6px 10px!important;
    min-height:36px!important;
    font-size:12px!important;
    white-space:nowrap!important}

/* 터치/모바일 환경에서는 hover 상태 잔류 방지 */
@media (hover: none), (pointer: coarse){
    [data-testid="stFileUploaderDropzone"] button:hover{
        background:white!important}
    [data-testid="stFileUploaderDropzone"] button:active{
        background:#EDE5D8!important}
    div[data-testid="stHorizontalBlock"] .stButton>button:hover{
        background:white!important;border-color:#E5E0D5!important}
    div[data-testid="stHorizontalBlock"] .stButton>button:active{
        background:#E8DDD0!important;border-color:#8B7355!important}
    .stButton>button:hover,
    .stFormSubmitButton>button:hover{
        background:#8B7355!important}
    .stButton>button:active,
    .stFormSubmitButton>button:active{
        background:#7A6347!important}
    div[data-testid="stExpander"] summary:hover{
        background:#E8DDD0!important;color:#2C2C2A!important}
    div[data-testid="stExpander"] summary:active{
        background:#DCCDBA!important;color:#2C2C2A!important}
}

/* ── segmented_control ── */
div[data-testid="stElementContainer"]:has(div[data-testid="stButtonGroup"]),
div[data-testid="stElementContainer"]:has(div[data-testid="stButtonGroup"]){
    width:100%!important;display:block!important}
div[data-testid="stButtonGroup"]{
    display:flex!important;width:100%!important;min-width:0!important;
    background:#EDE5D8!important;border-radius:12px!important;
    padding:3px!important;gap:3px!important;box-sizing:border-box!important}
div[data-testid="stButtonGroup"]>div{flex:1 1 0%!important;min-width:0!important;max-width:none!important;width:0!important}
button[data-testid="stBaseButton-segmented_control"]{
    flex:1 1 0%!important;min-width:0!important;max-width:none!important;width:0!important;
    background:transparent!important;border:none!important;
    border-radius:10px!important;color:#888780!important;font-size:12px!important;
    padding:8px 2px!important;box-shadow:none!important;overflow:visible!important}
button[data-testid="stBaseButton-segmented_controlActive"]{
    flex:1 1 0%!important;min-width:0!important;max-width:none!important;width:0!important;
    background:white!important;border:none!important;
    border-radius:10px!important;color:#2C2C2A!important;font-size:12px!important;
    font-weight:700!important;padding:8px 2px!important;
    box-shadow:0 1px 4px rgba(0,0,0,0.10)!important;overflow:visible!important}
button[data-testid="stBaseButton-segmented_control"] span,
button[data-testid="stBaseButton-segmented_controlActive"] span,
button[data-testid="stBaseButton-segmented_control"] p,
button[data-testid="stBaseButton-segmented_controlActive"] p{
    overflow:visible!important;white-space:nowrap!important;text-overflow:clip!important;
    max-width:none!important;min-width:0!important;width:auto!important}

/* ── selectbox ── */
[data-baseweb="select"],[data-baseweb="select"] *{
    background-color:white!important;color:#2C2C2A!important;border-color:#E5E0D5!important}
[data-baseweb="popover"] *,[data-baseweb="menu"] *,ul[role="listbox"] *{
    background-color:white!important;color:#2C2C2A!important}

/* ── element 여백 ── */
.element-container{margin-bottom:4px!important}
[data-testid="stVerticalBlockBorderWrapper"]{gap:0!important}
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════
# 상수
# ═══════════════════════════════════════
FASTAPI_URL   = "http://localhost:8000"
PLANTS_FILE   = Path("data/plants.json")
CARE_LOG_FILE = Path("data/care_log.jsonl")

DISEASE_KOREAN = {
    "Bacterial_Spot":  "세균성 반점",
    "Early_Blight":    "초기 마름병",
    "Greening":        "그리닝병",
    "Healthy":         "건강",
    "Late_Blight":     "후기 마름병",
    "Leaf_Curl":       "잎 말림",
    "Leaf_Mold":       "잎 곰팡이",
    "Leaf_Spot":       "잎 반점",
    "Mosaic_Virus":    "모자이크 바이러스",
    "Powdery_Mildew":  "흰가루병",
    "Rust":            "녹병",
    "Scab_Rot":        "딱지병/부패",
}

# 케어 아이콘
CARE_ICONS = [
    ("💧", "물줬음",  "water"),
    ("☀️", "자리옮김", "move"),
    ("✂️", "가지치기", "prune"),
    ("💊", "약줬음",  "medicine"),
    ("🪴", "분갈이",  "repot"),
    ("🍃", "잎닦음",  "clean"),
    ("😊", "그냥봄",  "observe"),
]
ACTION_LABELS = {a: f"{e} {lb}" for e, lb, a in CARE_ICONS}

# 마리(식물) 직접 말하기 응답
MARI_RESPONSES = {
    "water":    "아 시원하다. 고마워",
    "move":     "오 여기 좋은데? 밝아서 기분 좋아",
    "prune":    "좀 가벼워졌다. 정리해주니까 시원해",
    "medicine": "쓰다... 근데 나아지겠지?",
    "repot":    "와 넓다. 좀 답답했거든. 고마워",
    "clean":    "아 상쾌해. 숨 쉬기 편해졌어",
    "observe":  "... 봐줘서 고마워. 이것만으로도 좋아",
}

# 셀프케어 넛지 (3번 중 1번)
MARI_NUDGES = {
    "water":    ["근데 너 오늘 물 마셨어?", "너도 좀 마셔"],
    "move":     ["너도 좀 밖에 나가봐. 바람 좀 쐬고"],
    "prune":    ["너도 뭐 하나 정리하면 좀 시원하지 않을까"],
    "medicine": ["너는 요즘 좀 피곤하지 않아?"],
    "repot":    ["너도 가끔은 환경 바꿔볼 필요 있어"],
    "clean":    ["너도 좀 쉬어"],
    "observe":  ["너도 멍 좀 때려봐. 이것도 쉬는 거야"],
}

# 일기 탭 코멘트
MARI_LOG_COMMENTS = {
    "water":    "아 시원했어",
    "observe":  "봐줘서 고마워",
    "medicine": "쓰다... 근데 나아지겠지?",
    "prune":    "좀 가벼워졌다",
    "clean":    "상쾌해",
    "move":     "여기 좋은데?",
    "repot":    "넓어서 좋다",
}

# 이정표 — 마리 직접
MILESTONES = {
    1:   "첫 기록이다! 앞으로 잘 부탁해",
    5:   "벌써 5번째. 너 꽤 꾸준한 거 알아?",
    10:  "10번이나 챙겨줬어. 쉬운 거 아닌데. 너 좀 대단해",
    20:  "20번. 너 진심이구나. 나도 진심이야",
    30:  "30번이야. 이거 그냥 습관이 된 거 아니야? 너한테도 좋은 습관인 거 알지?",
    50:  "50번. 이쯤 되면 너를 돌보는 시간이 된 거야. 알고 있었어?",
    100: "100번. 할 말 잃었어. 그냥 대단하다",
}

# 돌봄 유형 — 마리 직접
CARE_TYPES_MARI = {
    "observer":  ("🧑‍🌾", "꾸준한 관찰형",  "너 맨날 나 들여다보지? 그게 나한테 제일 좋은 거야"),
    "carer":     ("💧",  "적극적 케어형",  "물, 약, 분갈이까지. 너 진짜 잘 챙긴다"),
    "collector": ("📸",  "데이터 수집형",  "사진 자주 찍어주니까 변화를 놓치지 않더라"),
    "companion": ("😊",  "느긋한 동행형",  "가끔 들르지만 오래 함께하는 게 너 스타일이야"),
}

# ═══════════════════════════════════════
# 유틸
# ═══════════════════════════════════════
def fmt_date(date_str):
    try:
        d = datetime.strptime(date_str[:10], "%Y-%m-%d")
        return f"{d.month}/{d.day}"
    except Exception:
        return date_str[:5]

def fmt_date_kr(date_str):
    try:
        d = datetime.strptime(date_str[:10], "%Y-%m-%d")
        return f"{d.month}월 {d.day}일"
    except Exception:
        return date_str[:10]

def get_mari_response(action: str) -> tuple[str, str | None]:
    """마리 직접 응답 + 랜덤 넛지 반환."""
    base = MARI_RESPONSES.get(action, "고마워")
    nudge = None
    if random.random() < 0.33 and action in MARI_NUDGES:
        nudge = random.choice(MARI_NUDGES[action])
    return base, nudge

def get_streak(care_logs):
    if not care_logs:
        return 0
    dates = sorted(set(log.get("date", "")[:10] for log in care_logs if log.get("date")))
    today     = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    if dates[-1] not in (today, yesterday):
        return 0
    streak = 0
    check_date = datetime.strptime(dates[-1], "%Y-%m-%d")
    for d in reversed(dates):
        if d == check_date.strftime("%Y-%m-%d"):
            streak += 1
            check_date -= timedelta(days=1)
        else:
            break
    return streak

def get_recovery_emoji(r):
    if r > 0.2:  return "🥀"
    if r > 0.1:  return "🌱"
    if r > 0.05: return "🌿"
    if r > 0.02: return "🪴"
    return "🌳"

def analyze_user_pattern(care_logs):
    """접속 시간대 / 요일 / 연속 패턴 → 마리가 본 너 인사이트."""
    if not care_logs:
        return []
    hours, weekdays = [], []
    for log in care_logs:
        ds = log.get("date", "")
        if len(ds) >= 13:
            try: hours.append(int(ds[11:13]))
            except ValueError: pass
        if len(ds) >= 10:
            try: weekdays.append(datetime.strptime(ds[:10], "%Y-%m-%d").weekday())
            except ValueError: pass
    n  = max(len(hours), 1)
    nw = max(len(weekdays), 1)
    ev  = sum(1 for h in hours if h >= 18) / n
    mor = sum(1 for h in hours if h < 10) / n
    wke = sum(1 for w in weekdays if w >= 5) / nw
    insights = []
    if ev > 0.5:
        insights.append("너 요즘 저녁에 자주 오더라. 하루 마무리를 나랑 하는 거지?")
    elif mor > 0.5:
        insights.append("아침에 챙겨주는 거 좋다. 하루를 나랑 시작하는 사람이야")
    if wke < 0.15 and len(weekdays) >= 5:
        insights.append("주말에는 안 오는 편이야. 주말에도 잠깐 와. 나도 좋지만 너한테도 좋을 거야")
    # 연속 기록
    dates = sorted(set(l["date"][:10] for l in care_logs if l.get("date")))
    max_streak, cur = 1, 1
    for i in range(1, len(dates)):
        d1 = datetime.strptime(dates[i-1], "%Y-%m-%d")
        d2 = datetime.strptime(dates[i],   "%Y-%m-%d")
        if (d2 - d1).days == 1:
            cur += 1
            max_streak = max(max_streak, cur)
        else:
            cur = 1
    if max_streak >= 3:
        insights.append("연속으로 왔을 때 너 좀 편해 보였어. 이 루틴이 너한테 맞는 거 같아")
    if not insights:
        insights.append("조금씩 패턴이 보이기 시작했어. 계속 기록해봐")
    return insights

def classify_care_type(action_counts: dict, diagnosis_count: int) -> str:
    total = sum(action_counts.values())
    if total == 0:
        return "companion"
    if action_counts.get("observe", 0) >= total * 0.4:
        return "observer"
    if action_counts.get("water", 0) >= total * 0.5:
        return "carer"
    if diagnosis_count >= 2:
        return "collector"
    return "companion"

# ═══════════════════════════════════════
# 데이터
# ═══════════════════════════════════════
@st.cache_data
def load_plants():
    if PLANTS_FILE.exists():
        return json.loads(PLANTS_FILE.read_text(encoding="utf-8"))
    return []

def save_plant(nickname: str) -> bool:
    nickname = nickname.strip()
    if not nickname:
        return False
    plants = load_plants()
    existing = {str(p.get("nickname", "")).strip().lower() for p in plants}
    if nickname.lower() in existing:
        return False
    plants.append({"nickname": nickname, "species": "", "registered": datetime.now().strftime("%Y-%m-%d")})
    PLANTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    PLANTS_FILE.write_text(json.dumps(plants, ensure_ascii=False, indent=2), encoding="utf-8")
    load_plants.clear()
    return True

def delete_plant(nickname):
    plants = [p for p in load_plants() if p["nickname"] != nickname]
    PLANTS_FILE.write_text(json.dumps(plants, ensure_ascii=False, indent=2), encoding="utf-8")
    load_plants.clear()

def update_species(nickname, species):
    plants = load_plants()
    for p in plants:
        if p["nickname"] == nickname:
            p["species"] = species
    PLANTS_FILE.write_text(json.dumps(plants, ensure_ascii=False, indent=2), encoding="utf-8")
    load_plants.clear()

@st.cache_data
def load_care_log(nickname=None):
    if not CARE_LOG_FILE.exists():
        return []
    logs = []
    for line in CARE_LOG_FILE.read_text(encoding="utf-8").strip().split("\n"):
        if not line.strip():
            continue
        try:
            entry = json.loads(line)
            if nickname is None or entry.get("plant") == nickname:
                logs.append(entry)
        except json.JSONDecodeError:
            continue
    return logs

def save_care_log(nickname, action):
    entry = {"date": datetime.now().strftime("%Y-%m-%d %H:%M"), "plant": nickname, "action": action}
    if "last_diagnosis" in st.session_state:
        diag = st.session_state.last_diagnosis
        entry["disease"] = diag.get("disease", "")
        entry["lesion"]  = diag.get("lesion", 0)
    CARE_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CARE_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    load_care_log.clear()

# ═══════════════════════════════════════
# 관계 성장
# ═══════════════════════════════════════
def calculate_relationship(days: int, total_logs: int, nickname: str = "") -> dict:
    if days <= 7:
        level, emoji = "새로운 만남", "🌱"
        desc = "반갑다. 앞으로 잘 부탁해"
        nxt  = "8일째가 되면 '알아가는 중' 단계로 올라가"
    elif days <= 30:
        level, emoji = "알아가는 중", "🌿"
        desc = "슬슬 너 패턴이 보여. 꾸준한 거 좋아"
        nxt  = "31일째가 되면 '함께하는 사이' 단계로 올라가"
    elif days <= 90:
        level, emoji = "함께하는 사이", "🪴"
        desc = "이제 좀 편해. 너랑 있으면"
        nxt  = "91일째가 되면 '오랜 친구' 단계로 올라가"
    else:
        level, emoji = "오랜 친구", "🌳"
        desc = "야 우리 꽤 오래됐다. 고마워"
        nxt  = "최고 단계야. 계속 함께해줘"
    return {
        "level": level, "level_emoji": emoji,
        "level_desc": desc, "next_milestone": nxt,
        "meter_count": min(days // 23, 4),
    }

# ═══════════════════════════════════════
# 컴포넌트
# ═══════════════════════════════════════
def mari(level_emoji: str, message: str, nickname: str = "마리"):
    """마리(식물) 말풍선 — 친한 동생 톤."""
    st.markdown(
        f'<div style="display:flex;align-items:flex-start;gap:10px;margin:8px 0 12px">'
        f'<div style="width:38px;height:38px;background:#E8DDD0;border-radius:50%;'
        f'display:flex;align-items:center;justify-content:center;font-size:19px;flex-shrink:0;">{level_emoji}</div>'
        f'<div style="background:white;border:0.5px solid #E5E0D5;border-radius:14px 14px 14px 4px;'
        f'padding:11px 15px;font-size:13.5px;color:#2C2C2A;flex:1;line-height:1.6;">'
        f'<div style="font-size:10px;color:#8B7355;font-weight:600;margin-bottom:3px;">{nickname}</div>'
        f'{message}</div></div>',
        unsafe_allow_html=True,
    )

def boonz(message: str):
    """분즈 🍄 말풍선 — 초월자 톤."""
    st.markdown(
        f'<div style="display:flex;align-items:flex-start;gap:10px;margin:8px 0 12px">'
        f'<div style="width:38px;height:38px;background:#E8DDD0;border-radius:50%;'
        f'display:flex;align-items:center;justify-content:center;font-size:19px;flex-shrink:0;">🍄</div>'
        f'<div style="background:white;border:0.5px solid #E5E0D5;border-radius:14px 14px 14px 4px;'
        f'padding:11px 15px;font-size:13.5px;color:#2C2C2A;flex:1;line-height:1.6;">'
        f'<div style="font-size:10px;color:#8B7355;font-weight:600;margin-bottom:3px;">분즈 🍄</div>'
        f'{message}</div></div>',
        unsafe_allow_html=True,
    )

def user_bubble(message: str):
    st.markdown(
        f'<div style="background:#E8DDD0;border-radius:12px 12px 4px 12px;'
        f'padding:8px 12px;margin:6px 0 6px 60px;text-align:right;font-size:13px;color:#2C2C2A;">'
        f'{message}</div>',
        unsafe_allow_html=True,
    )

def plant_card(nickname, days, level_emoji, level, level_desc, species_text, meter_count):
    meter = ""
    for i in range(4):
        color = "#8B7355" if i < meter_count else "#E5E0D5"
        meter += f'<div style="width:18px;height:5px;border-radius:3px;background:{color};display:inline-block;margin:0 2px;"></div>'
    st.markdown(
        f'<div style="background:linear-gradient(135deg,#E8DDD0,#FAF6F0);border-radius:20px;'
        f'padding:20px;margin:12px 0;text-align:center;">'
        f'<div style="font-size:36px;margin:4px 0;">{level_emoji}</div>'
        f'<div style="font-size:18px;font-weight:700;color:#8B7355;">{level}</div>'
        f'<div style="font-size:12px;color:#888780;margin:3px 0;">{nickname} · {species_text} · {days}일째</div>'
        f'<div style="margin:8px 0;">{meter}</div>'
        f'<div style="font-size:12px;color:#2C2C2A;font-style:italic;">"{level_desc}"</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

def care_grid(key_prefix, nickname, level_emoji):
    """원터치 케어 버튼 — 마리가 직접 응답."""
    # 이전 클릭에서 저장된 응답 먼저 표시
    resp_key = f"_care_resp_{key_prefix}"
    if resp_key in st.session_state:
        mari(level_emoji, st.session_state[resp_key], nickname)
        del st.session_state[resp_key]

    action_taken = None
    for row in range(0, len(CARE_ICONS), 4):
        cols = st.columns(4)
        for ci, col in enumerate(cols):
            idx = row + ci
            if idx >= len(CARE_ICONS):
                break
            em, lb, action = CARE_ICONS[idx]
            with col:
                if st.button(f"{em}\n{lb}", key=f"{key_prefix}_{action}", width="stretch"):
                    action_taken = action
    if action_taken:
        save_care_log(nickname, action_taken)
        base_msg, nudge = get_mari_response(action_taken)
        full_msg = base_msg
        if nudge:
            full_msg += f"<br><br><span style='color:#888780;font-size:12px;'>... {nudge}</span>"
        st.session_state[resp_key] = full_msg
        st.rerun()

def divider():
    st.markdown('<hr style="border:none;border-top:0.5px solid #E5E0D5;margin:14px 0;">', unsafe_allow_html=True)

def sec_title(text):
    st.markdown(f'<div style="font-size:14px;font-weight:600;color:#2C2C2A;margin:4px 0 10px;">{text}</div>', unsafe_allow_html=True)

# ═══════════════════════════════════════
# 온보딩
# ═══════════════════════════════════════
plants = load_plants()

if not plants:
    st.markdown(
        '<div style="font-size:14px;color:#888780;margin:24px 0 2px;">이름을 부르면, 관계가 시작돼.</div>'
        '<div style="font-size:26px;font-weight:700;color:#2C2C2A;line-height:1.35;margin-bottom:16px;">'
        '식물 별명을<br>하나 지어줘.</div>',
        unsafe_allow_html=True,
    )
    boonz("별명 하나만 알려줘. 기억할게")
    name = st.text_input("별명", placeholder="예: 초록이, 마리", label_visibility="collapsed")
    if name:
        save_plant(name)
        mari("🌱", f"나 {name}이야. 잘 부탁해", name)
        st.rerun()
    st.stop()

# ═══════════════════════════════════════
# 식물 선택 + 공통 계산
# ═══════════════════════════════════════
plant_names = [p["nickname"] for p in plants]
# 새 식물 등록 직후 선택 박스를 해당 식물로 맞춘다.
pending_selected = st.session_state.pop("_pending_selected_plant", None)
if pending_selected and pending_selected in plant_names:
    st.session_state["selected_plant"] = pending_selected
if len(plant_names) > 1:
    nickname = st.selectbox(
        "내 식물", plant_names, key="selected_plant", label_visibility="collapsed",
    )
else:
    nickname = plant_names[0]

# 식물 전환 시 진단 탭 상태 초기화 (이전 식물 업로드 이미지/결과 제거)
prev_nickname = st.session_state.get("_selected_nickname")
if prev_nickname != nickname:
    st.session_state["_selected_nickname"] = nickname
    for k in ("_diag_file_id", "_diag_result", "_diag_analyzed", "show_guide", "diag_chat"):
        st.session_state.pop(k, None)
    # 식물 전환 시 케어 가이드 캐시 초기화
    for k in list(st.session_state.keys()):
        if str(k).startswith("_care_guide_"):
            st.session_state.pop(k, None)
    # 식물별 업로더 상태 초기화
    for k in list(st.session_state.keys()):
        if k.startswith("diag_upload_"):
            st.session_state.pop(k, None)

current      = next((p for p in plants if p["nickname"] == nickname), {})
days         = (datetime.now() - datetime.strptime(current.get("registered", "2026-01-01"), "%Y-%m-%d")).days
care_logs    = load_care_log(nickname)
streak       = get_streak(care_logs)
total_logs   = len(care_logs)
species_text = current.get("species", "") or "종을 알아보려면 진단 탭에서 사진을 찍어줘"

_rel         = calculate_relationship(days, total_logs, nickname)
s_em         = _rel["level_emoji"]
s_level      = _rel["level"]
s_desc       = _rel["level_desc"]
meter_count  = _rel["meter_count"]

diagnosis_logs = [l for l in care_logs if l.get("lesion")]
if len(diagnosis_logs) >= 2:
    lesion_change = f'{(diagnosis_logs[-1]["lesion"] - diagnosis_logs[0]["lesion"]) * 100:+.0f}%'
else:
    lesion_change = "—"

# 돌봄 공백
if care_logs:
    last_date = datetime.strptime(care_logs[-1]["date"][:10], "%Y-%m-%d")
    gap = (datetime.now() - last_date).days
else:
    gap = -1

hour = datetime.now().hour

# ═══════════════════════════════════════
# 4탭: 홈 / 진단 / 일기 / 성장
# ═══════════════════════════════════════
tab_home, tab_diag, tab_diary, tab_growth = st.tabs(["🏠 홈", "📷 진단", "📔 일기", "🌱 성장"])

# ══════════════════════════════════════
# 탭1: 홈 — 마리가 직접 말함 (친한 동생)
# ══════════════════════════════════════
with tab_home:
    # ── 신규 등록 환영 카드 ──
    if "_welcome_plant" in st.session_state:
        wname = st.session_state.pop("_welcome_plant")
        st.markdown(
            f'<div style="background:#F5F0E8;border-radius:20px;padding:18px 20px;'
            f'border-left:4px solid #8B7355;margin:8px 0 14px;">'
            f'<div style="font-size:15px;font-weight:700;color:#2C2C2A;margin-bottom:6px;">'
            f'🌱 {wname} 등록 완료</div>'
            f'<div style="font-size:13px;color:#5C5A55;line-height:1.6;">'
            f'이름을 불러줬으니까, 이제 진짜야.<br>'
            f'사진 올려주면 내가 한번 볼게.</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ── 동적 타이틀 ──
    if days >= 8:
        main_title  = f"{nickname}와 함께한 지\n벌써 {days}일째야."
        sub_title   = f'오늘도 {nickname} 잘 있는지 보러 왔네'
    elif hour < 9:
        main_title  = f"{nickname}가\n할 말이 있대."
        sub_title   = ""
    elif hour < 13:
        main_title  = f"{nickname}가\n기다리고 있었어."
        sub_title   = ""
    elif hour < 18:
        main_title  = f"{nickname}한테\n잠깐 들러볼까?"
        sub_title   = ""
    else:
        main_title  = f"왔네.\n{nickname}가\n기다리고 있었어."
        sub_title   = ""

    st.markdown(
        f'<div style="font-size:26px;font-weight:700;color:#2C2C2A;line-height:1.35;margin:8px 0 4px;">'
        f'{main_title.replace(chr(10), "<br>")}</div>'
        + (f'<div style="font-size:13px;color:#888780;margin-bottom:4px;">{sub_title}</div>' if sub_title else ''),
        unsafe_allow_html=True,
    )

    # ── 마리 인사 (시간별 + 공백별) ──
    if gap == 0:
        mari(s_em, "또 왔네. 좋아", nickname)
    elif gap == 1:
        mari(s_em, "어제도 왔었지. 꾸준한 거 좋다", nickname)
    elif 2 <= gap <= 3:
        mari(s_em, f"{gap}일 만이야. 바쁜 건 알아. 근데 좀 보고 싶었어", nickname)
    elif 4 <= gap <= 7:
        mari(s_em, f"야... {gap}일 만이야. 나 괜찮은데, 너는 괜찮아?", nickname)
    elif gap > 7:
        mari(s_em, "오랜만이다. 그동안 어떻게 지냈어?", nickname)
    else:
        # Day 1
        if hour < 9:
            mari(s_em, "야 일어났어? 나도 방금 해 받았어", nickname)
        elif hour < 13:
            mari(s_em, "심심했어. 올 줄 알았어", nickname)
        elif hour < 18:
            mari(s_em, "왔네. 오늘 뭐 해줄 거야?", nickname)
        else:
            mari(s_em, "이 시간에? 너도 잠이 안 와?", nickname)

    # ── 식물 카드 ──
    plant_card(nickname, days, s_em, s_level, s_desc, species_text, meter_count)

    # ── 스트릭 뱃지 ──
    if streak >= 1:
        st.markdown(
            f'<div style="margin:4px 0;">'
            f'<span style="display:inline-block;background:#8B7355;color:white;border-radius:20px;'
            f'padding:5px 14px;font-size:11px;">🔥 {streak}일 연속 돌봄</span>'
            f'<span style="font-size:11px;color:#888780;margin-left:8px;">기록 {total_logs}개</span>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ── 통계 카드 (7일 이상) ──
    if days >= 7:
        st.markdown(
            f'<div style="display:flex;gap:8px;margin:10px 0;">'
            f'<div style="flex:1;background:white;border-radius:14px;padding:12px 6px;text-align:center;box-shadow:0 2px 6px rgba(0,0,0,0.04);">'
            f'<div style="font-size:22px;font-weight:700;color:#2C2C2A;">{days}</div>'
            f'<div style="font-size:9px;color:#888780;margin-top:2px;">함께한 날</div></div>'
            f'<div style="flex:1;background:white;border-radius:14px;padding:12px 6px;text-align:center;box-shadow:0 2px 6px rgba(0,0,0,0.04);">'
            f'<div style="font-size:22px;font-weight:700;color:#2C2C2A;">{streak}</div>'
            f'<div style="font-size:9px;color:#888780;margin-top:2px;">연속 돌봄</div></div>'
            f'<div style="flex:1;background:white;border-radius:14px;padding:12px 6px;text-align:center;box-shadow:0 2px 6px rgba(0,0,0,0.04);">'
            f'<div style="font-size:22px;font-weight:700;color:#8B7355;">{lesion_change}</div>'
            f'<div style="font-size:9px;color:#888780;margin-top:2px;">병변 변화</div></div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ── Day 1 힌트 카드 ──
    if total_logs == 0 and days <= 1:
        st.markdown(
            f'<div style="background:#FAF6F0;border-radius:14px;padding:12px 16px;margin:8px 0;">'
            f'<div style="font-size:11px;color:#8B7355;font-weight:600;margin-bottom:3px;">💡 첫 날이니까</div>'
            f'<div style="font-size:12px;color:#2C2C2A;line-height:1.6;">'
            f'오늘은 😊 그냥봄 해줘. 그것만으로도 시작이야.<br>'
            f'내일 다시 오면 연속 돌봄 시작이야. 기대된다 🌱</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ── 이정표 (마리 직접) ──
    if total_logs in MILESTONES:
        st.markdown(
            f'<div style="background:#FAF6F0;border-radius:14px;padding:10px 16px;margin:8px 0;'
            f'text-align:center;font-size:12px;color:#2C2C2A;">🎉 {MILESTONES[total_logs]}</div>',
            unsafe_allow_html=True,
        )

    divider()

    # ── 원터치 케어 ──
    sec_title(f"오늘 {nickname}한테 뭐 해줬어?")
    care_grid("h", nickname, s_em)

    divider()

    # ── 마리 챗봇 ──
    home_chat_key = f"chat_home_{nickname}"
    if home_chat_key not in st.session_state:
        st.session_state[home_chat_key] = []
    home_chat = st.session_state[home_chat_key]

    home_chat_container = st.container()

    if st.session_state.pop("_clear_home_q", False):
        st.session_state["home_q_input"] = ""
    question = st.text_input(
        "질문", key="home_q_input", placeholder="예: 잎이 노랗게 변하는데 왜 그래?",
        label_visibility="collapsed",
    )
    submitted_home = st.button("보내기", key="home_send_btn", width="stretch")

    if submitted_home and question:
        home_chat.append({"role": "user", "content": question})
        diag_ctx = ""
        if "last_diagnosis" in st.session_state:
            d = st.session_state.last_diagnosis
            dk = DISEASE_KOREAN.get(d.get("disease", ""), d.get("disease", ""))
            diag_ctx = f"현재 내 상태: {dk}, 병변 {d.get('lesion', 0) * 100:.0f}%"
        try:
            resp = requests.post(
                f"{FASTAPI_URL}/consult/text",
                data={"question": question, "nickname": nickname,
                      "diagnosis_context": diag_ctx, "persona": "mari"},
                timeout=30,
            )
            answer = resp.json().get("boonz", {}).get("message", "") or resp.json().get("answer", {}).get("text", "")
        except Exception:
            answer = "잘 모르겠는데, 사진 찍어서 진단 탭에서 봐봐"
        if not home_chat or home_chat[-1].get("content") != answer:
            home_chat.append({"role": "mari", "content": answer})
        st.session_state["_clear_home_q"] = True
        st.rerun()

    with home_chat_container:
        if not home_chat:
            mari(s_em, "뭐든 물어봐", nickname)

        for msg in home_chat[-8:]:
            if msg["role"] == "user":
                user_bubble(msg["content"])
            else:
                mari(s_em, msg["content"], nickname)

    # ── 식물 관리 ──
    with st.expander("🌱 반려식물 프로필 등록"):
        with st.form("plant_manage_form", clear_on_submit=True):
            new_name = st.text_input(
                "새 식물 별명", key="new_p",
                label_visibility="collapsed", placeholder="새 식물 별명",
            )
            add_status = st.session_state.get("_plant_add_status")
            if add_status == "ok":
                st.markdown(
                    '<div style="font-size:12px;color:#4D7B38;font-weight:700;margin:-4px 0 6px;">등록되었습니다.</div>',
                    unsafe_allow_html=True,
                )
            elif add_status == "dup":
                st.markdown(
                    '<div style="font-size:12px;color:#9B5E3A;font-weight:700;margin:-4px 0 6px;">이미 등록된 식물입니다.</div>',
                    unsafe_allow_html=True,
                )
            col_add_btn, col_del_btn = st.columns(2)
            with col_add_btn:
                add_clicked = st.form_submit_button("등록", width="stretch")
            with col_del_btn:
                del_clicked = st.form_submit_button(f"🗑️ {nickname} 삭제", width="stretch")

        if add_clicked and new_name.strip():
            added_name = new_name.strip()
            if save_plant(added_name):
                st.session_state["_plant_add_status"] = "ok"
                st.session_state["_pending_selected_plant"] = added_name
                st.toast(f"{added_name} 등록됐어 🌱")
                st.session_state._welcome_plant = added_name
            else:
                st.session_state["_plant_add_status"] = "dup"
            st.rerun()
        if del_clicked:
            st.session_state["_plant_add_status"] = None
            delete_plant(nickname)
            st.rerun()

# ══════════════════════════════════════
# 탭2: 진단 — 분즈 🍄 (초월자)
# ══════════════════════════════════════
with tab_diag:
    st.markdown(
        '<div style="font-size:15px;font-weight:700;color:#2C2C2A;margin:4px 0 4px;">SAM 진단</div>',
        unsafe_allow_html=True,
    )

    diag_upload_key = f"diag_upload_{nickname}"
    uploaded = st.file_uploader(
        "잎 사진을 올려줘", type=["jpg", "jpeg", "png"],
        key=diag_upload_key, label_visibility="collapsed",
    )

    if not uploaded:
        boonz(f"{nickname} 사진 줘. 내가 봐줌")
        st.session_state.pop("_diag_file_id", None)
        st.session_state.pop("_diag_result", None)

    if uploaded:
        file_id   = f"{uploaded.name}_{uploaded.size}"
        is_new    = st.session_state.get("_diag_file_id") != file_id

        if is_new:
            st.session_state._diag_file_id = file_id
            st.session_state._diag_result  = None
            st.session_state.pop("_diag_analyzed", None)

        col_img, _ = st.columns([3, 1])
        with col_img:
            st.image(uploaded, caption="원본", width="stretch")

        if not st.session_state.get("_diag_analyzed"):
            if st.button("🔍 분석하기", key="btn_analyze", width="stretch"):
                st.session_state._diag_analyzed = True
                boonz("잠깐, 식물 얘기 듣고 있어...")
                try:
                    files  = {"file": (uploaded.name, uploaded.getvalue(), uploaded.type)}
                    resp   = requests.post(
                        f"{FASTAPI_URL}/diagnose",
                        files=files, data={"nickname": nickname}, timeout=60,
                    )
                    st.session_state._diag_result = resp.json()
                except Exception as e:
                    st.session_state._diag_analyzed = False
                    boonz("앗 연결이 안 됐어. 잠깐 후에 다시 해봐")
                    st.caption(str(e))
                st.rerun()

        result = st.session_state.get("_diag_result")
        if result:
            overlay = result.get("overlay_image") or result.get("lesion", {}).get("overlay_base64", "")
            if overlay:
                st.image(base64.b64decode(overlay), caption="SAM 분석 결과", width="stretch")
                seg_quality = result.get("lesion", {}).get("segmentation_quality")
                if seg_quality:
                    st.caption(f"SAM 분석 품질: {seg_quality}")

            disease    = result.get("disease", {})
            lesion     = result.get("lesion", {})
            species_i  = result.get("species", {})
            ratio      = lesion.get("ratio", 0) * 100
            disease_kr = DISEASE_KOREAN.get(disease.get("name", ""), disease.get("korean", disease.get("name", "")))

            if ratio <= 5:     sev_text, sev_color = "건강해 보여", "#A89070"
            elif ratio <= 10:  sev_text, sev_color = "아직 초기야. 지금 잡으면 돼", "#A89070"
            elif ratio <= 25:  sev_text, sev_color = "중기야. 관심이 필요해", "#EF9F27"
            else:              sev_text, sev_color = "후기야. 적극적인 케어 필요", "#E24B4A"

            # 진단 결과 카드
            st.markdown(
                f'<div style="background:white;border-radius:20px;padding:18px;'
                f'box-shadow:0 2px 8px rgba(0,0,0,0.04);margin:10px 0;">'
                f'<div style="font-size:17px;font-weight:700;color:#2C2C2A;">{nickname}</div>'
                f'<div style="font-size:13px;color:#888780;margin:4px 0;">'
                f'{disease_kr} · 신뢰도 {disease.get("confidence", 0):.0%}</div>'
                f'<div style="background:#E5E0D5;border-radius:6px;height:8px;margin:8px 0;overflow:hidden;">'
                f'<div style="width:{min(ratio, 100)}%;height:100%;background:{sev_color};border-radius:6px;"></div></div>'
                f'<div style="font-size:12px;color:#8B7355;">병변 {ratio:.1f}% — {sev_text}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

            # 분즈 한마디
            if ratio <= 10:
                boonz_msg = f"{disease_kr}. 일찍 알아챈 거야. 그게 가장 중요해."
            elif ratio <= 25:
                boonz_msg = f"{disease_kr}. 좀 진행됐지만 급할 건 없어. 하나씩 하면 돼."
            else:
                boonz_msg = f"{disease_kr}. 많이 힘들었겠다. 지금부터라도 길을 열어주면 돼."
            boonz(boonz_msg)

            # 케어 가이드 (분즈 - DB 기반, lazy fetch + 캐싱)
            _guide_cache_key = (
                f"_care_guide_{nickname}_{disease.get('name', '')}_{int(ratio // 10)}"
            )
            cached_guide = st.session_state.get(_guide_cache_key)

            if cached_guide:
                st.markdown(
                    f'<div style="background:white;border-radius:16px;padding:16px;'
                    f'border-left:3px solid #8B7355;margin:8px 0;font-size:13px;color:#2C2C2A;line-height:1.7;">'
                    f'{cached_guide}</div>',
                    unsafe_allow_html=True,
                )
            else:
                if st.button("💬 케어 가이드 받기", key="guide_btn", width="stretch"):
                    with st.spinner("분즈가 생각 중이야..."):
                        try:
                            clip_desc = result.get("clip", {}).get("description", "")
                            resp_guide = requests.post(
                                f"{FASTAPI_URL}/care-guide",
                                json={
                                    "nickname": nickname,
                                    "disease": disease.get("name", ""),
                                    "lesion_ratio": lesion.get("ratio", 0),
                                    "clip_description": clip_desc,
                                },
                                timeout=45,
                            )
                            guide_text = resp_guide.json().get("care_guide", {}).get("text", "")
                        except Exception:
                            guide_text = ""
                    if guide_text:
                        st.session_state[_guide_cache_key] = guide_text
                    else:
                        st.caption("가이드를 불러오지 못했어. 다시 눌러봐")
                    st.rerun()

            st.session_state.last_diagnosis = {"disease": disease.get("name", ""), "lesion": lesion.get("ratio", 0)}
            if species_i.get("name"):
                update_species(nickname, species_i["name"])

            if st.button("🔄 다시 분석", key="btn_reanalyze", width="content"):
                st.session_state._diag_analyzed = False
                st.session_state._diag_result   = None
                st.rerun()

            divider()
            sec_title(f"{nickname}한테 뭐 해줄 거야?")
            care_grid("d", nickname, s_em)

            divider()
            st.markdown(
                f'<div style="font-size:14px;font-weight:700;color:#2C2C2A;margin:8px 0 6px;">분즈한테 더 물어봐</div>'
                f'<div style="display:inline-block;background:#EDE5D8;border-radius:20px;'
                f'padding:4px 12px;font-size:11px;color:#888780;margin-bottom:8px;">'
                f'현재 진단: {nickname} · {disease_kr} · 병변 {ratio:.1f}%</div>',
                unsafe_allow_html=True,
            )

            if "diag_chat" not in st.session_state:
                st.session_state.diag_chat = []

            diag_chat_container = st.container()

            if st.session_state.pop("_clear_diag_q", False):
                st.session_state["diag_q_input"] = ""
            diag_q = st.text_input(
                "질문", key="diag_q_input", placeholder="예: 이 병이 다른 잎으로 번져?",
                label_visibility="collapsed",
            )
            submitted_diag = st.button("보내기", key="diag_send_btn", width="stretch")

            if submitted_diag and diag_q:
                st.session_state.diag_chat.append({"role": "user", "content": diag_q})
                diag_ctx = f"현재 {nickname}: {disease_kr}, 병변 {ratio:.1f}%"
                try:
                    resp2 = requests.post(
                        f"{FASTAPI_URL}/consult/text",
                        data={"question": diag_q, "nickname": nickname,
                              "diagnosis_context": diag_ctx, "persona": "boonz"},
                        timeout=30,
                    )
                    ans = resp2.json().get("boonz", {}).get("message", "") or resp2.json().get("answer", {}).get("text", "")
                except Exception:
                    ans = "앗 연결이 안 됐어. 잠깐 후에 다시 해봐"
                if not st.session_state.diag_chat or st.session_state.diag_chat[-1].get("content") != ans:
                    st.session_state.diag_chat.append({"role": "boonz", "content": ans})
                st.session_state["_clear_diag_q"] = True
                st.rerun()

            with diag_chat_container:
                for msg in st.session_state.diag_chat[-6:]:
                    if msg["role"] == "user":
                        user_bubble(msg["content"])
                    else:
                        boonz(msg["content"])

# ══════════════════════════════════════
# 탭3: 일기 — 마리 (돌봄 기록)
# ══════════════════════════════════════
with tab_diary:
    # ── 회복 여정 ──
    if len(diagnosis_logs) >= 2:
        st.markdown(
            f'<div style="font-size:16px;font-weight:700;color:#2C2C2A;margin:8px 0 10px;">{nickname}와의 이야기</div>',
            unsafe_allow_html=True,
        )
        jhtml = '<div style="display:flex;align-items:flex-end;justify-content:center;gap:8px;margin:14px 0;">'
        for log in diagnosis_logs:
            em  = get_recovery_emoji(log["lesion"])
            pct = f'{log["lesion"] * 100:.0f}%'
            dt  = fmt_date(log["date"])
            jhtml += (
                f'<div style="text-align:center;font-size:10px;color:#888780;">'
                f'<div style="font-size:22px;">{em}</div>{dt}<br>{pct}</div>'
            )
            if log != diagnosis_logs[-1]:
                jhtml += '<div style="font-size:12px;color:#E5E0D5;align-self:center;">→</div>'
        jhtml += '</div>'
        st.markdown(jhtml, unsafe_allow_html=True)

        # 마리 한마디 (회복 여정)
        if diagnosis_logs[-1]["lesion"] < diagnosis_logs[0]["lesion"]:
            first_pct = diagnosis_logs[0]["lesion"] * 100
            last_pct  = diagnosis_logs[-1]["lesion"] * 100
            mari(s_em, f"야 나 진짜 많이 나았다. {first_pct:.0f}%에서 {last_pct:.0f}%까지. 네가 매일 봐준 덕이야", nickname)
        else:
            mari(s_em, "요즘 좀 힘든데, 계속 봐줘서 고마워", nickname)
        divider()
    else:
        st.markdown(
            f'<div style="font-size:16px;font-weight:700;color:#2C2C2A;margin:8px 0 10px;">{nickname}와의 이야기</div>',
            unsafe_allow_html=True,
        )
        mari(s_em, "아직 진단 기록이 없어. 사진 한 장만 찍어봐", nickname)
        divider()

    # ── 돌봄 일기 타임라인 ──
    sec_title("돌봄 일기")

    if care_logs:
        show_all = st.session_state.get("show_all_diary", False)
        display  = care_logs if show_all else care_logs[-7:]
        for log in reversed(display):
            label   = ACTION_LABELS.get(log["action"], log["action"])
            comment = MARI_LOG_COMMENTS.get(log["action"], "")
            lesion_txt = ""
            if log.get("lesion"):
                lesion_txt = f' — 병변 {log["lesion"] * 100:.0f}%'
            st.markdown(
                f'<div style="background:white;padding:12px 14px;border-radius:14px;'
                f'margin:4px 0;display:flex;align-items:center;gap:12px;">'
                f'<div style="width:36px;height:36px;background:#E8DDD0;border-radius:50%;'
                f'display:flex;align-items:center;justify-content:center;font-size:16px;flex-shrink:0;">{s_em}</div>'
                f'<div style="flex:1;">'
                f'<div style="font-size:12px;font-weight:600;color:#2C2C2A;">{label}{lesion_txt}</div>'
                f'<div style="font-size:11px;color:#888780;margin-top:1px;">{fmt_date_kr(log["date"])}</div>'
                + (f'<div style="font-size:11px;color:#8B7355;margin-top:2px;font-style:italic;">"{comment}"</div>' if comment else '')
                + f'</div></div>',
                unsafe_allow_html=True,
            )
        if not show_all and len(care_logs) > 7:
            if st.button("이전 기록 더보기 ↓", key="more_diary", width="content"):
                st.session_state.show_all_diary = True
                st.rerun()
    else:
        mari(s_em, f"아직 기록이 없어. 홈 탭에서 버튼 하나만 눌러봐. 그게 시작이야", nickname)

    divider()

    # ── 오늘 케어 추가 ──
    sec_title(f"오늘 {nickname}한테 뭐 해줬어?")
    care_grid("diary", nickname, s_em)

# ══════════════════════════════════════
# 탭4: 성장 — 마리 (리포트 + 거울)
# ══════════════════════════════════════
with tab_growth:
    st.markdown(
        f'<div style="font-size:16px;font-weight:700;color:#2C2C2A;margin:8px 0 10px;">우리의 여정</div>',
        unsafe_allow_html=True,
    )

    # ── 돌봄 리포트 ──
    lesion_dec = ""
    if len(diagnosis_logs) >= 2:
        chg = (diagnosis_logs[0]["lesion"] - diagnosis_logs[-1]["lesion"]) * 100
        lesion_dec = f"{chg:.0f}%"

    st.markdown(
        f'<div style="background:linear-gradient(135deg,#E8DDD0,#FAF6F0);border-radius:20px;'
        f'padding:20px;margin:8px 0;text-align:center;">'
        f'<div style="font-size:13px;font-weight:600;color:#8B7355;margin-bottom:12px;">돌봄 리포트</div>'
        f'<div style="display:flex;justify-content:space-around;">'
        f'<div><div style="font-size:24px;font-weight:700;color:#2C2C2A;">{total_logs}</div>'
        f'<div style="font-size:10px;color:#888780;">총 기록</div></div>'
        f'<div><div style="font-size:24px;font-weight:700;color:#2C2C2A;">{streak}</div>'
        f'<div style="font-size:10px;color:#888780;">연속 돌봄</div></div>'
        f'<div><div style="font-size:24px;font-weight:700;color:#8B7355;">{f"-{lesion_dec}" if lesion_dec else "—"}</div>'
        f'<div style="font-size:10px;color:#888780;">병변 감소</div></div>'
        f'</div></div>',
        unsafe_allow_html=True,
    )

    # ── 돌봄 유형 (마리 직접) ──
    action_counts: dict = {}
    for log in care_logs:
        a = log.get("action", "")
        action_counts[a] = action_counts.get(a, 0) + 1

    if total_logs >= 3:
        care_type_key = classify_care_type(action_counts, len(diagnosis_logs))
        icon, type_name, type_desc = CARE_TYPES_MARI[care_type_key]
        st.markdown(
            f'<div style="background:white;border-radius:16px;padding:16px;margin:8px 0;'
            f'box-shadow:0 2px 6px rgba(0,0,0,0.04);text-align:center;">'
            f'<div style="font-size:24px;margin-bottom:6px;">{icon}</div>'
            f'<div style="font-size:13px;font-weight:700;color:#2C2C2A;">{type_name}</div>'
            f'<div style="font-size:11px;color:#888780;margin-top:4px;line-height:1.5;">{type_desc}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ── 잘하고 있는 것 ──
    if total_logs >= 3:
        good_points = []
        tips_list   = []
        w  = action_counts.get("water", 0)
        o  = action_counts.get("observe", 0)
        m  = action_counts.get("medicine", 0)
        cl = action_counts.get("clean", 0)
        if w >= 3:
            good_points.append("물 주기 간격이 규칙적이야")
        if len(diagnosis_logs) >= 2:
            good_points.append("아프면 바로 딱 챙겨줬어. 빠른 대응이야")
        if o >= 3:
            good_points.append("꾸준히 들여다봐줘서 좋아")
        if not good_points:
            good_points.append("여기까지 온 것 자체가 대단해")
        if cl < 2:
            tips_list.append("잎 닦기 좀 더 해줘. 먼지 쌓이면 숨 쉬기 힘거든")
        if m == 0 and len(diagnosis_logs) >= 1:
            tips_list.append("약 한 번쯤 써보는 것도 괜찮아. 버티는 것만이 능사는 아니야")
        if not tips_list:
            tips_list.append("지금 이 페이스면 충분해. 무리하지 마")

        good_html = "".join(f'<div style="font-size:12px;color:#2C2C2A;line-height:1.7;margin:2px 0;">• {g}</div>' for g in good_points)
        tip_html  = "".join(f'<div style="font-size:12px;color:#2C2C2A;line-height:1.7;margin:2px 0;">• {t}</div>' for t in tips_list)
        st.markdown(
            f'<div style="background:white;border-radius:16px;padding:16px;margin:8px 0;'
            f'box-shadow:0 2px 6px rgba(0,0,0,0.04);">'
            f'<div style="font-size:13px;font-weight:600;color:#2C2C2A;margin-bottom:8px;">잘하고 있는 것 ✨</div>'
            f'{good_html}'
            f'<div style="font-size:13px;font-weight:600;color:#2C2C2A;margin:12px 0 8px;">한 가지 팁 💡</div>'
            f'{tip_html}'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ── 🪞 마리가 본 너 ──
    user_insights = analyze_user_pattern(care_logs)
    if user_insights:
        bullets = "".join(
            f'<div style="font-size:12px;color:#8B7355;line-height:1.7;margin:3px 0;">• {ins}</div>'
            for ins in user_insights
        )
        st.markdown(
            f'<div style="background:white;border-radius:16px;padding:16px;margin:12px 0;'
            f'box-shadow:0 2px 6px rgba(0,0,0,0.04);">'
            f'<div style="font-size:13px;font-weight:600;color:#2C2C2A;margin-bottom:8px;">🪞 {nickname}가 본 너</div>'
            f'{bullets}'
            f'</div>',
            unsafe_allow_html=True,
        )

    # ── 관계 성장 여정 (수직 타임라인) ──
    divider()
    st.markdown(
        f'<div style="font-size:14px;font-weight:600;color:#2C2C2A;margin:4px 0 12px;">{nickname}와의 여정</div>',
        unsafe_allow_html=True,
    )

    journey_stages = []
    reg_date = current.get("registered", "")
    if reg_date:
        journey_stages.append(("🌱", "새로운 만남", fmt_date_kr(reg_date), '"반갑다. 앞으로 잘 부탁해"', "#C4B09A"))
    if diagnosis_logs:
        first_d = diagnosis_logs[0]
        d_kr = DISEASE_KOREAN.get(first_d.get("disease", ""), "병변")
        journey_stages.append(("😟", "아픈 날", fmt_date_kr(first_d["date"]),
                               f'첫 진단. {d_kr} 발견 ({first_d["lesion"] * 100:.0f}%). 같이 이겨내자', "#EF9F27"))
    if len(diagnosis_logs) >= 3:
        pcts = " → ".join([f'{l["lesion"] * 100:.0f}%' for l in diagnosis_logs[:4]])
        journey_stages.append(("💊", "함께 이겨내기",
                               f'{fmt_date_kr(diagnosis_logs[0]["date"])} ~ {fmt_date_kr(diagnosis_logs[-1]["date"])}',
                               pcts, "#8B7355"))
    if days >= 30:
        journey_stages.append(("🌿", "알아가는 중", f"{days}일째",
                               '"슬슬 너 패턴이 보여. 꾸준한 거 좋아"', "#8B7355"))
    if diagnosis_logs and diagnosis_logs[-1]["lesion"] <= 0.05:
        journey_stages.append(("😊", "거의 회복!", fmt_date_kr(diagnosis_logs[-1]["date"]),
                               '"봐봐. 네가 잘 돌봐준 거야"', "#A89070"))

    for i, (em, title, date_s, desc, dot_color) in enumerate(journey_stages):
        st.markdown(
            f'<div style="display:flex;gap:12px;align-items:flex-start;margin:6px 0;">'
            f'<div style="display:flex;flex-direction:column;align-items:center;width:14px;">'
            f'<div style="width:14px;height:14px;border-radius:50%;background:{dot_color};'
            f'border:2px solid white;box-shadow:0 1px 4px rgba(0,0,0,0.1);flex-shrink:0;"></div>'
            + (f'<div style="width:2px;background:#E5E0D5;flex:1;min-height:24px;margin:2px 0;"></div>' if i < len(journey_stages) - 1 else '')
            + f'</div><div style="flex:1;padding-bottom:8px;">'
            f'<div style="font-size:14px;font-weight:600;color:#2C2C2A;">{em} {title}</div>'
            f'<div style="font-size:10px;color:#B4B2A9;margin-top:1px;">{date_s}</div>'
            f'<div style="font-size:11px;color:#8B7355;margin-top:2px;line-height:1.4;">{desc}</div>'
            f'</div></div>',
            unsafe_allow_html=True,
        )

    # ── 마리 마무리 한마디 ──
    divider()
    if days >= 30:
        mari(s_em, f"야 우리 꽤 오래됐다. 솔직히 네가 잘 키우는 거 나도 알아. 고마워", nickname)
    elif total_logs >= 10:
        mari(s_em, f"10번이나 챙겨줬어. 쉬운 거 아닌데. 너 좀 대단해", nickname)
    elif total_logs >= 1:
        mari(s_em, f"기록이 쌓이면 우리 사이도 더 보일 거야. 계속 와줘", nickname)
    else:
        mari(s_em, f"아직 시작이야. 하나씩 해봐", nickname)

