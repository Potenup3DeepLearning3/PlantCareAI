import base64
import random
from collections import Counter
import streamlit as st
import requests
import json
from pathlib import Path
from datetime import datetime, date
import plotly.graph_objects as go

# ========================================
# 페이지 설정
# ========================================
st.set_page_config(page_title="Boonz", layout="centered", page_icon="🌱")

# ========================================
# CSS (Greener 스타일: 크림 배경 + 그린 키컬러)
# ========================================
st.markdown("""
<style>
    [data-testid="stAppViewContainer"] { background-color: #F7F5F0 !important; }
    [data-testid="stHeader"] { background-color: #F7F5F0 !important; }
    [data-testid="stSidebar"] { display: none !important; }

    h1, h2, h3 { color: #2C2C2A !important; }
    p, span, label, div, li, td, th { color: #2C2C2A; }

    .stButton>button {
        border-radius: 20px !important;
        background-color: #3B6D11 !important;
        border: none !important;
        color: white !important;
        padding: 8px 20px !important;
    }
    .stButton>button:hover { background-color: #2B5A1D !important; }

    .stTextInput input, .stTextArea textarea {
        background: white !important;
        border: 1px solid #E5E0D5 !important;
        border-radius: 12px !important;
        color: #2C2C2A !important;
    }
    .stTextInput input:focus { border-color: #3B6D11 !important; }
    .stTextInput input::placeholder { color: #B4B2A9 !important; }

    [data-testid="stFileUploader"] {
        background: white !important;
        border: 1px dashed #E5E0D5 !important;
        border-radius: 16px !important;
    }
    [data-testid="stFileUploader"] * { color: #2C2C2A !important; }
    [data-testid="stFileUploader"] button {
        background: #3B6D11 !important;
        color: white !important;
        border-radius: 12px !important;
    }

    .stProgress > div > div {
        background-color: #3B6D11 !important;
        border-radius: 10px !important;
    }
    .stProgress > div {
        background-color: #E5E0D5 !important;
        border-radius: 10px !important;
    }

    [data-baseweb="select"], [data-baseweb="select"] * {
        background-color: white !important;
        color: #2C2C2A !important;
        border-color: #E5E0D5 !important;
    }
    [data-baseweb="popover"] *, [data-baseweb="menu"] *,
    ul[role="listbox"] * {
        background-color: white !important;
        color: #2C2C2A !important;
    }

    .stTabs [data-baseweb="tab-list"] {
        position: fixed;
        bottom: 0; left: 0; right: 0;
        z-index: 999;
        background: white !important;
        border-top: 1px solid #E5E0D5 !important;
        padding: 10px 0 !important;
        justify-content: space-around !important;
        box-shadow: 0 -2px 10px rgba(0,0,0,0.05);
    }
    .stTabs [data-baseweb="tab"] {
        color: #B4B2A9 !important;
        background: transparent !important;
        border: none !important;
    }
    .stTabs [aria-selected="true"] {
        color: #3B6D11 !important;
        font-weight: 600 !important;
    }
    .stTabs [data-baseweb="tab-border"],
    .stTabs [data-baseweb="tab-highlight"] { display: none !important; }
    .block-container { padding-bottom: 80px !important; }

    hr { border-color: #E5E0D5 !important; }
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
    "water": "💧 물줬음", "move": "☀️ 자리옮김",
    "prune": "✂️ 가지치기", "medicine": "💊 약줬음",
    "repot": "🪴 분갈이", "clean": "🍃 잎닦음",
    "observe": "😊 그냥봄",
}
ACTION_LABELS_REVERSE = {v: k for k, v in ACTION_LABELS.items()}

CARE_RESPONSES: dict[str, list[str]] = {
    "water": [
        "{}한테 전해놨어! 물 받아서 좋아하겠다",
        "기록했어. 꾸준히 챙겨주는 너 멋있다",
        "{}이 시원하대. 고마워",
    ],
    "medicine": [
        "{}한테 전해놨어! 빨리 나을 거야",
        "약 줬구나. 네가 옆에 있어서 {}이 든든할 거야",
    ],
    "observe": [
        "그냥 봐주는 것도 돌봄이야. {}이 알고 있을 거야",
        "가만히 지켜봐주는 것만으로도 충분할 때가 있어",
    ],
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
        "registered": datetime.now().strftime("%Y-%m-%d")
    })
    PLANTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    PLANTS_FILE.write_text(
        json.dumps(plants, ensure_ascii=False, indent=2), encoding="utf-8"
    )

def delete_plant(nickname):
    plants = [p for p in load_plants() if p["nickname"] != nickname]
    PLANTS_FILE.write_text(
        json.dumps(plants, ensure_ascii=False, indent=2), encoding="utf-8"
    )

def update_species(nickname, species):
    plants = load_plants()
    for p in plants:
        if p["nickname"] == nickname:
            p["species"] = species
    PLANTS_FILE.write_text(
        json.dumps(plants, ensure_ascii=False, indent=2), encoding="utf-8"
    )

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

# ========================================
# 분즈 메시지
# ========================================
def _show_boonz(result: dict, default_mood: str = "default") -> None:
    b = result.get("boonz", {})
    boonz(b.get("mood", default_mood), b.get("message", ""))


def boonz(mood, message):
    emojis = {
        "happy": "😊", "worried": "😟",
        "sad": "😢", "loading": "👀",
        "default": "🌱",
    }
    emoji = emojis.get(mood, "🌱")
    col1, col2 = st.columns([1, 8])
    with col1:
        st.markdown(
            f'<div style="width:40px;height:40px;background:#EAF3DE;'
            f'border-radius:50%;display:flex;align-items:center;'
            f'justify-content:center;font-size:20px;">{emoji}</div>',
            unsafe_allow_html=True,
        )
    with col2:
        st.markdown(
            f'<div style="background:white;border:1px solid #E5E0D5;'
            f'border-radius:16px 16px 16px 4px;padding:10px 14px;'
            f'color:#2C2C2A;font-size:14px;">'
            f'<span style="color:#3B6D11;font-size:11px;font-weight:600;">분즈</span><br>'
            f'{message}</div>',
            unsafe_allow_html=True,
        )

# ========================================
# 온보딩
# ========================================
plants = load_plants()

if not plants:
    st.markdown("## 식물 별명을\n하나 지어줘.")
    st.caption("이름을 부르면, 관계가 시작돼.")
    boonz("default", "별명 하나만 알려줘. 내가 기억할게")
    name = st.text_input(
        "별명", placeholder="예: 초록이, 마리", label_visibility="collapsed"
    )
    if name:
        save_plant(name)
        st.rerun()
    st.stop()

# ========================================
# 식물 선택
# ========================================
plant_names = [p["nickname"] for p in plants]
if len(plant_names) > 1:
    nickname = st.selectbox("내 식물", plant_names, label_visibility="collapsed")
else:
    nickname = plant_names[0]

current = next((p for p in plants if p["nickname"] == nickname), {})
days = (datetime.now() - datetime.strptime(
    current.get("registered", "2026-01-01"), "%Y-%m-%d"
)).days


def _get_dynamic_greeting(plant_nickname: str, logs: list) -> tuple[str, str]:
    """시간대 + 돌봄 공백 기반 인사 반환.

    Args:
        plant_nickname: 식물 별명.
        logs: load_care_log() 결과 (호출자가 제공).

    Returns:
        (title, boonz_msg) 튜플.
    """
    hour = datetime.now().hour
    if hour < 9:
        title = f"좋은 아침.\n{plant_nickname} 오늘도 잘 있을까?"
    elif hour < 13:
        title = f"오늘은 {plant_nickname}한테\n뭐 해줄 거야?"
    elif hour < 18:
        title = f"{plant_nickname}한테\n잠깐 들러볼까?"
    else:
        title = f"오늘 하루 수고했어.\n{plant_nickname}도 잘 있었을까?"

    boonz_msg = f"오늘은 {plant_nickname}한테 뭐 해줄 거야?"
    if logs:
        try:
            last_entry = logs[-1]
            last_date_str = last_entry.get("date", "")[:10]
            last_date = date.fromisoformat(last_date_str)
            gap = (date.today() - last_date).days
            last_action = last_entry.get("action", "")
            if gap == 0:
                boonz_msg = f"오늘도 {plant_nickname} 챙겨주네. 이런 시간이 너한테도 좋은 거야"
            elif gap == 1:
                last_action_label = ACTION_LABELS.get(last_action, "")
                boonz_msg = f"어제 {last_action_label} 해줬지? 꾸준한 거 좋다"
            elif gap == 2:
                boonz_msg = f"이틀 만이네. {plant_nickname} 보고 싶었을걸"
            elif gap <= 5:
                boonz_msg = f"{gap}일 만이다. 바빴구나. {plant_nickname}은 기다리고 있었어"
            else:
                boonz_msg = f"{gap}일째야. 바쁜 거 알지만, {plant_nickname} 좀 봐줘. 잠깐이면 돼"
        except (ValueError, IndexError):
            pass

    return title, boonz_msg


care_logs = load_care_log(nickname)
_title, _boonz_greeting = _get_dynamic_greeting(nickname, care_logs)

# ========================================
# 메인 타이틀 + 식물 카드
# ========================================
st.markdown(f"## {_title}")
st.caption("나와 식물 사이, 분즈가 통역해줄게")
boonz("default", _boonz_greeting)

species_text = current.get("species", "") or "종을 알아보려면 사진을 찍어줘"

if days <= 7:
    _relation_stage = "🌱 새로운 만남"
    _relation_desc = "서로 알아가는 중이야. 자주 들러줘"
elif days <= 30:
    _relation_stage = "🌿 알아가는 중"
    _relation_desc = "돌봄이 습관이 되고 있어. 좋은 신호야"
elif days <= 90:
    _relation_stage = "🪴 함께하는 사이"
    _relation_desc = f"{nickname}가 너의 하루 일부가 됐네"
else:
    _relation_stage = "🌳 오랜 친구"
    _relation_desc = f"이쯤 되면 {nickname}가 너를 돌보는 거야"

st.markdown(
    f'<div style="background:#FFF9E6;border-radius:20px;padding:20px;margin-bottom:12px;">'
    f'<div style="display:flex;justify-content:space-between;align-items:center;">'
    f'<div>'
    f'<div style="font-size:22px;font-weight:700;color:#2C2C2A;">{nickname}</div>'
    f'<div style="font-size:13px;color:#888780;">{species_text}</div>'
    f'<div style="font-size:12px;color:#B4B2A9;">키운 지 {days}일째 · {_relation_stage}</div>'
    f'<div style="font-size:11px;color:#B4B2A9;margin-top:2px;">{_relation_desc}</div>'
    f'</div>'
    f'<div style="font-size:36px;">🌱</div>'
    f'</div></div>',
    unsafe_allow_html=True,
)

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

            # 이미지 비교
            col1, col2 = st.columns(2)
            with col1:
                st.image(uploaded, caption="원본", use_container_width=True)
            with col2:
                overlay = result.get("overlay_image")
                if overlay:
                    st.image(
                        base64.b64decode(overlay),
                        caption="SAM 분석",
                        use_container_width=True,
                    )

            # 결과 카드
            disease = result.get("disease", {})
            lesion = result.get("lesion", {})
            species_info = result.get("species", {})
            ratio = lesion.get("ratio", 0) * 100
            disease_kr = DISEASE_KOREAN.get(
                disease.get("name", ""), disease.get("name", "")
            )

            st.markdown(
                f'<div style="background:white;border-radius:20px;padding:20px;'
                f'box-shadow:0 2px 8px rgba(0,0,0,0.04);margin:8px 0;">'
                f'<div style="font-size:18px;font-weight:700;color:#2C2C2A;">{nickname}</div>'
                f'<div style="font-size:13px;color:#888780;">증상: {disease_kr} ({disease.get("confidence", 0):.0%})</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

            st.progress(min(ratio / 100, 1.0))
            st.caption(f"병변 {ratio:.1f}% — {lesion.get('severity', '')}")

            _show_boonz(result)

            # 케어 가이드
            care = result.get("care_guide", {})
            if care.get("text"):
                st.markdown(
                    f'<div style="background:white;border-radius:16px;padding:16px;'
                    f'border-left:3px solid #3B6D11;margin:8px 0;color:#2C2C2A;font-size:14px;">'
                    f'{care["text"]}</div>',
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

            # 세션에 진단 결과 저장
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

    voice_tab, text_tab = st.tabs(["🎙️ 음성", "💬 텍스트"])

    with voice_tab:
        audio_input = st.audio_input("말해봐, 내가 들을게", key="voice")
        if audio_input:
            try:
                files = {"file": ("audio.wav", audio_input.getvalue(), "audio/wav")}
                resp = requests.post(
                    f"{FASTAPI_URL}/consult/voice",
                    files=files,
                    data={"nickname": nickname},
                )
                result = resp.json()
                st.caption(f"내가 한 말: {result.get('transcript', '')}")
                _show_boonz(result, "happy")
                if result.get("answer", {}).get("audio_url"):
                    st.audio(result["answer"]["audio_url"])
            except Exception as e:
                boonz("worried", "앗 나 잠깐 버그남. 근데 괜찮아, 다시 해볼게")

    with text_tab:
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []

        for entry in st.session_state.chat_history:
            role = entry.get("role", "user")
            text = entry.get("text", "")
            if role == "user":
                st.markdown(
                    f'<div style="text-align:right;margin:4px 0;">'
                    f'<span style="background:#EAF3DE;border-radius:16px 16px 4px 16px;'
                    f'padding:8px 14px;font-size:14px;color:#2C2C2A;display:inline-block;">'
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
                    f'<div style="background:white;border-radius:12px;padding:10px 14px;'
                    f'margin:4px 0;color:#2C2C2A;font-size:14px;">'
                    f'{ing["text"]} '
                    f'<span style="color:#888780;">({ing["confidence"]:.0%})</span></div>',
                    unsafe_allow_html=True,
                )

            _show_boonz(result)
        except Exception as e:
            boonz("worried", "앗 나 잠깐 버그남. 근데 괜찮아, 다시 해볼게")

# ========================================
# Tab 4: 케어 이력
# ========================================
with tab4:
    # --- 원터치 케어 로그 ---
    st.markdown(f"**오늘 {nickname}한테 뭐 해줬어?**")

    care_actions = {
        "💧 물주기": "water",
        "☀️ 자리옮김": "move",
        "✂️ 가지치기": "prune",
        "💊 약줬음": "medicine",
        "🪴 분갈이": "repot",
        "🍃 잎닦음": "clean",
        "😊 그냥봄": "observe",
    }

    cols = st.columns(4)
    for i, (label, action) in enumerate(care_actions.items()):
        with cols[i % 4]:
            if st.button(label, key=f"c_{action}", use_container_width=True):
                save_care_log(nickname, action)
                st.rerun()

    # --- 관리 현황 ---
    action_counts = Counter(log.get("action", "") for log in care_logs)

    st.markdown("")
    for label, key in [("💧 물주기", "water"), ("💊 약관리", "medicine"), ("😊 관심", "observe")]:
        count = action_counts.get(key, 0)
        c1, c2, c3 = st.columns([2, 6, 1])
        with c1:
            st.caption(label)
        with c2:
            st.progress(min(count / 10, 1.0))
        with c3:
            st.caption(f"{count}/10")

    st.divider()

    # --- 타임라인 ---
    st.markdown(f"### {nickname}와의 이야기")
    if care_logs:
        for log in reversed(care_logs[-15:]):
            label = ACTION_LABELS.get(log["action"], log["action"])
            lesion_text = ""
            if log.get("lesion"):
                lesion_text = f" — 병변 {log['lesion'] * 100:.0f}%"
            st.markdown(
                f'<div style="background:white;padding:10px 14px;border-radius:12px;'
                f'margin:4px 0;font-size:13px;color:#2C2C2A;">'
                f'{log["date"]} — {label}{lesion_text}</div>',
                unsafe_allow_html=True,
            )
    else:
        boonz("default", f"아직 {nickname}이랑 기록이 없네. 위에 버튼 눌러봐. 하나만 눌러도 시작이야")

    # --- Plotly 추세선 ---
    diagnosis_logs = [l for l in care_logs if l.get("lesion")]
    if len(diagnosis_logs) >= 2:
        st.markdown("### 병변 추이")
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=[l["date"] for l in diagnosis_logs],
            y=[l["lesion"] * 100 for l in diagnosis_logs],
            mode="lines+markers",
            line=dict(color="#3B6D11", width=2),
            marker=dict(color="#3B6D11", size=8),
        ))
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(gridcolor="#E5E0D5"),
            yaxis=dict(gridcolor="#E5E0D5", title="병변 %"),
            font=dict(color="#5F5E5A"),
            height=250,
            margin=dict(l=40, r=20, t=10, b=40),
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)
    elif len(diagnosis_logs) == 1:
        boonz("default", "진단 한 번 더 하면 추세선이 보여")

    st.divider()

    # --- 패턴 분석 ---
    if st.button("🔍 돌봄 패턴 분석", use_container_width=True):
        if len(care_logs) >= 10:
            try:
                resp = requests.get(f"{FASTAPI_URL}/pattern/{nickname}")
                result = resp.json()
                _show_boonz(result, "happy")
            except Exception as e:
                boonz("worried", "앗 나 잠깐 버그남. 근데 괜찮아, 다시 해볼게")
        else:
            boonz("default", f"아직 기록이 {len(care_logs)}개야. 조금만 더 쌓아줘")

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
