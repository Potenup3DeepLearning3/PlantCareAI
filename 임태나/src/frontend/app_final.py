import base64
import random
from collections import Counter
import streamlit as st
import requests
import json
from pathlib import Path
from datetime import datetime, date, timedelta
import plotly.graph_objects as go

# ========================================
# Page Config
# ========================================
st.set_page_config(
    page_title="분즈",
    layout="centered",
    page_icon="🌱",
    initial_sidebar_state="collapsed",
)

# ========================================
# Material 3 Design System — 폰트 로드 (link 방식, @import보다 안정적)
# ========================================
st.markdown(
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;600;700&display=swap" rel="stylesheet">',
    unsafe_allow_html=True,
)

# ========================================
# Material 3 Design System CSS
# m3.material.io 공식 타입 스케일 적용
# ========================================
st.markdown("""
<style>
/* ── Design Tokens ── */
:root {
  /* Color */
  --p:   #386A1F;   /* primary */
  --pd:  #245213;   /* primary dark (hover) */
  --pc:  #C3E8A8;   /* primary container */
  --opc: #072100;   /* on primary container */
  --s1:  #F8F8F5;   /* surface */
  --s2:  #F0F4EC;   /* surface variant */
  --s3:  #E4EBDd;   /* surface variant 2 */
  --os:  #1A1C18;   /* on-surface */
  --osm: #43483F;   /* on-surface medium */
  --osl: #73796E;   /* on-surface low */
  --ov:  #C3C8BB;   /* outline variant */
  /* Elevation */
  --el1: 0 1px 2px rgba(0,0,0,0.20), 0 1px 3px 1px rgba(0,0,0,0.10);
  --el2: 0 1px 2px rgba(0,0,0,0.20), 0 2px 6px 2px rgba(0,0,0,0.10);
  --el3: 0 4px 8px 3px rgba(0,0,0,0.10), 0 1px 3px rgba(0,0,0,0.15);
  /* Shape */
  --r-xs: 4px; --r-sm: 8px; --r-md: 12px;
  --r-lg: 16px; --r-xl: 28px; --r-full: 100px;
  /* M3 Type Scale (m3.material.io 공식값) */
  /* Display */
  --ts-disp-lg:  57px; --tw-disp-lg:  400; --tl-disp-lg:  64px;
  --ts-disp-md:  45px; --tw-disp-md:  400; --tl-disp-md:  52px;
  --ts-disp-sm:  36px; --tw-disp-sm:  400; --tl-disp-sm:  44px;
  /* Headline */
  --ts-hl-lg:    32px; --tw-hl-lg:    400; --tl-hl-lg:    40px; --tk-hl-lg:    0px;
  --ts-hl-md:    28px; --tw-hl-md:    400; --tl-hl-md:    36px; --tk-hl-md:    0px;
  --ts-hl-sm:    24px; --tw-hl-sm:    400; --tl-hl-sm:    32px; --tk-hl-sm:    0px;
  /* Title */
  --ts-tt-lg:    22px; --tw-tt-lg:    400; --tl-tt-lg:    28px; --tk-tt-lg:    0px;
  --ts-tt-md:    16px; --tw-tt-md:    500; --tl-tt-md:    24px; --tk-tt-md:    0.15px;
  --ts-tt-sm:    14px; --tw-tt-sm:    500; --tl-tt-sm:    20px; --tk-tt-sm:    0.1px;
  /* Label */
  --ts-lb-lg:    14px; --tw-lb-lg:    500; --tl-lb-lg:    20px; --tk-lb-lg:    0.1px;
  --ts-lb-md:    12px; --tw-lb-md:    500; --tl-lb-md:    16px; --tk-lb-md:    0.5px;
  --ts-lb-sm:    11px; --tw-lb-sm:    500; --tl-lb-sm:    16px; --tk-lb-sm:    0.5px;
  /* Body */
  --ts-bd-lg:    16px; --tw-bd-lg:    400; --tl-bd-lg:    24px; --tk-bd-lg:    0.5px;
  --ts-bd-md:    14px; --tw-bd-md:    400; --tl-bd-md:    20px; --tk-bd-md:    0.25px;
  --ts-bd-sm:    12px; --tw-bd-sm:    400; --tl-bd-sm:    16px; --tk-bd-sm:    0.4px;
}

/* ── Global Reset ── */
* { font-family: 'Noto Sans KR', -apple-system, BlinkMacSystemFont, sans-serif !important; }
[data-testid="stAppViewContainer"] { background: var(--s1) !important; }
[data-testid="stHeader"]           { background: var(--s1) !important; border-bottom: 1px solid var(--ov); }
[data-testid="stSidebar"]          { display: none !important; }
.block-container { padding: 16px 16px 96px !important; max-width: 480px !important; margin: 0 auto !important; }
::-webkit-scrollbar { width: 0; }

/* ── M3 Typography — Streamlit 마크다운 헤더 ── */
/* h1 → Headline Large */
h1 {
  font-size: var(--ts-hl-lg) !important;
  font-weight: 700 !important;          /* brand는 bold 처리 */
  line-height: var(--tl-hl-lg) !important;
  letter-spacing: var(--tk-hl-lg) !important;
  color: var(--os) !important;
  margin-bottom: 4px !important;
}
/* h2 → Headline Medium */
h2 {
  font-size: var(--ts-hl-md) !important;
  font-weight: 700 !important;
  line-height: var(--tl-hl-md) !important;
  letter-spacing: var(--tk-hl-md) !important;
  color: var(--os) !important;
  margin-bottom: 4px !important;
}
/* h3 → Title Large */
h3 {
  font-size: var(--ts-tt-lg) !important;
  font-weight: 600 !important;
  line-height: var(--tl-tt-lg) !important;
  color: var(--os) !important;
  margin: 16px 0 8px !important;
}
/* Body default → Body Medium */
p, span, label, div, li, td, th {
  font-size: var(--ts-bd-md) !important;
  line-height: var(--tl-bd-md) !important;
  color: var(--os) !important;
}

/* ── M3 Filled Button ── */
/* 일반 stButton (탭 내부 버튼들) */
.stButton > button {
  background: var(--p) !important;
  color: #fff !important;
  border: none !important;
  border-radius: var(--r-full) !important;
  padding: 10px 18px !important;
  font-size: var(--ts-lb-lg) !important;
  font-weight: var(--tw-lb-lg) !important;
  letter-spacing: var(--tk-lb-lg) !important;
  line-height: var(--tl-lb-lg) !important;
  box-shadow: var(--el1) !important;
  transition: background .15s, box-shadow .15s !important;
  width: 100% !important;
}
.stButton > button:hover  { background: var(--pd) !important; box-shadow: var(--el2) !important; }
.stButton > button:active { transform: scale(.98) !important; }
.stButton > button * { color: #fff !important; font-size: inherit !important; }
/* 파일업로더 안의 stButton은 width auto로 덮어쓰기 */
[data-testid="stFileUploader"] .stButton > button {
  width: auto !important;
  padding: 8px 20px !important;
}

/* ── M3 Text Input ── */
[data-baseweb="input"] input, [data-baseweb="textarea"] textarea {
  background: #fff !important;
  border: 1.5px solid var(--ov) !important;
  border-radius: var(--r-md) !important;
  color: var(--os) !important;
  padding: 14px 16px !important;
  font-size: var(--ts-bd-lg) !important;
  line-height: var(--tl-bd-lg) !important;
}
[data-baseweb="input"] input:focus {
  border-color: var(--p) !important;
  box-shadow: 0 0 0 3px rgba(56,106,31,.12) !important;
}
[data-baseweb="input"], [data-baseweb="base-input"] { border: none !important; background: transparent !important; }
.stTextInput input::placeholder { color: var(--osl) !important; }

/* ── File Uploader ── */
[data-testid="stFileUploader"] {
  background: #fff !important;
  border: 1.5px dashed var(--ov) !important;
  border-radius: var(--r-lg) !important;
}
[data-testid="stFileUploader"] *             { color: var(--os) !important; }
[data-testid="stFileUploader"] section       { background: transparent !important; }
[data-testid="stFileUploader"] section > div { background: transparent !important; color: var(--os) !important; }
[data-testid="stFileUploader"] button {
  background: var(--p) !important;
  color: #fff !important;
  border-radius: var(--r-full) !important;
  font-size: var(--ts-lb-lg) !important;
  font-weight: var(--tw-lb-lg) !important;
  padding: 8px 20px !important;
}
[data-testid="stFileUploader"] button * { color: #fff !important; }
/* 파일업로더 내 드래그 안내 텍스트 */
[data-testid="stFileUploaderDropzoneInstructions"] p {
  font-size: var(--ts-bd-md) !important;
  color: var(--osl) !important;
}

/* ── Audio Input ── */
[data-testid="stAudioInput"] {
  background: var(--s2) !important;
  border: 1.5px solid var(--ov) !important;
  border-radius: var(--r-lg) !important;
  overflow: hidden !important;
}
[data-testid="stAudioInput"] > div { background: var(--s2) !important; }
[data-testid="stAudioInput"] * svg path { fill: var(--p) !important; }

/* ── Radio — Segment Control ── */
.stRadio > div {
  display: flex !important;
  flex-direction: row !important;
  background: var(--s2) !important;
  border-radius: var(--r-full) !important;
  padding: 4px !important;
  gap: 0 !important;
}
.stRadio > div > label {
  flex: 1 !important;
  text-align: center !important;
  border-radius: var(--r-full) !important;
  padding: 10px 16px !important;
  cursor: pointer !important;
  transition: all .15s !important;
  margin: 0 !important;
  background: transparent !important;
}
.stRadio > div > label[data-checked="true"],
.stRadio > div > label[aria-checked="true"] {
  background: #fff !important;
  box-shadow: var(--el1) !important;
}
.stRadio > div > label * { color: var(--os) !important; }
[data-testid="stWidgetLabel"],
[data-testid="InputInstructions"] { display: none !important; }

/* ── Progress Bar ── */
.stProgress > div     { background: var(--s3) !important; border-radius: var(--r-full) !important; height: 8px !important; }
.stProgress > div > div { background: var(--p) !important; border-radius: var(--r-full) !important; }

/* ── Expander ── */
[data-testid="stExpander"] {
  background: #fff !important;
  border: 1px solid var(--ov) !important;
  border-radius: var(--r-lg) !important;
  overflow: hidden !important;
  box-shadow: var(--el1) !important;
}
/* summary 전체 흰색 + 텍스트 정상화 */
details summary {
  background: #fff !important;
  padding: 16px !important;
  cursor: pointer !important;
  list-style: none !important;
}
details summary::-webkit-details-marker { display: none !important; }
/* Streamlit이 summary 안에 삽입하는 모든 요소 */
details summary *,
.streamlit-expanderHeader,
.streamlit-expanderHeader * {
  background: #fff !important;
  color: var(--os) !important;
  font-size: var(--ts-tt-md) !important;
  font-weight: var(--tw-tt-md) !important;
}
[data-testid="stExpanderToggleIcon"],
[data-testid="stExpanderToggleIcon"] * {
  fill: var(--os) !important;
  color: var(--os) !important;
}

/* ── Selectbox ── */
[data-baseweb="select"], [data-baseweb="select"] * {
  background: #fff !important; color: var(--os) !important;
  border-color: var(--ov) !important; border-radius: var(--r-md) !important;
}
[data-baseweb="popover"] *, [data-baseweb="menu"] *, ul[role="listbox"] * {
  background: #fff !important; color: var(--os) !important;
}

/* ── Bottom Navigation Tabs ── */
.stTabs [data-baseweb="tab-list"] {
  position: fixed !important;
  bottom: 0 !important; left: 0 !important; right: 0 !important;
  z-index: 9999 !important;
  background: rgba(255,255,255,.97) !important;
  backdrop-filter: blur(20px) !important;
  -webkit-backdrop-filter: blur(20px) !important;
  border-top: 1px solid var(--ov) !important;
  padding: 4px 0 12px !important;
  justify-content: space-around !important;
  gap: 0 !important;
}
.stTabs [data-baseweb="tab"] {
  color: var(--osl) !important;
  background: transparent !important;
  border: none !important;
  padding: 6px 12px 2px !important;
  /* Label Small (M3 탭 스펙) */
  font-size: var(--ts-lb-sm) !important;
  font-weight: var(--tw-lb-sm) !important;
  letter-spacing: var(--tk-lb-sm) !important;
  min-height: 52px !important;
  flex-direction: column !important;
  gap: 2px !important;
}
.stTabs [aria-selected="true"] {
  color: var(--p) !important;
  font-weight: 600 !important;
}
.stTabs [data-baseweb="tab-border"],
.stTabs [data-baseweb="tab-highlight"] { display: none !important; }
.stTabs [data-baseweb="tab-panel"]     { padding-top: 0 !important; }

/* ── Divider ── */
hr { border: none !important; border-top: 1px solid var(--ov) !important; margin: 16px 0 !important; }

/* ── Caption — Label Medium ── */
[data-testid="stCaptionContainer"] p {
  color: var(--osl) !important;
  font-size: var(--ts-lb-md) !important;
  line-height: var(--tl-lb-md) !important;
  letter-spacing: var(--tk-lb-md) !important;
}

/* ── Alert ── */
[data-testid="stAlert"] {
  background: var(--s2) !important; border-color: var(--ov) !important;
  color: var(--os) !important; border-radius: var(--r-lg) !important;
}
[data-testid="stAlert"] * { color: var(--os) !important; }
</style>
""", unsafe_allow_html=True)

# ========================================
# 상수
# ========================================
FASTAPI_URL = "http://localhost:8000"
PLANTS_FILE = Path("data/plants.json")
CARE_LOG_FILE = Path("data/care_log.jsonl")

DISEASE_KOREAN = {
    "Bacterial_Spot": "세균성 반점",
    "Early_Blight": "초기 마름병",
    "Greening": "그리닝병",
    "Healthy": "건강",
    "Late_Blight": "후기 마름병",
    "Leaf_Curl": "잎 말림",
    "Leaf_Mold": "잎 곰팡이",
    "Leaf_Spot": "잎 반점",
    "Mosaic_Virus": "모자이크 바이러스",
    "Powdery_Mildew": "흰가루병",
    "Rust": "녹병",
    "Scab_Rot": "딱지병/부패",
}

ACTION_LABELS = {
    "water": "💧 물줬음",
    "move": "☀️ 자리옮김",
    "prune": "✂️ 가지치기",
    "medicine": "💊 약줬음",
    "repot": "🪴 분갈이",
    "clean": "🍃 잎닦음",
    "observe": "😊 그냥봄",
}
ACTION_LABELS_REVERSE = {v: k for k, v in ACTION_LABELS.items()}

ACTION_COLORS = {
    "water": "#4A90D9",
    "move": "#F5A623",
    "prune": "#7ED321",
    "medicine": "#D0021B",
    "repot": "#8B572A",
    "clean": "#9013FE",
    "observe": "#386A1F",
}

CARE_RESPONSES: dict[str, list[str]] = {
    "water": ["{}한테 전해놨어! 물 받아서 좋아하겠다", "기록했어. 꾸준히 챙겨주는 너 멋있다", "{}이 시원하대. 고마워"],
    "medicine": ["{}한테 전해놨어! 빨리 나을 거야", "약 줬구나. 네가 옆에 있어서 {}이 든든할 거야"],
    "observe": ["그냥 봐주는 것도 돌봄이야. {}이 알고 있을 거야", "가만히 지켜봐주는 것만으로도 충분할 때가 있어"],
    "move": ["{}한테 전해놨어! 새 자리 마음에 들어하겠다"],
    "prune": ["정리해줬구나. {}이 한결 가벼워졌을 거야"],
    "repot": ["분갈이까지! 너 진짜 잘 챙긴다. {}이 좋아할 거야"],
    "clean": ["잎 닦아줬구나. {}이 상쾌하대"],
}

# ========================================
# 데이터 함수
# ========================================
def load_plants():
    if PLANTS_FILE.exists():
        return json.loads(PLANTS_FILE.read_text(encoding="utf-8"))
    return []

def save_plant(nickname):
    plants = load_plants()
    plants.append({
        "nickname": nickname,
        "species": "",
        "registered": datetime.now().strftime("%Y-%m-%d"),
    })
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
    entry = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "plant": nickname,
        "action": action,
    }
    if "last_diagnosis" in st.session_state:
        diag = st.session_state.last_diagnosis
        entry["disease"] = diag.get("disease", "")
        entry["lesion"] = diag.get("lesion", 0)
    CARE_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CARE_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

def compute_streak(logs: list) -> int:
    if not logs:
        return 0
    care_dates = sorted({l["date"][:10] for l in logs}, reverse=True)
    streak = 0
    expected = date.today()
    for d_str in care_dates:
        try:
            d = date.fromisoformat(d_str)
        except ValueError:
            continue
        if d >= expected - timedelta(days=1):
            streak += 1
            expected = d - timedelta(days=1)
        else:
            break
    return streak

def compute_lesion_trend(logs: list) -> str | None:
    diag_logs = [l for l in logs if l.get("lesion") is not None and l["lesion"] > 0]
    if len(diag_logs) < 2:
        return None
    first = diag_logs[0]["lesion"]
    last = diag_logs[-1]["lesion"]
    if first == 0:
        return None
    change = (last - first) / first * 100
    sign = "+" if change > 0 else ""
    return f"{sign}{change:.0f}%"

# ========================================
# 컴포넌트 함수
# ========================================
def chip(text: str, color: str = "#386A1F", bg: str = "#C3E8A8") -> str:
    return (
        f'<span style="display:inline-flex;align-items:center;background:{bg};color:{color};'
        f'border-radius:100px;padding:4px 12px;font-size:12px;font-weight:600;'
        f'line-height:1.4;white-space:nowrap;">{text}</span>'
    )

def boonz(mood: str, message: str) -> None:
    emojis = {"happy": "😊", "worried": "😟", "sad": "😢", "loading": "👀", "default": "🌱"}
    emoji = emojis.get(mood, "🌱")
    col1, col2 = st.columns([1, 8])
    with col1:
        st.markdown(
            f'<div style="width:40px;height:40px;background:#EAF3DE;border-radius:50%;'
            f'display:flex;align-items:center;justify-content:center;font-size:20px;">{emoji}</div>',
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f'<div style="background:#fff;border:1px solid #E5E0D5;'
            f'border-radius:16px 16px 16px 4px;padding:10px 14px;'
            f'box-shadow:0 1px 3px rgba(0,0,0,0.06);margin-bottom:4px;">'
            f'<div style="color:#386A1F;font-size:11px;font-weight:600;margin-bottom:2px;">분즈</div>'
            f'<div style="color:#1A1C18;font-size:14px;line-height:1.55;">{message}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )

def _show_boonz(result: dict, default_mood: str = "default") -> None:
    b = result.get("boonz", {})
    boonz(b.get("mood", default_mood), b.get("message", ""))

def stat_card_row(stats: list[tuple]) -> None:
    """stats: list of (label, value, color)"""
    n = len(stats)
    divider = '<div style="width:1px;background:#E5E0D5;margin:4px 0;align-self:stretch;"></div>'
    cells = []
    for label, value, color in stats:
        cells.append(
            f'<div style="flex:1;text-align:center;padding:12px 8px;">'
            f'<div style="font-size:26px;font-weight:700;color:{color};letter-spacing:-.5px;line-height:1.2;">{value}</div>'
            f'<div style="font-size:11px;color:#73796E;margin-top:4px;font-weight:500;">{label}</div>'
            f'</div>'
        )
    inner = divider.join(cells)
    st.markdown(
        f'<div style="display:flex;align-items:stretch;background:#fff;'
        f'border-radius:16px;padding:4px 0;box-shadow:0 1px 3px rgba(0,0,0,0.08);margin:8px 0;">'
        f'{inner}</div>',
        unsafe_allow_html=True,
    )

def timeline_entry(log_date: str, action: str, disease: str = "", lesion: float = 0) -> None:
    label = ACTION_LABELS.get(action, action)
    color = ACTION_COLORS.get(action, "#73796E")
    disease_kr = DISEASE_KOREAN.get(disease, disease)
    disease_html = ""
    if disease and disease not in ("", "Healthy"):
        disease_html = (
            f'<div style="font-size:11px;color:#73796E;margin-top:2px;">'
            f'{disease_kr} — 병변 {lesion*100:.0f}%</div>'
        )
    st.markdown(
        f'<div style="display:flex;gap:12px;margin:2px 0;">'
        f'<div style="display:flex;flex-direction:column;align-items:center;width:16px;">'
        f'<div style="width:10px;height:10px;border-radius:50%;background:{color};flex-shrink:0;margin-top:6px;"></div>'
        f'<div style="width:1.5px;flex:1;background:#E5E0D5;margin-top:3px;"></div>'
        f'</div>'
        f'<div style="flex:1;background:#fff;border-radius:12px;padding:10px 14px;'
        f'box-shadow:0 1px 2px rgba(0,0,0,0.06);margin-bottom:6px;">'
        f'<div style="font-size:13px;font-weight:500;color:#1A1C18;">{label}</div>'
        f'<div style="font-size:11px;color:#B4B2A9;margin-top:2px;">{log_date}</div>'
        f'{disease_html}'
        f'</div></div>',
        unsafe_allow_html=True,
    )

def milestone_chip_render(stage: str) -> None:
    bg_map = {
        "🌱 새로운 만남": "#C3E8A8",
        "🌿 알아가는 중": "#B7D4A0",
        "🪴 함께하는 사이": "#9EC080",
        "🌳 오랜 친구": "#6A9E50",
    }
    bg = bg_map.get(stage, "#C3E8A8")
    st.markdown(
        f'<div style="text-align:center;margin:12px 0 4px;">'
        f'<span style="background:{bg};color:#245213;border-radius:100px;'
        f'padding:5px 16px;font-size:12px;font-weight:600;">{stage}</span></div>',
        unsafe_allow_html=True,
    )

# ========================================
# 인사 메시지
# ========================================
def get_greeting(nickname: str, days: int, logs: list) -> tuple[str, str]:
    hour = datetime.now().hour
    if days >= 30:
        title = f"{nickname}랑 함께한 지\n벌써 {days}일째야."
    elif hour < 9:
        title = f"좋은 아침.\n{nickname} 오늘도 잘 있을까?"
    elif hour < 13:
        title = f"오늘은 {nickname}한테\n뭐 해줄 거야?"
    elif hour < 18:
        title = f"{nickname}한테\n잠깐 들러볼까?"
    else:
        title = f"오늘 하루 수고했어.\n{nickname}도 잘 있었을까?"

    boonz_msg = f"오늘도 {nickname} 챙겨주네. 이런 시간이 너한테도 좋은 거야"
    if logs:
        try:
            last_date_str = logs[-1].get("date", "")[:10]
            last_date = date.fromisoformat(last_date_str)
            gap = (date.today() - last_date).days
            last_action = logs[-1].get("action", "")
            if gap == 0:
                boonz_msg = f"오늘도 {nickname} 챙겨주네. 이런 시간이 너한테도 좋은 거야"
            elif gap == 1:
                al = ACTION_LABELS.get(last_action, "")
                boonz_msg = f"어제 {al} 해줬지? 꾸준한 거 좋다"
            elif gap <= 5:
                boonz_msg = f"{gap}일 만이네. 바빴구나. {nickname}은 기다리고 있었어"
            else:
                boonz_msg = f"{gap}일째야. 바쁜 거 알지만, {nickname} 좀 봐줘. 잠깐이면 돼"
        except (ValueError, IndexError):
            pass
    return title, boonz_msg

# ========================================
# 온보딩
# ========================================
plants = load_plants()

if not plants:
    st.markdown(
        '<div style="margin: 8px 0 16px;">'
        '<div style="font-size:15px;font-weight:400;color:#73796E;line-height:1.4;margin-bottom:2px;">식물 별명을</div>'
        '<div style="font-size:28px;font-weight:700;color:#1A1C18;line-height:1.25;letter-spacing:-0.3px;">하나 지어줘.</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.caption("이름을 부르면, 관계가 시작돼.")
    boonz("default", "별명 하나만 알려줘. 내가 기억할게")
    name = st.text_input("별명", placeholder="예: 초록이, 마리", label_visibility="collapsed")
    if name:
        save_plant(name)
        st.rerun()
    st.stop()

# ========================================
# 식물 선택 + 계산
# ========================================
plant_names = [p["nickname"] for p in plants]
if len(plant_names) > 1:
    nickname = st.selectbox("내 식물", plant_names, label_visibility="collapsed")
else:
    nickname = plant_names[0]

current = next((p for p in plants if p["nickname"] == nickname), {})
try:
    days = (datetime.now() - datetime.strptime(
        current.get("registered", "2026-01-01"), "%Y-%m-%d"
    )).days
except ValueError:
    days = 0

care_logs = load_care_log(nickname)
streak = compute_streak(care_logs)
lesion_trend = compute_lesion_trend(care_logs)
action_counts = Counter(log.get("action", "") for log in care_logs)
total_care = len(care_logs)

if days <= 7:
    _stage = "🌱 새로운 만남"
    _stage_desc = "서로 알아가는 중이야. 자주 들러줘"
    _stage_idx = 0
elif days <= 30:
    _stage = "🌿 알아가는 중"
    _stage_desc = "돌봄이 습관이 되고 있어. 좋은 신호야"
    _stage_idx = 1
elif days <= 90:
    _stage = "🪴 함께하는 사이"
    _stage_desc = f"{nickname}가 너의 하루 일부가 됐네"
    _stage_idx = 2
else:
    _stage = "🌳 오랜 친구"
    _stage_desc = f"이쯤 되면 {nickname}가 너를 돌보는 거야"
    _stage_idx = 3

species_text = current.get("species", "") or "종을 알아보려면 사진을 찍어줘"
_title, _boonz_greeting = get_greeting(nickname, days, care_logs)

# ========================================
# 홈 헤더
# ========================================
# _title은 "\n" 구분으로 두 줄. 앞 줄은 Body Large(컨텍스트), 뒷 줄은 Headline Large(메인)
_title_parts = _title.split("\n")
_context_line = _title_parts[0] if len(_title_parts) > 1 else ""
_headline_line = _title_parts[-1]

st.markdown(
    f'<div style="margin: 8px 0 16px;">'
    f'<div style="font-size:15px;font-weight:400;color:#73796E;line-height:1.4;margin-bottom:2px;">'
    f'{_context_line}</div>'
    f'<div style="font-size:28px;font-weight:700;color:#1A1C18;line-height:1.25;letter-spacing:-0.3px;">'
    f'{_headline_line}</div>'
    f'</div>',
    unsafe_allow_html=True,
)

# 식물 카드
st.markdown(
    f'<div style="background:linear-gradient(135deg,#F6FBF0 0%,#ECF5E3 100%);'
    f'border-radius:20px;padding:20px;margin:12px 0;'
    f'box-shadow:0 2px 8px rgba(56,106,31,0.10);">'
    f'<div style="display:flex;justify-content:space-between;align-items:flex-start;">'
    f'<div style="flex:1;">'
    f'<div style="font-size:22px;font-weight:700;color:#1A1C18;margin-bottom:4px;">{nickname}</div>'
    f'<div style="font-size:13px;color:#73796E;margin-bottom:8px;">{species_text}</div>'
    f'{chip(_stage)}'
    f'<div style="font-size:11px;color:#8E9E89;margin-top:8px;">{_stage_desc}</div>'
    f'</div>'
    f'<div style="font-size:52px;filter:drop-shadow(0 2px 4px rgba(0,0,0,.08));margin-left:12px;">🌱</div>'
    f'</div></div>',
    unsafe_allow_html=True,
)

# 통계 3칸
trend_color = "#BA1A1A" if lesion_trend and lesion_trend.startswith("+") else "#386A1F"
stat_card_row([
    ("함께한 날", f"{days}일", "#386A1F"),
    ("연속 돌봄", f"{streak}일", "#386A1F"),
    ("병변 변화", lesion_trend or "—", trend_color if lesion_trend else "#B4B2A9"),
])

# 분즈 인사
boonz("default", _boonz_greeting)

# ========================================
# 탭 (바텀 네비)
# ========================================
tab1, tab2, tab3, tab4 = st.tabs(["📷 진단", "🎙️ 상담", "💊 약제", "📊 이력"])

# ========================================
# Tab 1: 사진 진단
# ========================================
with tab1:
    uploaded = st.file_uploader(
        "잎 사진을 올려줘", type=["jpg", "jpeg", "png"],
        key="diag", label_visibility="collapsed",
    )

    if not uploaded:
        boonz("default", f"{nickname} 사진 줘. 내가 봐줌")

    if uploaded:
        boonz("loading", "잠깐, 얘 얘기 좀 들어보고 있어...")
        try:
            files = {"file": (uploaded.name, uploaded.getvalue(), uploaded.type)}
            resp = requests.post(
                f"{FASTAPI_URL}/diagnose",
                files=files,
                data={"nickname": nickname},
            )
            result = resp.json()

            # SAM 비교
            col1, col2 = st.columns(2)
            with col1:
                st.image(uploaded, caption="원본", use_container_width=True)
            with col2:
                overlay = result.get("overlay_image")
                if overlay:
                    st.image(base64.b64decode(overlay), caption="병변 분석", use_container_width=True)

            # 진단 결과 카드
            disease = result.get("disease", {})
            lesion = result.get("lesion", {})
            species_info = result.get("species", {})
            ratio = lesion.get("ratio", 0) * 100
            disease_kr = DISEASE_KOREAN.get(disease.get("name", ""), disease.get("name", ""))
            conf = disease.get("confidence", 0)
            severity = lesion.get("severity", "")

            healthy = disease.get("name", "") == "Healthy"
            card_bg = "#F6FBF0" if healthy else "#FFF8F8"
            card_accent = "#386A1F" if healthy else "#D0021B"
            status_chip = chip("건강해 👍", "#245213", "#C3E8A8") if healthy else chip(f"{disease_kr}", "#7A0010", "#FFD7D7")

            st.markdown(
                f'<div style="background:{card_bg};border-radius:16px;padding:16px;'
                f'border-left:4px solid {card_accent};margin:8px 0;'
                f'box-shadow:0 1px 3px rgba(0,0,0,0.07);">'
                f'<div style="font-size:16px;font-weight:700;color:#1A1C18;margin-bottom:6px;">{nickname}</div>'
                f'<div style="margin-bottom:8px;">{status_chip}</div>'
                f'<div style="font-size:12px;color:#73796E;">신뢰도 {conf:.0%} · 병변 {ratio:.1f}% · {severity}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

            st.progress(min(ratio / 100, 1.0))

            _show_boonz(result)

            # 케어 가이드
            care = result.get("care_guide", {})
            if care.get("text"):
                st.markdown(
                    f'<div style="background:#fff;border-radius:16px;padding:16px;'
                    f'border-left:3px solid #386A1F;margin:8px 0;'
                    f'box-shadow:0 1px 3px rgba(0,0,0,0.06);">'
                    f'<div style="font-size:12px;font-weight:600;color:#386A1F;margin-bottom:6px;">🌿 케어 가이드</div>'
                    f'<div style="font-size:14px;color:#1A1C18;line-height:1.6;">{care["text"]}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            if care.get("audio_url"):
                st.audio(care["audio_url"])

            st.divider()
            st.markdown(f"**방금 {nickname}한테 뭐 해줬어?**")
            care_cols = st.columns(4)
            for i, (label, action) in enumerate(ACTION_LABELS_REVERSE.items()):
                with care_cols[i % 4]:
                    if st.button(label, key=f"t1_{action}", use_container_width=True):
                        save_care_log(nickname, action)
                        templates = CARE_RESPONSES.get(action, ["{}한테 전해놨어!"])
                        _msg = random.choice(templates).format(nickname)
                        boonz("happy", _msg)

            st.session_state.last_diagnosis = {
                "disease": disease.get("name", ""),
                "lesion": lesion.get("ratio", 0),
            }
            if species_info.get("name"):
                update_species(nickname, species_info["name"])

        except Exception as e:
            boonz("worried", "앗 나 잠깐 버그남. 근데 괜찮아, 다시 해볼게")
            st.caption(str(e))

# ========================================
# Tab 2: 음성 상담
# ========================================
with tab2:
    boonz("default", f"뭐가 궁금해? 내가 {nickname}한테 물어볼게")

    consult_mode = st.radio(
        "입력방식", ["🎙️ 음성", "💬 텍스트"],
        horizontal=True, label_visibility="collapsed",
        key="consult_mode",
    )

    if consult_mode == "🎙️ 음성":
        audio_input = st.audio_input("말해봐, 내가 들을게", key="voice")

        if audio_input:
            try:
                files = {"file": ("audio.wav", audio_input.getvalue(), "audio/wav")}
                resp = requests.post(
                    f"{FASTAPI_URL}/consult/voice",
                    files=files,
                    data={"nickname": nickname},
                )
                st.session_state.voice_result = resp.json()
            except Exception as e:
                st.session_state.voice_result = {"_error": str(e)}

        vr = st.session_state.get("voice_result")
        if vr:
            if "_error" in vr:
                boonz("worried", "앗 나 잠깐 버그남. 근데 괜찮아, 다시 해볼게")
                st.caption(vr["_error"])
            else:
                transcript = vr.get("transcript", "")
                if transcript:
                    st.markdown(
                        f'<div style="text-align:right;margin:4px 0;">'
                        f'<span style="background:#EAF3DE;border-radius:16px 16px 4px 16px;'
                        f'padding:8px 14px;font-size:14px;color:#1A1C18;display:inline-block;">'
                        f'{transcript}</span></div>',
                        unsafe_allow_html=True,
                    )
                _show_boonz(vr, "happy")
                audio_url = vr.get("answer", {}).get("audio_url")
                if audio_url:
                    st.audio(audio_url)

    else:
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []

        for entry in st.session_state.chat_history:
            role = entry.get("role", "user")
            text = entry.get("text", "")
            if role == "user":
                st.markdown(
                    f'<div style="text-align:right;margin:4px 0;">'
                    f'<span style="background:#EAF3DE;border-radius:16px 16px 4px 16px;'
                    f'padding:8px 14px;font-size:14px;color:#1A1C18;display:inline-block;">'
                    f'{text}</span></div>',
                    unsafe_allow_html=True,
                )
            else:
                boonz("happy", text)

        question = st.text_input(
            "질문", placeholder="예: 잎이 노랗게 변하는데 왜 그래?",
            key="q_text", label_visibility="collapsed",
        )
        if question:
            st.session_state.chat_history.append({"role": "user", "text": question})
            try:
                diagnosis_context = ""
                if "last_diagnosis" in st.session_state:
                    d = st.session_state.last_diagnosis
                    diagnosis_context = f"{d.get('disease', '')} 병변 {d.get('lesion', 0)*100:.0f}%"
                resp = requests.post(
                    f"{FASTAPI_URL}/consult/text",
                    data={
                        "question": question,
                        "nickname": nickname,
                        "diagnosis_context": diagnosis_context,
                    },
                )
                result = resp.json()
                answer_text = result.get("answer", {}).get("text", "")
                if answer_text:
                    st.session_state.chat_history.append({"role": "boonz", "text": answer_text})
                _show_boonz(result, "happy")
                if result.get("answer", {}).get("audio_url"):
                    st.audio(result["answer"]["audio_url"])
                st.rerun()
            except Exception as e:
                boonz("worried", "앗 나 잠깐 버그남. 근데 괜찮아, 다시 해볼게")

# ========================================
# Tab 3: 약제 체크
# ========================================
with tab3:
    uploaded_med = st.file_uploader(
        "약제 라벨 찍어줘", type=["jpg", "jpeg", "png"],
        key="med", label_visibility="collapsed",
    )

    if not uploaded_med:
        if "last_diagnosis" not in st.session_state:
            boonz("worried", f"먼저 {nickname} 사진을 찍어줘. 뭐가 필요한지 알아야 도와줄 수 있어")
        else:
            boonz("default", "뭐 사왔어? 보여줘")

    if uploaded_med:
        try:
            files = {"file": (uploaded_med.name, uploaded_med.getvalue(), uploaded_med.type)}
            resp = requests.post(
                f"{FASTAPI_URL}/medicine",
                files=files,
                data={"nickname": nickname},
            )
            result = resp.json()

            for ing in result.get("ingredients", []):
                st.markdown(
                    f'<div style="background:#fff;border-radius:12px;padding:12px 16px;'
                    f'margin:4px 0;box-shadow:0 1px 2px rgba(0,0,0,0.06);">'
                    f'<span style="color:#1A1C18;font-size:14px;">{ing["text"]}</span> '
                    f'<span style="color:#73796E;font-size:12px;">({ing["confidence"]:.0%})</span>'
                    f'</div>',
                    unsafe_allow_html=True,
                )

            _show_boonz(result)
        except Exception as e:
            boonz("worried", "앗 나 잠깐 버그남. 근데 괜찮아, 다시 해볼게")

# ========================================
# Tab 4: 케어 이력
# ========================================
with tab4:

    # ── A. 원터치 케어 ──
    st.markdown(f"**오늘 {nickname}한테 뭐 해줬어?**")
    care_cols = st.columns(4)
    for i, (label, action) in enumerate(ACTION_LABELS.items()):
        with care_cols[i % 4]:
            if st.button(label, key=f"c_{action}", use_container_width=True):
                save_care_log(nickname, action)
                st.rerun()

    st.divider()

    # ── B. 돌봄 리포트 카드 ──
    st.markdown("### 돌봄 리포트")
    tr_color = "#BA1A1A" if lesion_trend and lesion_trend.startswith("+") else "#386A1F"
    stat_card_row([
        ("함께한 날", f"{days}일", "#386A1F"),
        ("총 돌봄 횟수", f"{total_care}회", "#386A1F"),
        ("병변 변화", lesion_trend or "—", tr_color if lesion_trend else "#B4B2A9"),
    ])

    # ── C. 로컬 패턴 분석 ──
    good_items = []
    if streak >= 3:
        good_items.append(f"🔥 {streak}일 연속 돌봄 중이야. 대단해")
    if action_counts.get("water", 0) >= 5:
        good_items.append(f"💧 물주기를 {action_counts['water']}번이나 챙겼어")
    if total_care >= 10:
        good_items.append(f"📝 기록이 {total_care}개 쌓였어. 관계가 보이기 시작해")

    hint_items = []
    least_done = min(
        [(k, action_counts.get(k, 0)) for k in ACTION_LABELS if k != "observe"],
        key=lambda x: x[1], default=None
    )
    if least_done and least_done[1] == 0:
        hint_label = ACTION_LABELS[least_done[0]]
        hint_items.append(f"{hint_label}은 아직 한 번도 안 했어. 한번 해봐")
    elif days > 30 and action_counts.get("repot", 0) == 0:
        hint_items.append(f"함께한 지 {days}일째야. 분갈이 한번 생각해봐")

    if good_items or hint_items:
        good_html = "".join([
            f'<div style="font-size:13px;color:#1A1C18;padding:6px 0;border-bottom:1px solid #F0F0EC;">'
            f'{item}</div>'
            for item in good_items
        ])
        hint_html = "".join([
            f'<div style="font-size:13px;color:#1A1C18;padding:6px 0;">'
            f'{item}</div>'
            for item in hint_items
        ])
        sections = ""
        if good_html:
            sections += (
                f'<div style="margin-bottom:12px;">'
                f'<div style="font-size:11px;font-weight:600;color:#386A1F;margin-bottom:4px;">잘하고 있어 👏</div>'
                f'{good_html}</div>'
            )
        if hint_html:
            sections += (
                f'<div>'
                f'<div style="font-size:11px;font-weight:600;color:#73796E;margin-bottom:4px;">한 가지 힌트 💡</div>'
                f'{hint_html}</div>'
            )
        boonz_col, _ = st.columns([1, 8])
        st.markdown(
            f'<div style="background:#fff;border-radius:16px;padding:16px;'
            f'box-shadow:0 1px 3px rgba(0,0,0,0.07);margin:4px 0 12px;">'
            f'{sections}</div>',
            unsafe_allow_html=True,
        )

    # ── D. 타임라인 ──
    st.markdown(f"### {nickname}와의 이야기")
    if care_logs:
        recent = list(reversed(care_logs[-20:]))
        prev_stage_idx = None
        for log in recent:
            # 관계 단계 변경 milestone 삽입
            log_days_ago = 0
            try:
                ld = date.fromisoformat(log["date"][:10])
                reg = date.fromisoformat(current.get("registered", "2026-01-01"))
                log_days_ago = (ld - reg).days
            except ValueError:
                pass

            if log_days_ago <= 7:
                log_stage_idx = 0
            elif log_days_ago <= 30:
                log_stage_idx = 1
            elif log_days_ago <= 90:
                log_stage_idx = 2
            else:
                log_stage_idx = 3

            if prev_stage_idx is not None and log_stage_idx != prev_stage_idx:
                stages = ["🌱 새로운 만남", "🌿 알아가는 중", "🪴 함께하는 사이", "🌳 오랜 친구"]
                milestone_chip_render(stages[log_stage_idx])
            prev_stage_idx = log_stage_idx

            timeline_entry(
                log["date"],
                log.get("action", ""),
                log.get("disease", ""),
                log.get("lesion", 0),
            )
    else:
        boonz("default", f"아직 {nickname}이랑 기록이 없네. 위에 버튼 하나만 눌러봐. 그게 시작이야")

    # ── E. 관계 성장 여정 ──
    st.divider()
    st.markdown("### 관계 성장 여정")
    journey_stages = [
        ("🌱", "새로운 만남", "0~7일", 0),
        ("🌿", "알아가는 중", "8~30일", 1),
        ("🪴", "함께하는 사이", "31~90일", 2),
        ("🌳", "오랜 친구", "91일~", 3),
    ]
    for emoji, name, period, idx in journey_stages:
        is_current = idx == _stage_idx
        is_done = idx < _stage_idx
        bg = "#F0F9E8" if is_current else ("#fff" if is_done else "#F8F8F5")
        border = "2px solid #386A1F" if is_current else "1px solid #E5E0D5"
        name_color = "#245213" if is_current else ("#1A1C18" if is_done else "#B4B2A9")
        badge = f' {chip("현재", "#245213", "#C3E8A8")}' if is_current else ("" if not is_done else " ✓")
        st.markdown(
            f'<div style="display:flex;align-items:center;gap:14px;'
            f'background:{bg};border:{border};border-radius:14px;'
            f'padding:14px 16px;margin:6px 0;">'
            f'<div style="font-size:28px;">{emoji}</div>'
            f'<div style="flex:1;">'
            f'<div style="font-size:14px;font-weight:600;color:{name_color};">{name}{badge}</div>'
            f'<div style="font-size:11px;color:#B4B2A9;margin-top:2px;">{period}</div>'
            f'</div></div>',
            unsafe_allow_html=True,
        )

    # ── F. 병변 추세 차트 ──
    diag_logs = [l for l in care_logs if l.get("lesion")]
    if len(diag_logs) >= 2:
        st.divider()
        st.markdown("### 병변 추이")
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=[l["date"] for l in diag_logs],
            y=[l["lesion"] * 100 for l in diag_logs],
            mode="lines+markers",
            line=dict(color="#386A1F", width=2),
            marker=dict(color="#386A1F", size=8),
            fill="tozeroy",
            fillcolor="rgba(56,106,31,0.08)",
        ))
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(gridcolor="#F0EDE8", showline=False, color="#73796E"),
            yaxis=dict(gridcolor="#F0EDE8", title="병변 %", color="#73796E", title_font_color="#73796E"),
            font=dict(color="#73796E", family="Noto Sans KR"),
            height=240,
            margin=dict(l=40, r=16, t=10, b=40),
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)
    elif len(diag_logs) == 1:
        boonz("default", "진단 한 번 더 하면 추세선이 보여")

    # ── G. API 패턴 분석 ──
    st.divider()
    if st.button("🔍 AI 돌봄 패턴 분석", use_container_width=True):
        if len(care_logs) >= 10:
            try:
                resp = requests.get(f"{FASTAPI_URL}/pattern/{nickname}")
                _show_boonz(resp.json(), "happy")
            except Exception:
                boonz("worried", "앗 나 잠깐 버그남. 근데 괜찮아, 다시 해볼게")
        else:
            boonz("default", f"아직 기록이 {len(care_logs)}개야. 10개 넘으면 분석해줄게")

# ========================================
# 하단: 식물 관리
# ========================================
st.divider()
with st.expander("🌱 식물 관리"):
    new_name = st.text_input(
        "새 식물 별명", key="new_p", label_visibility="collapsed",
        placeholder="새 식물 별명 입력",
    )
    if st.button("추가", key="add_p") and new_name:
        save_plant(new_name)
        st.rerun()

    st.divider()
    if st.button(f"🗑️ {nickname} 삭제", key="del_p"):
        delete_plant(nickname)
        st.rerun()
