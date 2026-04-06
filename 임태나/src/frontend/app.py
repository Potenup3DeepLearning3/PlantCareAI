import base64
import json
import random
from datetime import datetime, timedelta
from pathlib import Path

import plotly.graph_objects as go
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
.stTabs [aria-selected="true"]{color:#3B6D11!important;font-weight:600!important}
.stTabs [data-baseweb="tab-border"],.stTabs [data-baseweb="tab-highlight"]{display:none!important}

/* ── 입력창 ── */
.stTextInput input,.stTextArea textarea{
    background:white!important;border:1.5px solid #E5E0D5!important;
    border-radius:12px!important;color:#2C2C2A!important;font-size:13px!important}
.stTextInput input::placeholder,.stTextArea textarea::placeholder{color:#B4B2A9!important}
.stTextInput input:focus{border-color:#3B6D11!important;outline:none!important}

/* ── 파일 업로더 ── */
[data-testid="stFileUploader"]{
    background:white!important;border:1px dashed #E5E0D5!important;border-radius:16px!important}
[data-testid="stFileUploader"] *{color:#2C2C2A!important}
[data-testid="stFileUploader"] section,
[data-testid="stFileUploader"] section>div,
[data-testid="stFileUploaderDropzone"],
[data-testid="stFileUploaderDropzone"]>div{background:white!important}
[data-testid="stFileUploaderDropzone"] button{
    background:white!important;color:#2C2C2A!important;
    border:1.5px solid #C3C8BB!important;border-radius:8px!important}
[data-testid="stFileUploaderDropzone"] button:hover{background:#F0EDE6!important}

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
    width:100%!important}
div[data-testid="stHorizontalBlock"] .stButton>button:hover{
    background:#EAF3DE!important;border-color:#3B6D11!important}

/* ── 일반 버튼 (full-width green) ── */
.stButton>button{
    border-radius:20px!important;background:#3B6D11!important;
    border:none!important;color:white!important;
    padding:10px 20px!important;font-size:13px!important;font-weight:500!important}
.stButton>button:hover{background:#2B5A1D!important}

/* ── segmented_control ── */
div[data-testid="stElementContainer"]:has(div[data-testid="stButtonGroup"]),
div[class*="st-key-diag_mode"],div[class*="st-key-hist_sub"]{
    width:100%!important;display:block!important}
div[data-testid="stButtonGroup"]{
    display:flex!important;width:100%!important;min-width:0!important;
    background:#F0EDE6!important;border-radius:12px!important;
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
FASTAPI_URL = "http://localhost:8000"
PLANTS_FILE  = Path("data/plants.json")
CARE_LOG_FILE= Path("data/care_log.jsonl")

DISEASE_KOREAN = {
    "Bacterial_Spot":"세균성 반점","Early_Blight":"초기 마름병",
    "Greening":"그리닝병","Healthy":"건강",
    "Late_Blight":"후기 마름병","Leaf_Curl":"잎 말림",
    "Leaf_Mold":"잎 곰팡이","Leaf_Spot":"잎 반점",
    "Mosaic_Virus":"모자이크 바이러스","Powdery_Mildew":"흰가루병",
    "Rust":"녹병","Scab_Rot":"딱지병/부패",
}

# 케어 아이콘 정의: (이모지, 라벨, action_key)
CARE_ICONS = [
    ("💧","물줬음","water"),("☀️","자리옮김","move"),
    ("✂️","가지치기","prune"),("💊","약줬음","medicine"),
    ("🪴","분갈이","repot"),("🍃","잎닦음","clean"),
    ("😊","그냥봄","observe"),
]
ACTION_LABELS = {a: f"{e} {lb}" for e,lb,a in CARE_ICONS}

CARE_RESPONSES = {
    "water":["{0}한테 전해놨어! 물 받아서 좋아하겠다","기록했어. 꾸준히 챙겨주는 너 멋있다"],
    "medicine":["{0}한테 전해놨어! 빨리 나을 거야","약 줬구나. 네가 옆에 있어서 {0}이 든든할 거야"],
    "observe":["그냥 봐주는 것도 돌봄이야. {0}이 알고 있을 거야","가만히 지켜봐주는 것만으로도 충분할 때가 있어"],
    "move":["{0}한테 전해놨어! 새 자리 마음에 들어하겠다"],
    "prune":["정리해줬구나. {0}이 한결 가벼워졌을 거야"],
    "repot":["분갈이까지! 너 진짜 잘 챙긴다. {0}이 좋아할 거야"],
    "clean":["잎 닦아줬구나. {0}이 상쾌하대"],
}

# 셀프케어 넛지 (3번 중 1번 랜덤)
SELFCARE_NUDGES = {
    "water": ["근데 너는? 오늘 물 충분히 마셨어?", "너도 오늘 따뜻한 거 한 잔 마셔"],
    "move": ["너도 오늘 좀 환기시켜", "가끔은 너도 다른 자리에 앉아봐"],
    "prune": ["너도 오늘 뭐 하나 내려놓아도 괜찮아", "정리하고 나면 마음도 좀 가벼워지지"],
    "medicine": ["너도 요즘 좀 피곤하지 않아?", "아픈 건 빨리 챙기는 게 좋아. 너도"],
    "repot": ["가끔은 너도 환경을 바꿔볼 필요가 있어"],
    "clean": ["너도 오늘 좀 쉬어", "상쾌한 거 좋지? 너도 오늘 그런 시간 가져"],
    "observe": ["너도 오늘 잠깐 멍 때려봐", "가만히 있는 것도 쉬는 거야"],
}

def get_care_response(action, nickname):
    base_msg = random.choice(CARE_RESPONSES.get(action, ["{0}한테 전해놨어!"])).format(nickname)
    if random.random() < 0.33 and action in SELFCARE_NUDGES:
        nudge = random.choice(SELFCARE_NUDGES[action])
        return base_msg + "\n\n..." + nudge
    return base_msg

# 분즈 오프너 5가지 (가중치)
OPENERS = [
    ("{nickname}한테 물어봤는데, ", 0.50),
    ("이건 내 생각인데, ", 0.20),
    ("솔직히 말하면, ", 0.15),
    ("...{nickname}가 너한테 할 말이 있대. ", 0.10),
    ("", 0.05),
]

def get_opener(nickname):
    r = random.random()
    cumulative = 0.0
    for opener, prob in OPENERS:
        cumulative += prob
        if r < cumulative:
            return opener.format(nickname=nickname)
    return nickname + "한테 물어봤는데, "

MILESTONES = {
    1: "{0}이랑 첫 기록이다! 여기서부터 시작이야.\n내일 다시 오면 연속 돌봄 시작이야. 기대된다",
    5: "벌써 5번째. 슬슬 리듬이 생기고 있어",
    10: "10번 챙겼어. 뭔가를 10번이나 꾸준히 한 거야. 쉬운 거 아닌데",
    20: "20번이나 챙겼어. 너 이거 진심이구나",
    30: "30번이나 꾸준히 뭔가를 돌본 거야. 이거 쉬운 거 아니거든. 너 자신도 좀 대단하다고 생각해",
    50: "50번. 이쯤 되면 {0}를 돌보는 게 아니라, 너를 돌보는 시간이 된 거야",
    100: "100번. 할 말 잃었어. 그냥 대단하다",
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

# ═══════════════════════════════════════
# 데이터
# ═══════════════════════════════════════
def load_plants():
    if PLANTS_FILE.exists():
        return json.loads(PLANTS_FILE.read_text(encoding="utf-8"))
    return []

def save_plant(nickname):
    plants = load_plants()
    plants.append({"nickname":nickname,"species":"","registered":datetime.now().strftime("%Y-%m-%d")})
    PLANTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    PLANTS_FILE.write_text(json.dumps(plants, ensure_ascii=False, indent=2), encoding="utf-8")

def delete_plant(nickname):
    plants = [p for p in load_plants() if p["nickname"] != nickname]
    PLANTS_FILE.write_text(json.dumps(plants, ensure_ascii=False, indent=2), encoding="utf-8")

def update_species(nickname, species):
    plants = load_plants()
    for p in plants:
        if p["nickname"] == nickname:
            p["species"] = species
    PLANTS_FILE.write_text(json.dumps(plants, ensure_ascii=False, indent=2), encoding="utf-8")

def load_care_log(nickname=None):
    if not CARE_LOG_FILE.exists():
        return []
    logs = []
    for line in CARE_LOG_FILE.read_text(encoding="utf-8").strip().split("\n"):
        if line:
            entry = json.loads(line)
            if nickname is None or entry.get("plant") == nickname:
                logs.append(entry)
    return logs

def save_care_log(nickname, action):
    entry = {"date":datetime.now().strftime("%Y-%m-%d %H:%M"),"plant":nickname,"action":action}
    if "last_diagnosis" in st.session_state:
        diag = st.session_state.last_diagnosis
        entry["disease"] = diag.get("disease","")
        entry["lesion"]  = diag.get("lesion", 0)
    CARE_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CARE_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

def get_streak(care_logs):
    if not care_logs:
        return 0
    dates = sorted(set(log["date"][:10] for log in care_logs))
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    # 오늘 or 어제 기록이 없으면 streak 0
    if dates[-1] not in (today, yesterday):
        return 0
    streak = 0
    # 가장 최근 날짜부터 연속일 카운트
    check_date = datetime.strptime(dates[-1], "%Y-%m-%d")
    for d in reversed(dates):
        if d == check_date.strftime("%Y-%m-%d"):
            streak += 1
            check_date -= timedelta(days=1)
        else:
            break
    return streak

def get_recovery_emoji(r):
    if r > 0.2: return "🥀"
    if r > 0.1: return "🌱"
    if r > 0.05: return "🌿"
    if r > 0.02: return "🪴"
    return "🌳"

def analyze_user_pattern(care_logs):
    """접속 시간대 / 요일 / 공백 패턴 분석 → '마리가 본 너' 인사이트"""
    if not care_logs:
        return []
    hours = []
    weekdays = []
    for log in care_logs:
        date_str = log.get("date", "")
        if len(date_str) >= 13:
            try:
                hours.append(int(date_str[11:13]))
            except ValueError:
                pass
        if len(date_str) >= 10:
            try:
                weekdays.append(datetime.strptime(date_str[:10], "%Y-%m-%d").weekday())
            except ValueError:
                pass
    n = max(len(hours), 1)
    nw = max(len(weekdays), 1)
    evening_ratio = sum(1 for h in hours if h >= 18) / n
    morning_ratio = sum(1 for h in hours if h < 10) / n
    weekend_ratio = sum(1 for w in weekdays if w >= 5) / nw
    insights = []
    if evening_ratio > 0.5:
        insights.append("너 요즘 저녁에 자주 오더라. 하루 마무리를 같이 하는 거지?")
    if morning_ratio > 0.5:
        insights.append("아침에 챙겨주는 거 좋다. 하루를 식물로 시작하는 사람이야")
    if weekend_ratio < 0.15 and len(weekdays) >= 5:
        insights.append("주말에는 안 오는 편이야. 주말에도 잠깐 들러봐. 너한테도 좋을 거야")
    if not insights:
        insights.append("조금씩 패턴이 보이기 시작했어. 계속 기록해봐")
    return insights

# ═══════════════════════════════════════
# 컴포넌트
# ═══════════════════════════════════════
def boonz(mood, message):
    emojis = {"happy":"😊","worried":"😟","sad":"😢","loading":"👀","default":"🌱"}
    e = emojis.get(mood, "🌱")
    st.markdown(
        f'<div style="display:flex;align-items:flex-start;gap:10px;margin:8px 0 12px">'
        f'<div style="width:38px;height:38px;background:#EAF3DE;border-radius:50%;'
        f'display:flex;align-items:center;justify-content:center;font-size:19px;flex-shrink:0;">{e}</div>'
        f'<div style="background:white;border:0.5px solid #E5E0D5;border-radius:14px 14px 14px 4px;'
        f'padding:11px 15px;font-size:13.5px;color:#2C2C2A;flex:1;line-height:1.6;">'
        f'<div style="font-size:10px;color:#3B6D11;font-weight:600;margin-bottom:3px;">분즈</div>'
        f'{message}</div></div>',
        unsafe_allow_html=True,
    )

def care_grid(key_prefix, nickname, show_response=True):
    """아이콘 케어 버튼 그리드 (목업 스타일)"""
    action_taken = None
    for row in range(0, len(CARE_ICONS), 4):
        cols = st.columns(4)
        for ci, col in enumerate(cols):
            idx = row + ci
            if idx >= len(CARE_ICONS):
                break
            em, lb, action = CARE_ICONS[idx]
            with col:
                if st.button(f"{em}\n{lb}", key=f"{key_prefix}_{action}", use_container_width=True):
                    action_taken = action
    if action_taken:
        save_care_log(nickname, action_taken)
        msg = get_care_response(action_taken, nickname)
        if show_response:
            boonz("happy", msg)
        st.rerun()

def plant_card(nickname, days, status_emoji, status_text, status_desc, species_text, meter_count):
    meter = ""
    for i in range(4):
        color = "#3B6D11" if i < meter_count else "#E5E0D5"
        meter += f'<div style="width:18px;height:5px;border-radius:3px;background:{color};display:inline-block;margin:0 2px;"></div>'
    st.markdown(
        f'<div style="background:linear-gradient(135deg,#EAF3DE,#FFF9E6);border-radius:20px;'
        f'padding:20px;margin:12px 0;text-align:center;">'
        f'<div style="font-size:36px;margin:4px 0;">{status_emoji}</div>'
        f'<div style="font-size:18px;font-weight:700;color:#3B6D11;">{status_text}</div>'
        f'<div style="font-size:12px;color:#888780;margin:3px 0;">{nickname} · {species_text} · {days}일째</div>'
        f'<div style="margin:8px 0;">{meter}</div>'
        f'<div style="font-size:12px;color:#2C2C2A;font-style:italic;">"{status_desc}"</div>'
        f'</div>',
        unsafe_allow_html=True,
    )

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
    boonz("default", "별명 하나만 알려줘. 내가 기억할게")
    name = st.text_input("별명", placeholder="예: 초록이, 마리", label_visibility="collapsed")
    if name:
        save_plant(name)
        boonz("happy", f"{name}? 좋은 이름이다. 잘 부탁해")
        st.rerun()
    st.stop()

# ═══════════════════════════════════════
# 식물 선택 + 공통 계산
# ═══════════════════════════════════════
plant_names = [p["nickname"] for p in plants]
if len(plant_names) > 1:
    nickname = st.selectbox("내 식물", plant_names, label_visibility="collapsed")
else:
    nickname = plant_names[0]

current   = next((p for p in plants if p["nickname"] == nickname), {})
days      = (datetime.now() - datetime.strptime(current.get("registered","2026-01-01"), "%Y-%m-%d")).days
care_logs = load_care_log(nickname)
streak    = get_streak(care_logs)
total_logs= len(care_logs)

# 관계 단계
if days <= 7:
    s_em, s_text, s_desc = "🌱", "새로운 만남", "서로 알아가는 중이야. 자주 들러줘"
elif days <= 30:
    s_em, s_text, s_desc = "🌿", "알아가는 중", "돌봄이 습관이 되고 있어. 좋은 신호야"
elif days <= 90:
    s_em, s_text, s_desc = "🪴", "함께하는 사이", f"{nickname}가 너의 하루 일부가 됐네"
else:
    s_em, s_text, s_desc = "🌳", "오랜 친구", f"이쯤 되면 {nickname}가 너를 돌보는 거야"

meter_count = min(days // 23, 4)
species_text = current.get("species","") or "종을 알아보려면 진단 탭에서 사진을 찍어줘"

# 동적 타이틀 (시간별)
hour = datetime.now().hour
if   hour < 9:  greeting = "좋은 아침."
elif hour < 13: greeting = "오늘은"
elif hour < 18: greeting = "잠깐 들러볼까."
else:           greeting = "오늘 하루 수고했어."

# 돌봄 공백
if care_logs:
    last_date = datetime.strptime(care_logs[-1]["date"][:10], "%Y-%m-%d")
    gap = (datetime.now() - last_date).days
else:
    gap = -1

# 병변 변화
diagnosis_logs = [l for l in care_logs if l.get("lesion")]
if len(diagnosis_logs) >= 2:
    lesion_change = f'{(diagnosis_logs[-1]["lesion"]-diagnosis_logs[0]["lesion"])*100:+.0f}%'
else:
    lesion_change = "—"

# ═══════════════════════════════════════
# 탭: 홈 / 진단 / 이력
# ═══════════════════════════════════════
tab_home, tab_diag, tab_hist = st.tabs(["🏠 홈", "📷 진단", "📊 이력"])

# ══════════════════════════════
# 탭 홈
# ══════════════════════════════
with tab_home:
    # 타이틀 (시간별 동적 + 관계 단계별)
    if days >= 8:
        main_title = f"{nickname}와 함께한 지\n벌써 {days}일째야."
    elif hour < 9:
        main_title = f"좋은 아침.\n{nickname} 오늘도 잘 있을까?"
    elif hour < 13:
        main_title = f"오늘은 {nickname}한테\n뭐 해줄 거야?"
    elif hour < 18:
        main_title = f"{nickname}한테\n잠깐 들러볼까?"
    else:
        main_title = f"오늘 하루 수고했어.\n{nickname}도 잘 있었을까?"
    main_title_html = main_title.replace("\n", "<br>")
    subtitle_html = ""
    if days >= 8:
        subtitle_html = f'<div style="font-size:13px;color:#888780;margin-top:4px;margin-bottom:4px;">오늘도 {nickname} 잘 있는지 보러 왔네</div>'
    st.markdown(
        f'<div style="font-size:14px;color:#888780;margin:0 0 2px;">{greeting}</div>'
        f'<div style="font-size:26px;font-weight:700;color:#2C2C2A;line-height:1.35;margin-bottom:4px;">'
        f'{main_title_html}</div>'
        f'{subtitle_html}',
        unsafe_allow_html=True,
    )

    # 분즈 메시지
    if gap == 0:
        boonz("happy", f"오늘도 {nickname} 챙겨주네. 이런 시간이 너한테도 좋은 거야")
    elif gap == 1:
        last_act = ACTION_LABELS.get(care_logs[-1].get("action",""), "")
        boonz("default", f"어제 {last_act} 해줬지? 꾸준한 거 좋다")
    elif 2 <= gap <= 5:
        boonz("default", f"{gap}일 만이네. 바쁜 거 알아. 근데 이런 시간이 너한테 필요한 거 아닐까?")
    elif gap > 5:
        boonz("worried", f"일주일이네. {nickname}도 보고 싶어하지만, 솔직히 너도 좀 쉬어야 할 거 같아서")
    elif gap == -1 and days <= 1:
        boonz("default", f"{nickname} 종류가 뭔지 아직 모르지? 진단 탭에서 사진 한 장 찍어봐.\n첫 날이니까 오늘은 😊 그냥봄 해줘. 그것만으로도 시작이야")
    else:
        boonz("default", "나와 식물 사이, 분즈가 통역해줄게")

    # 식물 카드
    plant_card(nickname, days, s_em, s_text, s_desc, species_text, meter_count)

    # 스트릭 + 통계 (30일 이상)
    if streak >= 1:
        st.markdown(
            f'<div style="margin:4px 0;">'
            f'<span style="display:inline-block;background:#3B6D11;color:white;border-radius:20px;'
            f'padding:5px 14px;font-size:11px;">🔥 {streak}일 연속 돌봄</span>'
            f'<span style="font-size:11px;color:#888780;margin-left:8px;">기록 {total_logs}개</span>'
            f'</div>',
            unsafe_allow_html=True,
        )
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
            f'<div style="font-size:22px;font-weight:700;color:#3B6D11;">{lesion_change}</div>'
            f'<div style="font-size:9px;color:#888780;margin-top:2px;">병변 변화</div></div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # Day 1 넛지 카드 (첫 기록 없을 때)
    if total_logs == 0 and days <= 1:
        st.markdown(
            f'<div style="background:#FFF9E6;border-radius:14px;padding:12px 16px;margin:8px 0;">'
            f'<div style="font-size:11px;color:#3B6D11;font-weight:600;margin-bottom:3px;">💡 첫 날이니까</div>'
            f'<div style="font-size:12px;color:#2C2C2A;line-height:1.6;">'
            f'오늘은 😊 그냥봄 해줘. 그것만으로도 시작이야.<br>'
            f'내일 다시 오면 연속 돌봄 시작이야. 기대된다 🌱</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

    # 이정표
    if total_logs in MILESTONES:
        st.markdown(
            f'<div style="background:#FFF9E6;border-radius:14px;padding:10px 16px;margin:8px 0;'
            f'text-align:center;font-size:12px;color:#2C2C2A;">🎉 {MILESTONES[total_logs].format(nickname)}</div>',
            unsafe_allow_html=True,
        )

    divider()

    # 원터치 케어
    sec_title(f"오늘 {nickname}한테 뭐 해줬어?")
    care_grid("h", nickname)

    divider()

    # 챗봇
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []

    if not st.session_state.chat_history:
        boonz("default", "뭐든 물어봐. 내가 알아볼게")

    for msg in st.session_state.chat_history[-8:]:
        if msg["role"] == "user":
            st.markdown(
                f'<div style="background:#EAF3DE;border-radius:12px 12px 4px 12px;'
                f'padding:8px 12px;margin:6px 0 6px 60px;text-align:right;font-size:13px;color:#2C2C2A;">'
                f'{msg["content"]}</div>',
                unsafe_allow_html=True,
            )
        else:
            boonz("happy", msg["content"])

    question = st.text_input(
        "질문", placeholder="예: 잎이 노랗게 변하는데 왜 그래?",
        key="q_home", label_visibility="collapsed",
    )
    if question:
        st.session_state.chat_history.append({"role":"user","content":question})
        diag_ctx = ""
        if "last_diagnosis" in st.session_state:
            d = st.session_state.last_diagnosis
            dk = DISEASE_KOREAN.get(d.get("disease",""), d.get("disease",""))
            diag_ctx = f"현재 {nickname}: {dk}, 병변 {d.get('lesion',0)*100:.0f}%"
        try:
            resp = requests.post(
                f"{FASTAPI_URL}/consult/text",
                data={"question":question,"nickname":nickname,"diagnosis_context":diag_ctx},
                timeout=30,
            )
            answer = resp.json().get("boonz",{}).get("message","") or resp.json().get("answer",{}).get("text","")
        except Exception:
            answer = "앗 나 잠깐 버그남. 근데 괜찮아, 다시 해볼게"
        st.session_state.chat_history.append({"role":"boonz","content":answer})
        st.rerun()

    # 식물 관리
    with st.expander("🌱 식물 관리"):
        new_name = st.text_input("새 식물 별명", key="new_p", label_visibility="collapsed", placeholder="새 식물 별명")
        if st.button("추가", key="add_p") and new_name:
            save_plant(new_name); st.rerun()
        if st.button(f"🗑️ {nickname} 삭제", key="del_p"):
            delete_plant(nickname); st.rerun()

# ══════════════════════════════
# 탭 진단
# ══════════════════════════════
with tab_diag:
    # SAM 모드 선택
    diag_mode = st.segmented_control(
        "모드", ["원본", "SAM 분석"], default="원본",
        label_visibility="collapsed", key="diag_mode",
    )
    st.markdown('<div style="margin-top:8px;"></div>', unsafe_allow_html=True)

    uploaded = st.file_uploader(
        "잎 사진을 올려줘", type=["jpg","jpeg","png"],
        key="diag_upload", label_visibility="collapsed",
    )

    if not uploaded:
        boonz("default", f"{nickname} 사진 줘. 내가 봐줌")

    if uploaded:
        boonz("loading", "잠깐, 얘 얘기 좀 들어보고 있어...")
        try:
            files = {"file":(uploaded.name, uploaded.getvalue(), uploaded.type)}
            resp  = requests.post(f"{FASTAPI_URL}/diagnose", files=files, data={"nickname":nickname}, timeout=60)
            result= resp.json()

            # 이미지 표시
            col1, col2 = st.columns(2)
            with col1:
                st.image(uploaded, caption="원본", use_container_width=True)
            with col2:
                overlay = result.get("overlay_image") or result.get("lesion",{}).get("overlay_base64","")
                if overlay and (diag_mode == "SAM 분석"):
                    st.image(base64.b64decode(overlay), caption="SAM 분석", use_container_width=True)
                else:
                    st.markdown(
                        '<div style="background:#F7F5F0;border-radius:14px;height:140px;'
                        'display:flex;align-items:center;justify-content:center;'
                        'font-size:12px;color:#B4B2A9;">SAM 분석 탭을 선택하면 보여줄게</div>',
                        unsafe_allow_html=True,
                    )

            # 결과 카드
            disease    = result.get("disease",{})
            lesion     = result.get("lesion",{})
            species_i  = result.get("species",{})
            ratio      = lesion.get("ratio",0) * 100
            disease_kr = DISEASE_KOREAN.get(disease.get("name",""), disease.get("korean", disease.get("name","")))

            if ratio <= 5:   sev_text, sev_color = "건강해 보여", "#97C459"
            elif ratio <= 10: sev_text, sev_color = "아직 초기야. 지금 잡으면 돼", "#97C459"
            elif ratio <= 25: sev_text, sev_color = "중기야. 관심이 필요해", "#EF9F27"
            else:             sev_text, sev_color = "후기야. 적극적인 케어 필요", "#E24B4A"

            st.markdown(
                f'<div style="background:white;border-radius:20px;padding:18px;'
                f'box-shadow:0 2px 8px rgba(0,0,0,0.04);margin:10px 0;">'
                f'<div style="font-size:17px;font-weight:700;color:#2C2C2A;">{nickname}가 좀 아프대</div>'
                f'<div style="font-size:13px;color:#888780;margin:4px 0;">'
                f'{disease_kr} · 신뢰도 {disease.get("confidence",0):.0%}</div>'
                f'<div style="background:#E5E0D5;border-radius:6px;height:8px;margin:8px 0;overflow:hidden;">'
                f'<div style="width:{min(ratio,100)}%;height:100%;background:{sev_color};border-radius:6px;"></div></div>'
                f'<div style="font-size:12px;color:#3B6D11;">병변 {ratio:.1f}% — {sev_text}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

            # 분즈
            b = result.get("boonz",{})
            boonz(b.get("mood","worried"), b.get("message", f"{nickname}한테 물어봤는데, 좀 힘들다고 해. 같이 돌보자"))

            # 케어 가이드 버튼 + 텍스트
            care = result.get("care_guide",{})
            if care.get("text"):
                if "show_guide" not in st.session_state:
                    st.session_state.show_guide = False
                if st.button("💬 케어 가이드 받기", key="guide_btn", use_container_width=True):
                    st.session_state.show_guide = True
                if st.session_state.show_guide:
                    st.markdown(
                        f'<div style="background:white;border-radius:16px;padding:16px;'
                        f'border-left:3px solid #3B6D11;margin:8px 0;font-size:13px;color:#2C2C2A;line-height:1.7;">'
                        f'{care["text"]}'
                        f'<div style="font-size:11px;color:#888780;margin-top:8px;font-style:italic;">'
                        f'네가 이렇게 신경 써주는 거, {nickname}한테 큰 힘이 될 거야</div></div>',
                        unsafe_allow_html=True,
                    )
            if care.get("audio_url"):
                st.audio(care["audio_url"])

            # 진단 저장
            st.session_state.last_diagnosis = {"disease":disease.get("name",""), "lesion":lesion.get("ratio",0)}
            if species_i.get("name"):
                update_species(nickname, species_i["name"])

            divider()
            sec_title(f"{nickname}한테 뭐 해줄 거야?")
            care_grid("d", nickname)

            # 진단 관련 질문
            divider()
            st.markdown(
                f'<div style="font-size:16px;font-weight:700;color:#2C2C2A;margin:8px 0 10px;">진단 관련 질문</div>',
                unsafe_allow_html=True,
            )
            # 현재 진단 컨텍스트 칩
            st.markdown(
                f'<div style="display:inline-block;background:#F0EDE6;border-radius:20px;'
                f'padding:4px 12px;font-size:11px;color:#888780;margin-bottom:8px;">'
                f'현재 진단: {nickname} · {disease_kr} · 병변 {ratio:.1f}%</div>',
                unsafe_allow_html=True,
            )

            if "diag_chat" not in st.session_state:
                st.session_state.diag_chat = []

            for msg in st.session_state.diag_chat[-6:]:
                if msg["role"] == "user":
                    st.markdown(
                        f'<div style="background:#EAF3DE;border-radius:12px 12px 4px 12px;'
                        f'padding:8px 12px;margin:6px 0 6px 60px;text-align:right;font-size:13px;color:#2C2C2A;">'
                        f'{msg["content"]}</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    boonz("happy", msg["content"])

            diag_q = st.text_input(
                "질문", placeholder=f"예: 이 병이 다른 잎으로 번져?",
                key="q_diag", label_visibility="collapsed",
            )
            if diag_q:
                st.session_state.diag_chat.append({"role":"user","content":diag_q})
                diag_ctx = f"현재 {nickname}: {disease_kr}, 병변 {ratio:.1f}%"
                try:
                    resp2 = requests.post(
                        f"{FASTAPI_URL}/consult/text",
                        data={"question":diag_q,"nickname":nickname,"diagnosis_context":diag_ctx},
                        timeout=30,
                    )
                    ans = resp2.json().get("boonz",{}).get("message","") or resp2.json().get("answer",{}).get("text","")
                except Exception:
                    ans = "앗 나 잠깐 버그남. 근데 괜찮아, 다시 해볼게"
                st.session_state.diag_chat.append({"role":"boonz","content":ans})
                st.rerun()

        except Exception as e:
            boonz("worried", "앗 나 잠깐 버그남. 근데 괜찮아, 다시 해볼게")
            st.caption(str(e))

# ══════════════════════════════
# 탭 이력
# ══════════════════════════════
with tab_hist:
    sub = st.segmented_control(
        "이력 서브탭", ["케어일기","리포트","타임라인"],
        default="케어일기", label_visibility="collapsed", key="hist_sub",
    )

    # 행동 빈도 (탭 공통)
    action_counts: dict = {}
    for log in care_logs:
        a = log.get("action", "")
        action_counts[a] = action_counts.get(a, 0) + 1

    # ── 이야기 ──
    if sub is None or sub == "케어일기":
        sec_title(f"오늘 {nickname}한테 뭐 해줬어?")
        care_grid("hist", nickname)

        # 행동 빈도 프로그레스
        for lbl, key in [("💧 물","water"),("☀️ 자리","move"),("✂️ 가지","prune"),("😊 관심","observe")]:
            count = action_counts.get(key, 0)
            pct   = min(count/10, 1.0) * 100
            st.markdown(
                f'<div style="display:flex;align-items:center;gap:6px;margin:4px 0;font-size:11px;color:#888780;">'
                f'<span style="width:40px;">{lbl}</span>'
                f'<div style="flex:1;background:#E5E0D5;border-radius:4px;height:5px;overflow:hidden;">'
                f'<div style="width:{pct}%;height:100%;background:#3B6D11;border-radius:4px;"></div></div>'
                f'<span>{count}번</span></div>',
                unsafe_allow_html=True,
            )

        divider()

        # 회복 여정
        if len(diagnosis_logs) >= 2:
            st.markdown(
                f'<div style="font-size:16px;font-weight:700;color:#2C2C2A;margin:8px 0 10px;">{nickname}와의 이야기</div>',
                unsafe_allow_html=True,
            )
            jhtml = '<div style="display:flex;align-items:flex-end;justify-content:center;gap:8px;margin:14px 0;">'
            for log in diagnosis_logs:
                em  = get_recovery_emoji(log["lesion"])
                pct = f'{log["lesion"]*100:.0f}%'
                dt  = fmt_date(log["date"])
                jhtml += (
                    f'<div style="text-align:center;font-size:10px;color:#888780;">'
                    f'<div style="font-size:22px;">{em}</div>{dt}<br>{pct}</div>'
                )
                if log != diagnosis_logs[-1]:
                    jhtml += '<div style="font-size:12px;color:#E5E0D5;align-self:center;">→</div>'
            jhtml += '</div>'
            st.markdown(jhtml, unsafe_allow_html=True)

            if diagnosis_logs[-1]["lesion"] < diagnosis_logs[0]["lesion"]:
                boonz("happy", f"봐봐, {nickname} 너랑 있으면서 점점 좋아지고 있어. 너가 잘 돌봐준 거야")
            else:
                boonz("worried", f"{nickname}가 요즘 좀 힘들어하고 있어. 더 자주 들여다봐줄래?")

        divider()

        # 돌봄 일기
        st.markdown('<div style="font-size:16px;font-weight:700;color:#2C2C2A;margin:8px 0 10px;">돌봄 일기</div>', unsafe_allow_html=True)

        if care_logs:
            show_all = st.session_state.get("show_all_hist", False)
            display  = care_logs if show_all else care_logs[-5:]
            for log in reversed(display):
                label = ACTION_LABELS.get(log["action"], log["action"])
                lesion_txt = ""
                comment    = ""
                if log.get("lesion"):
                    lesion_txt = f' — 병변 {log["lesion"]*100:.0f}%'
                    if log["lesion"] <= 0.05:
                        comment = f'· {nickname}가 많이 나아졌대'
                    elif log["lesion"] <= 0.1:
                        comment = '· 좋아지고 있어!'
                    else:
                        comment = f'· 힘내자 {nickname}'
                st.markdown(
                    f'<div style="background:white;padding:10px 14px;border-radius:12px;'
                    f'margin:4px 0;font-size:12px;color:#2C2C2A;">'
                    f'{fmt_date_kr(log["date"])} — {label}{lesion_txt}'
                    f'<span style="color:#3B6D11;font-size:11px;"> {comment}</span></div>',
                    unsafe_allow_html=True,
                )
            if not show_all and len(care_logs) > 5:
                if st.button("이전 기록 더보기 ↓", key="more_hist", use_container_width=False):
                    st.session_state.show_all_hist = True
                    st.rerun()
        else:
            boonz("default", f"아직 {nickname}이랑 기록이 없네. 홈 탭에서 버튼 눌러봐. 하나만 눌러도 시작이야")

    # ── 패턴 ──
    elif sub == "리포트":
        st.markdown(
            f'<div style="font-size:16px;font-weight:700;color:#2C2C2A;margin:8px 0 10px;">{nickname}가 본 너의 돌봄</div>',
            unsafe_allow_html=True,
        )

        lesion_dec = ""
        if len(diagnosis_logs) >= 2:
            chg = (diagnosis_logs[0]["lesion"]-diagnosis_logs[-1]["lesion"])*100
            lesion_dec = f"{chg:.0f}%"

        # 돌봄 리포트 카드
        st.markdown(
            f'<div style="background:linear-gradient(135deg,#EAF3DE,#FFF9E6);border-radius:20px;'
            f'padding:20px;margin:12px 0;text-align:center;">'
            f'<div style="font-size:14px;font-weight:600;color:#3B6D11;margin-bottom:12px;">돌봄 리포트</div>'
            f'<div style="display:flex;justify-content:space-around;">'
            f'<div><div style="font-size:24px;font-weight:700;color:#2C2C2A;">{total_logs}</div>'
            f'<div style="font-size:10px;color:#888780;">총 기록</div></div>'
            f'<div><div style="font-size:24px;font-weight:700;color:#2C2C2A;">{streak}</div>'
            f'<div style="font-size:10px;color:#888780;">연속 돌봄</div></div>'
            f'<div><div style="font-size:24px;font-weight:700;color:#3B6D11;">{f"-{lesion_dec}" if lesion_dec else "—"}</div>'
            f'<div style="font-size:10px;color:#888780;">병변 감소</div></div>'
            f'</div></div>',
            unsafe_allow_html=True,
        )

        # 돌봄 유형 뱃지
        if total_logs >= 3:
            observe_cnt = action_counts.get("observe",0)
            water_cnt   = action_counts.get("water",0)
            diag_cnt    = len(diagnosis_logs)
            if observe_cnt >= total_logs * 0.4:
                care_type, care_icon, care_desc = "꾸준한 관찰형", "🧑‍🌾", f"매일 들여다봐주는 거, {nickname}한테 제일 좋은 돌봄이야"
            elif water_cnt >= total_logs * 0.5:
                care_type, care_icon, care_desc = "섬세한 케어형", "💧", f"물 주기 하나도 허투루 안 하는 타입이야"
            elif diag_cnt >= 2:
                care_type, care_icon, care_desc = "데이터 수집형", "📸", f"기록이 쌓이면 {nickname}가 어떻게 달라지는지 보일 거야"
            else:
                care_type, care_icon, care_desc = "동행형", "😊", f"{nickname}랑 같이 있어주는 것만으로도 충분해"
            st.markdown(
                f'<div style="background:white;border-radius:16px;padding:16px;margin:8px 0 4px;'
                f'box-shadow:0 2px 6px rgba(0,0,0,0.04);text-align:center;">'
                f'<div style="font-size:24px;margin-bottom:6px;">{care_icon}</div>'
                f'<div style="font-size:13px;font-weight:700;color:#2C2C2A;">{care_type}</div>'
                f'<div style="font-size:11px;color:#888780;margin-top:4px;line-height:1.5;">{care_desc}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

        # "잘하고 있는 것" + "한 가지 팁"
        if total_logs >= 3:
            good_points = []
            tips = []
            w  = action_counts.get("water",0)
            o  = action_counts.get("observe",0)
            m  = action_counts.get("medicine",0)
            cl = action_counts.get("clean",0)
            if w >= 3:
                good_points.append("물 주기 간격이 규칙적이야")
            if len(diagnosis_logs) >= 2:
                good_points.append("아프면 바로 딱 챙겨줘. 빠른 대응 달아 좋아")
            if o >= 3:
                good_points.append("꾸준히 들여다봐주는 거 대단해")
            if not good_points:
                good_points.append("여기까지 온 것 자체가 대단해")
            if cl < 2:
                tips.append("잎 닦기를 좀 더 해줘. 먼지 쌓이면 숨 쉬기 힘거든")
            if m == 0 and len(diagnosis_logs) >= 1:
                tips.append("약 한 번쯤 써보는 것도 괜찮아. 버티는 것만이 능사는 아니야")
            if not tips:
                tips.append("지금 이 페이스면 충분해. 무리하지 마")
            good_html = "".join(f'<div style="font-size:12px;color:#2C2C2A;line-height:1.7;margin:2px 0;">• {g}</div>' for g in good_points)
            tip_html  = "".join(f'<div style="font-size:12px;color:#2C2C2A;line-height:1.7;margin:2px 0;">• {t}</div>' for t in tips)
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

        # "마리가 본 너" 섹션 (완전한 단일 HTML 블록)
        user_insights = analyze_user_pattern(care_logs)
        if user_insights:
            bullets = "".join(
                f'<div style="font-size:12px;color:#3B6D11;line-height:1.7;margin:3px 0;">• {ins}</div>'
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

        # LLM 패턴 분석
        if st.button("🔍 패턴 분석 받기", key="pattern_btn", use_container_width=True):
            if len(care_logs) >= 5:
                try:
                    resp = requests.get(f"{FASTAPI_URL}/pattern/{nickname}", timeout=60)
                    result = resp.json()
                    b = result.get("boonz",{})
                    msg_text = b.get("message","")
                    if msg_text:
                        boonz(b.get("mood","happy"), msg_text)
                except Exception:
                    boonz("worried", "앗 나 잠깐 버그남. 근데 괜찮아, 다시 해볼게")
            else:
                boonz("default", f"기록이 {total_logs}개야. 5개 이상 쌓이면 패턴이 보일 거야")

        # 셀프케어 마무리 메시지
        boonz("happy", get_opener(nickname) + "너 꽤 잘 돌보는 듯. 이런 시간이 너한테도 의미 있을 거야")

    # ── 여정 ──
    elif sub == "타임라인":
        st.markdown(
            f'<div style="font-size:16px;font-weight:700;color:#2C2C2A;margin:8px 0 14px;">{nickname}와의 여정</div>',
            unsafe_allow_html=True,
        )

        # 수직 타임라인
        stages = []
        reg_date = current.get("registered","")
        if reg_date:
            stages.append(("🌱","새로운 만남", fmt_date_kr(reg_date), f'"{nickname}야? 잘 부탁해"', "#C0DD97"))
        if diagnosis_logs:
            first_d = diagnosis_logs[0]
            stages.append(("😟","아픈 날", fmt_date_kr(first_d["date"]),
                           f'첫 진단. {DISEASE_KOREAN.get(first_d.get("disease",""),"병변")} 발견 ({first_d["lesion"]*100:.0f}%). 같이 이겨내자', "#EF9F27"))
        if len(diagnosis_logs) >= 3:
            pcts = " → ".join([f'{l["lesion"]*100:.0f}%' for l in diagnosis_logs[:4]])
            stages.append(("💊","함께 이겨내기",
                           f'{fmt_date_kr(diagnosis_logs[0]["date"])} ~ {fmt_date_kr(diagnosis_logs[-1]["date"])}',
                           f'{pcts}', "#3B6D11"))
        if days >= 30:
            stages.append(("🌿","알아가는 중", f"{days}일째",
                           f'"돌봄이 습관이 되고 있어. 이 시간이 너한테도 의미 있을 거야"', "#3B6D11"))
        if diagnosis_logs and diagnosis_logs[-1]["lesion"] <= 0.05:
            stages.append(("😊","거의 회복!", fmt_date_kr(diagnosis_logs[-1]["date"]),
                           f'"봐봐, 너가 잘 돌봐준 거야"', "#97C459"))

        for i, (em, title, date_s, desc, dot_color) in enumerate(stages):
            st.markdown(
                f'<div style="display:flex;gap:12px;align-items:flex-start;margin:6px 0;">'
                f'<div style="display:flex;flex-direction:column;align-items:center;width:14px;">'
                f'<div style="width:14px;height:14px;border-radius:50%;background:{dot_color};'
                f'border:2px solid white;box-shadow:0 1px 4px rgba(0,0,0,0.1);flex-shrink:0;"></div>'
                + (f'<div style="width:2px;background:#3B6D11;flex:1;min-height:24px;margin:2px 0;"></div>' if i < len(stages)-1 else '')
                + f'</div><div style="flex:1;padding-bottom:8px;">'
                f'<div style="font-size:14px;font-weight:600;color:#2C2C2A;">{em} {title}</div>'
                f'<div style="font-size:10px;color:#B4B2A9;margin-top:1px;">{date_s}</div>'
                f'<div style="font-size:11px;color:#3B6D11;margin-top:2px;line-height:1.4;">{desc}</div>'
                f'</div></div>',
                unsafe_allow_html=True,
            )

        st.markdown(
            '<div style="background:linear-gradient(135deg,#EAF3DE,#FFF9E6);border-radius:16px;'
            'padding:18px 20px;margin:16px 0;text-align:center;">'
            '<div style="font-size:15px;font-weight:600;color:#3B6D11;line-height:1.5;">'
            '돌봄이 관계가 되고,<br>관계가 성장이 됩니다 🌱</div>'
            '<div style="font-size:12px;color:#888780;margin-top:6px;line-height:1.5;">'
            '식물을 돌보는 시간이<br>나를 돌보는 시간이 됩니다</div></div>',
            unsafe_allow_html=True,
        )

        # Day 1 vs Day 30 비교 카드
        if days >= 14:
            reg_display = fmt_date_kr(current.get("registered","")) if current.get("registered") else "—"
            first_lesion_txt = f'{diagnosis_logs[0]["lesion"]*100:.0f}%' if diagnosis_logs else "—"
            last_lesion_txt  = f'{diagnosis_logs[-1]["lesion"]*100:.0f}%' if len(diagnosis_logs) >= 2 else "—"
            lesion_range = f"병변 {first_lesion_txt} → {last_lesion_txt}" if len(diagnosis_logs) >= 2 else ""
            st.markdown(
                f'<div style="background:white;border-radius:16px;padding:18px;margin:12px 0;'
                f'box-shadow:0 2px 6px rgba(0,0,0,0.04);">'
                f'<div style="font-size:13px;font-weight:700;color:#2C2C2A;margin-bottom:12px;text-align:center;">같은 앱, 다른 관계</div>'
                f'<div style="display:flex;gap:10px;">'
                f'<div style="flex:1;background:#F7F5F0;border-radius:12px;padding:12px;">'
                f'<div style="font-size:10px;color:#888780;margin-bottom:4px;">Day 1 · 초록이</div>'
                f'<div style="font-size:12px;font-weight:600;color:#2C2C2A;">🌱 새로운 만남</div>'
                f'<div style="font-size:10px;color:#B4B2A9;margin-top:4px;">기록 0개 · 진단 0번</div>'
                f'</div>'
                f'<div style="flex:1;background:#EAF3DE;border-radius:12px;padding:12px;">'
                f'<div style="font-size:10px;color:#3B6D11;margin-bottom:4px;">Day {days} · {nickname}</div>'
                f'<div style="font-size:12px;font-weight:600;color:#2C2C2A;">🌿 알아가는 중</div>'
                f'<div style="font-size:10px;color:#3B6D11;margin-top:4px;">기록 {total_logs}개 · {lesion_range}</div>'
                f'</div></div>'
                f'</div>',
                unsafe_allow_html=True,
            )
            boonz("happy", f"솔직히 너 꽤 잘 키우는 듯. {nickname}도 그럴 게 생각돼")

        # 분즈 정체성 카드
        st.markdown(
            '<div style="background:#F7F5F0;border-radius:16px;padding:18px 20px;margin:12px 0;text-align:center;">'
            '<div style="font-size:12px;font-weight:600;color:#2C2C2A;margin-bottom:6px;">분즈는 진단 AI가 아닙니다</div>'
            '<div style="font-size:11px;color:#888780;line-height:1.7;">'
            '나와 식물 사이에서<br>관계를 돌봐주는 친구입니다<br><br>'
            '식물을 돌보는 시간이<br>나를 돌보는 시간이 됩니다</div>'
            '</div>',
            unsafe_allow_html=True,
        )

