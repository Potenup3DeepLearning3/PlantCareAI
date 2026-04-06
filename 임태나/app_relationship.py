# Boonz Streamlit 전면 재구축 가이드

## 지시사항
src/frontend/app.py를 삭제하고, 아래 코드로 완전히 새로 만들어줘.
기존 코드 무시. 이 파일이 app.py의 전부야.
절대 부분 수정하지 마. 파일 전체를 이 내용으로 교체해.

반드시 docs/tone-guide.md도 읽고, 모든 메시지를 그 톤에 맞춰.

## 사전 정보
- 병변 모델: 12클래스, create_efficientnet_b3(num_classes=12)
- 체크포인트: checkpoint["model_state_dict"]로 로드
- config 변수: PROJECT_ROOT, MODELS_DIR, OLLAMA_MODEL
- 한글 경로: PIL로 읽고 numpy 변환
- TTS: Qwen3-TTS CustomVoice, speaker="sohee"
- STT: whisper.load_model("turbo")
- FastAPI: localhost:8000

---

## 완성 코드

```python
import streamlit as st
import requests
import json
import random
from pathlib import Path
from datetime import datetime, timedelta
import plotly.graph_objects as go

# ========================================
# 페이지 설정
# ========================================
st.set_page_config(page_title="Boonz", layout="centered", page_icon="🌱")

# ========================================
# CSS (Greener 스타일 + 관계 톤)
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

    .stProgress > div > div { background-color: #3B6D11 !important; border-radius: 10px !important; }
    .stProgress > div { background-color: #E5E0D5 !important; border-radius: 10px !important; }

    [data-baseweb="select"], [data-baseweb="select"] * {
        background-color: white !important; color: #2C2C2A !important; border-color: #E5E0D5 !important;
    }
    [data-baseweb="popover"] *, [data-baseweb="menu"] *, ul[role="listbox"] * {
        background-color: white !important; color: #2C2C2A !important;
    }

    .stTabs [data-baseweb="tab-list"] {
        position: fixed; bottom: 0; left: 0; right: 0; z-index: 999;
        background: white !important; border-top: 1px solid #E5E0D5 !important;
        padding: 10px 0 !important; justify-content: space-around !important;
        box-shadow: 0 -2px 10px rgba(0,0,0,0.05);
    }
    .stTabs [data-baseweb="tab"] { color: #B4B2A9 !important; background: transparent !important; border: none !important; }
    .stTabs [aria-selected="true"] { color: #3B6D11 !important; font-weight: 600 !important; }
    .stTabs [data-baseweb="tab-border"], .stTabs [data-baseweb="tab-highlight"] { display: none !important; }
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
    "Bacterial_Spot": "세균성 반점", "Early_Blight": "초기 마름병",
    "Greening": "그리닝병", "Healthy": "건강",
    "Late_Blight": "후기 마름병", "Leaf_Curl": "잎 말림",
    "Leaf_Mold": "잎 곰팡이", "Leaf_Spot": "잎 반점",
    "Mosaic_Virus": "모자이크 바이러스", "Powdery_Mildew": "흰가루병",
    "Rust": "녹병", "Scab_Rot": "딱지병/부패",
}

ACTION_LABELS = {
    "water": "💧 물줬음", "move": "☀️ 자리옮김", "prune": "✂️ 가지치기",
    "medicine": "💊 약줬음", "repot": "🪴 분갈이", "clean": "🍃 잎닦음",
    "observe": "😊 그냥봄",
}

CARE_RESPONSES = {
    "water": ["{}한테 전해놨어! 물 받아서 좋아하겠다", "기록했어. 꾸준히 챙겨주는 너 멋있다"],
    "medicine": ["{}한테 전해놨어! 빨리 나을 거야", "약 줬구나. 네가 옆에 있어서 {}이 든든할 거야"],
    "observe": ["그냥 봐주는 것도 돌봄이야. {}이 알고 있을 거야", "가만히 지켜봐주는 것만으로도 충분할 때가 있어"],
    "move": ["{}한테 전해놨어! 새 자리 마음에 들어하겠다"],
    "prune": ["정리해줬구나. {}이 한결 가벼워졌을 거야"],
    "repot": ["분갈이까지! 너 진짜 잘 챙긴다"],
    "clean": ["잎 닦아줬구나. {}이 상쾌하대"],
}

MILESTONES = {
    1: "{}이랑 첫 기록이다! 여기서부터 시작이야",
    5: "벌써 5번째. 슬슬 리듬이 생기고 있어",
    10: "10번째 기록! {}이 너한테 고마워하고 있을걸",
    20: "20번이나 챙겼어. 너 이거 진심이구나",
    30: "30번째... {}이 많이 의지하고 있을 거야",
    50: "50번째. 이쯤 되면 {}가 너를 돌보는 거야",
    100: "100번. 할 말 잃었어. 그냥 대단하다",
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
    plants.append({"nickname": nickname, "species": "", "registered": datetime.now().strftime("%Y-%m-%d")})
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
    entry = {"date": datetime.now().strftime("%Y-%m-%d %H:%M"), "plant": nickname, "action": action}
    if "last_diagnosis" in st.session_state:
        diag = st.session_state.last_diagnosis
        entry["disease"] = diag.get("disease", "")
        entry["lesion"] = diag.get("lesion", 0)
    CARE_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CARE_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

def get_streak(care_logs):
    if not care_logs:
        return 0
    dates = sorted(set(log["date"][:10] for log in care_logs))
    streak = 0
    for i in range(len(dates) - 1, -1, -1):
        expected = (datetime.now() - timedelta(days=len(dates) - 1 - i)).strftime("%Y-%m-%d")
        if dates[i] == expected:
            streak += 1
        else:
            break
    return streak

def get_recovery_emoji(lesion_ratio):
    if lesion_ratio > 0.2: return "🥀"
    elif lesion_ratio > 0.1: return "🌱"
    elif lesion_ratio > 0.05: return "🌿"
    elif lesion_ratio > 0.02: return "🪴"
    else: return "🌳"

# ========================================
# 분즈 메시지
# ========================================
def boonz(mood, message):
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
            f'<div style="background:white;border:0.5px solid #E5E0D5;border-radius:16px 16px 16px 4px;'
            f'padding:10px 14px;color:#2C2C2A;font-size:14px;">'
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
    name = st.text_input("별명", placeholder="예: 초록이, 마리", label_visibility="collapsed")
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
days = (datetime.now() - datetime.strptime(current.get("registered", "2026-01-01"), "%Y-%m-%d")).days
care_logs = load_care_log(nickname)
streak = get_streak(care_logs)
total_logs = len(care_logs)

# ========================================
# 관계 성장 단계
# ========================================
if days <= 7:
    status_emoji, status_text, status_desc = "🌱", "새로운 만남", "서로 알아가는 중이야. 자주 들러줘"
elif days <= 30:
    status_emoji, status_text, status_desc = "🌿", "알아가는 중", "돌봄이 습관이 되고 있어. 좋은 신호야"
elif days <= 90:
    status_emoji, status_text, status_desc = "🪴", "함께하는 사이", f"{nickname}가 너의 하루 일부가 됐네"
else:
    status_emoji, status_text, status_desc = "🌳", "오랜 친구", f"이쯤 되면 {nickname}가 너를 돌보는 거야"

# ========================================
# 메인 타이틀 (동적 인사)
# ========================================
hour = datetime.now().hour
if hour < 9:
    main_title = f"좋은 아침.\n{nickname} 오늘도 잘 있을까?"
elif hour < 13:
    main_title = f"오늘은 {nickname}한테\n뭐 해줄 거야?"
elif hour < 18:
    main_title = f"{nickname}한테\n잠깐 들러볼까?"
else:
    main_title = f"오늘 하루 수고했어.\n{nickname}도 잘 있었을까?"

st.markdown(f"## {main_title}")

# 돌봄 공백 메시지
if care_logs:
    last_date = datetime.strptime(care_logs[-1]["date"][:10], "%Y-%m-%d")
    gap = (datetime.now() - last_date).days
    if gap == 0:
        boonz("happy", f"오늘도 {nickname} 챙겨주네. 이런 시간이 너한테도 좋은 거야")
    elif gap == 1:
        last_act = ACTION_LABELS.get(care_logs[-1].get("action", ""), "")
        boonz("default", f"어제 {last_act} 해줬지? 꾸준한 거 좋다")
    elif gap <= 3:
        boonz("default", f"{gap}일 만이네. {nickname} 보고 싶었을걸")
    else:
        boonz("worried", f"{gap}일째야. 바쁜 거 알지만, {nickname} 좀 봐줘")
else:
    boonz("default", "나와 식물 사이, 분즈가 통역해줄게")

# ========================================
# 성장 카드
# ========================================
species_text = current.get("species", "") or "종을 알아보려면 사진을 찍어줘"
streak_html = f'<div style="font-size:11px;color:#3B6D11;">🔥 {streak}일 연속 돌봄!</div>' if streak >= 3 else ""
meter_html = ""
meter_count = min(days // 23, 4)  # 0~4 단계
for i in range(4):
    color = "#3B6D11" if i < meter_count else "#E5E0D5"
    meter_html += f'<div style="width:14px;height:4px;border-radius:2px;background:{color};display:inline-block;margin:0 1px;"></div>'

st.markdown(
    f'<div style="background:linear-gradient(135deg,#EAF3DE 0%,#FFF9E6 100%);border-radius:20px;padding:16px;margin:8px 0;text-align:center;">'
    f'<div style="font-size:32px;margin:4px 0;">{status_emoji}</div>'
    f'<div style="font-size:16px;font-weight:700;color:#3B6D11;">{status_text}</div>'
    f'<div style="font-size:12px;color:#888780;">{nickname} · {species_text} · {days}일째</div>'
    f'<div style="margin:6px 0;">{meter_html}</div>'
    f'<div style="font-size:11px;color:#2C2C2A;font-style:italic;">"{status_desc}"</div>'
    f'{streak_html}'
    f'</div>',
    unsafe_allow_html=True,
)

# 이정표
if total_logs in MILESTONES:
    st.markdown(
        f'<div style="background:#FFF9E6;border-radius:12px;padding:8px 14px;margin:6px 0;'
        f'text-align:center;font-size:13px;color:#2C2C2A;">'
        f'🎉 {MILESTONES[total_logs].format(nickname)}</div>',
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
    uploaded = st.file_uploader("잎 사진을 올려줘", type=["jpg", "jpeg", "png"], key="diag", label_visibility="collapsed")

    if not uploaded:
        boonz("default", f"{nickname} 사진 줘. 내가 봐줌")

    if uploaded:
        boonz("loading", "잠깐, 얘 얘기 좀 들어보고 있어...")
        try:
            files = {"file": (uploaded.name, uploaded.getvalue(), uploaded.type)}
            resp = requests.post(f"{FASTAPI_URL}/diagnose", files=files, data={"nickname": nickname})
            result = resp.json()

            # 이미지 비교
            col1, col2 = st.columns(2)
            with col1:
                st.image(uploaded, caption="원본", use_container_width=True)
            with col2:
                overlay = result.get("overlay_image")
                if overlay:
                    import base64
                    st.image(base64.b64decode(overlay), caption="SAM 분석", use_container_width=True)

            # 결과 카드
            disease = result.get("disease", {})
            lesion = result.get("lesion", {})
            species_info = result.get("species", {})
            ratio = lesion.get("ratio", 0) * 100
            disease_kr = DISEASE_KOREAN.get(disease.get("name", ""), disease.get("korean", disease.get("name", "")))

            # 병변별 메시지
            if ratio <= 5:
                severity_text = "건강해 보여"
                severity_color = "#97C459"
            elif ratio <= 10:
                severity_text = "초기 — 지금 잡으면 돼"
                severity_color = "#97C459"
            elif ratio <= 25:
                severity_text = "중기 — 관심이 필요해"
                severity_color = "#EF9F27"
            else:
                severity_text = "후기 — 적극적인 케어 필요"
                severity_color = "#E24B4A"

            st.markdown(
                f'<div style="background:white;border-radius:20px;padding:16px;box-shadow:0 2px 8px rgba(0,0,0,0.04);margin:8px 0;">'
                f'<div style="font-size:16px;font-weight:700;color:#2C2C2A;">{nickname}가 좀 아프대</div>'
                f'<div style="font-size:13px;color:#888780;margin:4px 0;">{disease_kr} · 신뢰도 {disease.get("confidence", 0):.0%}</div>'
                f'<div style="background:#E5E0D5;border-radius:6px;height:8px;margin:8px 0;overflow:hidden;">'
                f'<div style="width:{min(ratio, 100)}%;height:100%;background:{severity_color};border-radius:6px;"></div></div>'
                f'<div style="font-size:12px;color:#3B6D11;">{severity_text}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

            # 분즈 메시지
            b = result.get("boonz", {})
            boonz_mood = b.get("mood", "worried")
            boonz_msg = b.get("message", f"{nickname}한테 물어봤는데, 좀 힘들다고 해. 같이 돌보자")
            boonz(boonz_mood, boonz_msg)

            # 케어 가이드
            care = result.get("care_guide", {})
            if care.get("text"):
                st.markdown(
                    f'<div style="background:white;border-radius:16px;padding:14px;'
                    f'border-left:3px solid #3B6D11;margin:8px 0;color:#2C2C2A;font-size:13px;">'
                    f'{care["text"]}'
                    f'<div style="font-size:11px;color:#888780;margin-top:8px;font-style:italic;">'
                    f'네가 이렇게 신경 써주는 거, {nickname}한테 큰 힘이 될 거야</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
            if care.get("audio_url"):
                st.audio(care["audio_url"])

            # 진단 저장
            st.session_state.last_diagnosis = {"disease": disease.get("name", ""), "lesion": lesion.get("ratio", 0)}
            if species_info.get("name"):
                update_species(nickname, species_info["name"])

            # === 진단 후 바로 케어 기록 ===
            st.divider()
            st.markdown(f"**{nickname}한테 뭐 해줄 거야?**")
            care_cols = st.columns(4)
            care_actions_quick = {
                "💧 물줬음": "water", "☀️ 자리옮김": "move",
                "✂️ 가지치기": "prune", "💊 약줬음": "medicine",
                "🪴 분갈이": "repot", "🍃 잎닦음": "clean",
                "😊 그냥봄": "observe",
            }
            for i, (label, action) in enumerate(care_actions_quick.items()):
                with care_cols[i % 4]:
                    if st.button(label, key=f"t1_{action}", use_container_width=True):
                        save_care_log(nickname, action)
                        msg = random.choice(CARE_RESPONSES.get(action, ["{}한테 전해놨어!"])).format(nickname)
                        boonz("happy", msg)

        except Exception as e:
            boonz("worried", "앗 나 잠깐 버그남. 근데 괜찮아, 다시 해볼게")
            st.caption(str(e))

# ========================================
# Tab 2: 음성/텍스트 상담
# ========================================
with tab2:
    boonz("default", f"뭐가 궁금해? 내가 {nickname}한테 물어볼게")
    voice_tab, text_tab = st.tabs(["🎙️ 음성", "💬 텍스트"])

    with voice_tab:
        audio_file = st.file_uploader("음성 파일", type=["wav", "mp3", "m4a"], key="voice", label_visibility="collapsed")
        if audio_file:
            diagnosis_context = ""
            if "last_diagnosis" in st.session_state:
                d = st.session_state.last_diagnosis
                disease_kr = DISEASE_KOREAN.get(d.get("disease", ""), d.get("disease", ""))
                diagnosis_context = f"현재 {nickname}: {disease_kr}, 병변 {d.get('lesion', 0)*100:.0f}%"
            try:
                files = {"file": ("audio.wav", audio_file.getvalue(), "audio/wav")}
                resp = requests.post(f"{FASTAPI_URL}/consult/voice", files=files, data={"nickname": nickname, "diagnosis_context": diagnosis_context})
                result = resp.json()
                st.caption(f"내가 한 말: {result.get('transcript', '')}")
                b = result.get("boonz", {})
                boonz(b.get("mood", "happy"), b.get("message", ""))
                if result.get("answer", {}).get("audio_url"):
                    st.audio(result["answer"]["audio_url"])
            except:
                boonz("worried", "앗 나 잠깐 버그남. 근데 괜찮아, 다시 해볼게")

    with text_tab:
        if "chat_history" not in st.session_state:
            st.session_state.chat_history = []
        for chat in st.session_state.chat_history:
            if chat["role"] == "user":
                st.markdown(f'<div style="text-align:right;background:#EAF3DE;border-radius:12px 12px 4px 12px;padding:8px 12px;margin:4px 0 4px 60px;color:#2C2C2A;font-size:13px;">{chat["content"]}</div>', unsafe_allow_html=True)
            else:
                boonz("happy", chat["content"])
        question = st.text_input("질문", placeholder="예: 잎이 노랗게 변하는데 왜 그래?", key="q_text", label_visibility="collapsed")
        if question:
            st.session_state.chat_history.append({"role": "user", "content": question})
            diagnosis_context = ""
            if "last_diagnosis" in st.session_state:
                d = st.session_state.last_diagnosis
                disease_kr = DISEASE_KOREAN.get(d.get("disease", ""), d.get("disease", ""))
                diagnosis_context = f"현재 {nickname}: {disease_kr}, 병변 {d.get('lesion', 0)*100:.0f}%"
            try:
                resp = requests.post(f"{FASTAPI_URL}/consult/text", json={"question": question, "nickname": nickname, "diagnosis_context": diagnosis_context})
                result = resp.json()
                answer = result.get("boonz", {}).get("message", "")
                st.session_state.chat_history.append({"role": "boonz", "content": answer})
                st.rerun()
            except:
                boonz("worried", "앗 나 잠깐 버그남. 근데 괜찮아, 다시 해볼게")

# ========================================
# Tab 3: 약제 체크
# ========================================
with tab3:
    has_diagnosis = "last_diagnosis" in st.session_state
    uploaded_med = st.file_uploader("약제 라벨 찍어줘", type=["jpg", "jpeg", "png"], key="med", label_visibility="collapsed")

    if not uploaded_med and not has_diagnosis:
        boonz("default", f"먼저 {nickname} 사진을 찍어줘. 뭐가 필요한지 알아야 도와줄 수 있어")
    elif not uploaded_med:
        boonz("default", "뭐 사왔어? 보여줘")

    if uploaded_med:
        if not has_diagnosis:
            boonz("worried", f"약을 보기 전에 {nickname} 사진 먼저 찍어줘. 뭐가 아픈지 알아야 약을 판단할 수 있어")
        else:
            try:
                files = {"file": (uploaded_med.name, uploaded_med.getvalue(), uploaded_med.type)}
                resp = requests.post(f"{FASTAPI_URL}/medicine", files=files, data={"nickname": nickname})
                result = resp.json()
                for ing in result.get("ingredients", []):
                    st.markdown(f'<div style="background:white;border-radius:12px;padding:10px 14px;margin:4px 0;color:#2C2C2A;font-size:13px;">{ing["text"]} <span style="color:#888780;">({ing["confidence"]:.0%})</span></div>', unsafe_allow_html=True)
                b = result.get("boonz", {})
                boonz(b.get("mood", "default"), b.get("message", ""))
            except:
                boonz("worried", "앗 나 잠깐 버그남. 근데 괜찮아, 다시 해볼게")

# ========================================
# Tab 4: 케어 이력 (관계 중심)
# ========================================
with tab4:
    # --- 원터치 태그 ---
    st.markdown(f"**오늘 {nickname}한테 뭐 해줬어?**")
    care_actions = {"💧 물줬음": "water", "☀️ 자리옮김": "move", "✂️ 가지치기": "prune", "💊 약줬음": "medicine", "🪴 분갈이": "repot", "🍃 잎닦음": "clean", "😊 그냥봄": "observe"}
    cols = st.columns(4)
    for i, (label, action) in enumerate(care_actions.items()):
        with cols[i % 4]:
            if st.button(label, key=f"c_{action}", use_container_width=True):
                save_care_log(nickname, action)
                msg = random.choice(CARE_RESPONSES.get(action, ["{}한테 전해놨어!"])).format(nickname)
                boonz("happy", msg)
                st.rerun()

    # --- 관리 현황 ---
    action_counts = {}
    for log in care_logs:
        a = log.get("action", "")
        action_counts[a] = action_counts.get(a, 0) + 1

    for label, key in [("💧 물", "water"), ("💊 약", "medicine"), ("😊 관심", "observe")]:
        count = action_counts.get(key, 0)
        c1, c2, c3 = st.columns([2, 6, 1])
        with c1:
            st.caption(label)
        with c2:
            st.progress(min(count / 10, 1.0))
        with c3:
            st.caption(f"{count}번")

    st.divider()

    # --- 회복 여정 (병변 추이 대신) ---
    diagnosis_logs = [l for l in care_logs if l.get("lesion")]
    if len(diagnosis_logs) >= 2:
        st.markdown(f"### {nickname}와의 이야기")
        journey_html = '<div style="display:flex;align-items:flex-end;justify-content:center;gap:8px;margin:12px 0;">'
        for log in diagnosis_logs:
            emoji = get_recovery_emoji(log["lesion"])
            pct = f'{log["lesion"]*100:.0f}%'
            date = log["date"][:5]
            journey_html += f'<div style="text-align:center;font-size:11px;color:#888780;"><div style="font-size:20px;">{emoji}</div>{date}<br>{pct}</div>'
            if log != diagnosis_logs[-1]:
                journey_html += '<div style="font-size:12px;color:#E5E0D5;align-self:center;">→</div>'
        journey_html += '</div>'
        st.markdown(journey_html, unsafe_allow_html=True)

        if diagnosis_logs[-1]["lesion"] < diagnosis_logs[0]["lesion"]:
            boonz("happy", f"봐봐, {nickname} 너랑 있으면서 점점 좋아지고 있어. 너가 잘 돌봐준 거야")
        else:
            boonz("worried", f"{nickname}가 요즘 좀 힘들어하고 있어. 더 자주 들여다봐줄래?")

    st.divider()

    # --- 돌봄 일기 (타임라인) ---
    st.markdown(f"### 돌봄 일기")
    if care_logs:
        show_all = st.checkbox("전체 보기", key="timeline_all")
        display_logs = care_logs if show_all else care_logs[-5:]
        for log in reversed(display_logs):
            label = ACTION_LABELS.get(log["action"], log["action"])
            lesion_text = ""
            comment = ""
            if log.get("lesion"):
                lesion_text = f' — 병변 {log["lesion"]*100:.0f}%'
                if log["lesion"] <= 0.05:
                    comment = f" · {nickname}가 많이 나아졌대"
                elif log["lesion"] <= 0.1:
                    comment = " · 좋아지고 있어!"
                else:
                    comment = f" · 힘내자 {nickname}"
            st.markdown(
                f'<div style="background:white;padding:10px 14px;border-radius:12px;margin:4px 0;font-size:12px;color:#2C2C2A;">'
                f'{log["date"][:10]} — {label}{lesion_text}'
                f'<span style="color:#3B6D11;font-size:11px;">{comment}</span></div>',
                unsafe_allow_html=True,
            )
    else:
        boonz("default", f"아직 {nickname}이랑 기록이 없네. 위에 버튼 눌러봐. 하나만 눌러도 시작이야")

    st.divider()

    # --- Plotly (있으면) ---
    if len(diagnosis_logs) >= 2:
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=[l["date"][:10] for l in diagnosis_logs],
            y=[l["lesion"] * 100 for l in diagnosis_logs],
            mode="lines+markers",
            line=dict(color="#3B6D11", width=2),
            marker=dict(color="#3B6D11", size=8),
        ))
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(gridcolor="#E5E0D5"), yaxis=dict(gridcolor="#E5E0D5", title=""),
            font=dict(color="#5F5E5A"), height=200, margin=dict(l=40, r=20, t=10, b=40),
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # --- 패턴 분석 ---
    if st.button("🔍 돌봄 패턴 분석", use_container_width=True):
        if len(care_logs) >= 10:
            try:
                resp = requests.get(f"{FASTAPI_URL}/pattern/{nickname}")
                result = resp.json()
                # 돌봄 리포트
                lesion_logs = [l for l in care_logs if l.get("lesion")]
                decrease = ""
                if len(lesion_logs) >= 2:
                    decrease = f'{(lesion_logs[0]["lesion"] - lesion_logs[-1]["lesion"])*100:.0f}%'
                st.markdown(
                    f'<div style="background:linear-gradient(135deg,#EAF3DE,#FFF9E6);border-radius:16px;padding:16px;margin:8px 0;text-align:center;">'
                    f'<div style="font-size:13px;font-weight:600;color:#3B6D11;margin-bottom:8px;">돌봄 리포트</div>'
                    f'<div style="display:flex;justify-content:space-around;">'
                    f'<div><div style="font-size:20px;font-weight:700;color:#2C2C2A;">{total_logs}</div><div style="font-size:10px;color:#888780;">총 기록</div></div>'
                    f'<div><div style="font-size:20px;font-weight:700;color:#2C2C2A;">{streak}</div><div style="font-size:10px;color:#888780;">연속 돌봄</div></div>'
                    f'<div><div style="font-size:20px;font-weight:700;color:#3B6D11;">-{decrease}</div><div style="font-size:10px;color:#888780;">병변 감소</div></div>'
                    f'</div></div>',
                    unsafe_allow_html=True,
                )
                b = result.get("boonz", {})
                boonz(b.get("mood", "happy"), b.get("message", ""))
            except:
                boonz("worried", "앗 나 잠깐 버그남. 근데 괜찮아, 다시 해볼게")
        else:
            boonz("default", f"아직 기록이 {total_logs}개야. 조금만 더 쌓이면 패턴이 보일 거야")

    st.divider()

    # --- 식물 관리 ---
    with st.expander("🌱 식물 관리"):
        new_name = st.text_input("새 식물 별명", key="new_p", label_visibility="collapsed", placeholder="새 식물 별명 입력")
        if st.button("추가", key="add_p") and new_name:
            save_plant(new_name)
            st.rerun()
        st.divider()
        if st.button(f"🗑️ {nickname} 삭제", key="del_p"):
            delete_plant(nickname)
            st.rerun()
```
