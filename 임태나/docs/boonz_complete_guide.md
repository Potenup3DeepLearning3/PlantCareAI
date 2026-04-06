# Boonz UI 전체 수정 가이드 (Claude Code용)

이 문서의 모든 내용을 순서대로 적용해줘.
docs/brand-essence.md, docs/sprint-plan.md, docs/coding-order.md, docs/llm-prompt.md도 같이 읽어.

---

## 1단계: 전역 CSS (app.py 맨 상단, st.set_page_config 바로 다음)

기존 CSS 전부 지우고 이걸로 교체. !important 빠뜨리지 마.

```python
st.markdown("""
<style>
    /* === 전체 앱 === */
    .stApp, .main, .block-container {
        background: linear-gradient(180deg, #0a1a0a 0%, #050d05 100%) !important;
        color: #e0e0d0 !important;
    }
    
    /* === 모든 텍스트 === */
    .stApp p, .stApp span, .stApp label, .stApp div,
    .stApp li, .stApp td, .stApp th {
        color: #e0e0d0 !important;
    }
    
    /* === 제목 === */
    .stApp h1, .stApp h2, .stApp h3, .stApp h4 {
        color: #CCFF00 !important;
    }
    
    /* === 입력창 === */
    .stApp input, .stApp textarea {
        background-color: #1e2e1e !important;
        color: #e0e0d0 !important;
        border: 1px solid #CCFF00 !important;
    }
    .stApp input::placeholder, .stApp textarea::placeholder {
        color: #8a8a7a !important;
    }
    .stApp input:focus, .stApp textarea:focus {
        box-shadow: 0 0 15px rgba(204,255,0,0.2) !important;
    }
    
    /* === 셀렉트박스 === */
    .stApp [data-baseweb="select"],
    .stApp [data-baseweb="select"] * {
        background-color: #1e2e1e !important;
        color: #e0e0d0 !important;
        border-color: #2a3a2a !important;
    }
    
    /* === 드롭다운 메뉴 === */
    [data-baseweb="popover"], [data-baseweb="popover"] *,
    [data-baseweb="menu"], [data-baseweb="menu"] *,
    ul[role="listbox"], ul[role="listbox"] * {
        background-color: #1e2e1e !important;
        color: #e0e0d0 !important;
    }
    
    /* === 버튼 === */
    .stApp button {
        background-color: #1e2e1e !important;
        color: #CCFF00 !important;
        border: 1px solid #CCFF00 !important;
    }
    .stApp button:hover {
        box-shadow: 0 0 15px rgba(204,255,0,0.2) !important;
    }
    
    /* === 탭 === */
    .stApp [data-baseweb="tab-list"] {
        background-color: #1a2a1a !important;
    }
    .stApp [data-baseweb="tab"] {
        color: #8a8a7a !important;
    }
    .stApp [aria-selected="true"] {
        color: #CCFF00 !important;
        border-bottom-color: #CCFF00 !important;
    }
    
    /* === 파일 업로더 === */
    .stApp [data-testid="stFileUploader"],
    .stApp [data-testid="stFileUploader"] * {
        color: #e0e0d0 !important;
        background-color: #1e2e1e !important;
        border-color: #2a3a2a !important;
    }
    
    /* === 라디오 버튼 === */
    .stApp [role="radiogroup"] label {
        color: #e0e0d0 !important;
    }
    
    /* === 구분선 === */
    .stApp hr {
        border-color: #2a3a2a !important;
    }
    
    /* === 익스팬더 === */
    .stApp [data-testid="stExpander"] {
        background-color: #1e2e1e !important;
        border: 1px solid #2a3a2a !important;
    }
    .stApp [data-testid="stExpander"] summary {
        color: #e0e0d0 !important;
    }
    
    /* === 사이드바 === */
    [data-testid="stSidebar"],
    [data-testid="stSidebar"] > div {
        background: linear-gradient(180deg, #0a1a0a 0%, #050d05 100%) !important;
    }
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] div,
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: #e0e0d0 !important;
    }
    [data-testid="stSidebar"] input {
        background-color: #1e2e1e !important;
        color: #e0e0d0 !important;
        border: 1px solid #CCFF00 !important;
    }
    [data-testid="stSidebar"] [data-baseweb="select"],
    [data-testid="stSidebar"] [data-baseweb="select"] * {
        background-color: #1e2e1e !important;
        color: #e0e0d0 !important;
    }
    [data-testid="stSidebar"] button {
        background-color: #1e2e1e !important;
        color: #FF6B6B !important;
        border: 1px solid #FF6B6B !important;
    }
    
    /* === 스크롤바 === */
    ::-webkit-scrollbar { width: 8px; }
    ::-webkit-scrollbar-track { background: #0a1a0a; }
    ::-webkit-scrollbar-thumb { background: #2a3a2a; border-radius: 4px; }
    
    /* === 분즈 애니메이션 === */
    @keyframes float {
        0%, 100% { transform: translateY(0px); }
        50% { transform: translateY(-8px); }
    }
    @keyframes shake {
        0%, 100% { transform: rotate(0deg); }
        25% { transform: rotate(-5deg); }
        75% { transform: rotate(5deg); }
    }
    @keyframes bounce {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-15px); }
    }
    .boonz-happy, .boonz-default { animation: float 3s ease-in-out infinite; }
    .boonz-worried { animation: shake 0.5s ease-in-out infinite; }
    .boonz-sad { animation: float 4s ease-in-out infinite; opacity: 0.8; }
    .boonz-loading { animation: bounce 0.6s ease-in-out infinite; }
</style>
""", unsafe_allow_html=True)
```

---

## 2단계: animated_boonz 함수 (기존 함수 교체)

```python
import base64
from pathlib import Path

def animated_boonz(mood="default", message=""):
    """분즈 캐릭터 + 말풍선 표시. 이미지 없으면 이모지 폴백."""
    assets = Path(__file__).parent / "assets"
    img_path = assets / f"boonz_{mood}.png"
    
    # loading은 default 이미지 사용
    if mood == "loading" and not img_path.exists():
        img_path = assets / "boonz_default.png"
    
    if img_path.exists():
        with open(img_path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode()
        img_html = f'''<img src="data:image/png;base64,{img_b64}" 
            class="boonz-{mood}" 
            style="width:100px; border-radius:20px; border:2px solid #CCFF00; 
                   box-shadow: 0 0 20px rgba(204,255,0,0.15);">'''
    else:
        emoji = {"happy": "😊🥦", "worried": "😟🥦", "sad": "😢🥦", "loading": "⏳🥦"}.get(mood, "🥦")
        img_html = f'<div class="boonz-{mood}" style="font-size:50px;text-align:center;">{emoji}</div>'
    
    col1, col2 = st.columns([1, 4])
    with col1:
        st.markdown(img_html, unsafe_allow_html=True)
    with col2:
        if message:
            st.markdown(f"""
            <div style="
                background: #1e2e1e;
                border: 1px solid #CCFF00;
                border-radius: 16px 16px 16px 4px;
                padding: 12px 16px;
                color: #e0e0d0;
                box-shadow: 0 0 15px rgba(204, 255, 0, 0.1);
                margin-top: 8px;
                font-size: 15px;
            ">
                {message}
            </div>
            """, unsafe_allow_html=True)
```

---

## 3단계: 식물 등록 + plants.json CRUD

```python
import json
from datetime import datetime

PLANTS_FILE = Path("data/plants.json")

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

def get_nickname():
    """현재 선택된 식물 별명 반환"""
    return st.session_state.get("current_plant", "식물")
```

---

## 4단계: 원터치 케어 로그

```python
CARE_LOG_FILE = Path("data/care_log.jsonl")

def save_care_log(nickname, action):
    entry = {
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "plant": nickname,
        "action": action
    }
    # 마지막 진단 결과가 있으면 같이 저장
    if "last_diagnosis" in st.session_state:
        diag = st.session_state.last_diagnosis
        entry["disease"] = diag.get("disease", "")
        entry["lesion"] = diag.get("lesion", 0)
    
    CARE_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CARE_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

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
```

---

## 5단계: 앱 구조 (온보딩 → 사이드바 → 4탭)

```python
import streamlit as st
import requests
import json
import plotly.graph_objects as go
from pathlib import Path
from datetime import datetime

st.set_page_config(page_title="Boonz", layout="wide", page_icon="🥦")

# === 1단계 CSS 여기에 삽입 ===
# === 2단계 animated_boonz 함수 여기에 삽입 ===
# === 3단계 plants.json 함수 여기에 삽입 ===
# === 4단계 케어 로그 함수 여기에 삽입 ===

FASTAPI_URL = "http://localhost:8000"
plants = load_plants()

# ========================================
# 온보딩: 식물 미등록 시
# ========================================
if not plants:
    st.markdown("# 🌿 Boonz")
    st.markdown("##### 나와 식물 사이, 분즈가 통역해줄게")
    animated_boonz("default", "식물 별명 하나 지어줘. 그게 시작이야")
    
    nickname_input = st.text_input("별명을 입력해줘 (예: 초록이, 마리)")
    if nickname_input:
        save_plant(nickname_input)
        st.session_state.current_plant = nickname_input
        animated_boonz("happy", f"{nickname_input}? 잘 부탁해")
        st.rerun()
    
    st.stop()  # 여기서 멈춤. 아래 탭은 안 보임.

# ========================================
# 사이드바: 식물 관리
# ========================================
with st.sidebar:
    st.markdown("### 🌱 내 식물")
    
    plant_names = [p["nickname"] for p in plants]
    selected = st.selectbox(
        "선택", 
        plant_names, 
        index=0,
        label_visibility="collapsed"
    )
    st.session_state.current_plant = selected
    nickname = selected
    
    # 등록된 식물 정보
    current = next((p for p in plants if p["nickname"] == nickname), {})
    species_text = current.get("species", "아직 모름")
    st.markdown(f"종: {species_text}")
    st.markdown(f"등록일: {current.get('registered', '')}")
    
    st.divider()
    
    # 새 식물 추가
    with st.expander("새 식물 추가"):
        new_name = st.text_input("별명", key="new_plant")
        if st.button("추가") and new_name:
            save_plant(new_name)
            st.rerun()
    
    # 삭제
    if st.button("현재 식물 삭제", type="secondary"):
        delete_plant(nickname)
        st.rerun()

# ========================================
# 메인: 4탭
# ========================================
st.markdown(f"# 🥦 Boonz")
st.markdown("##### 나와 식물 사이, 분즈가 통역해줄게")

tab1, tab2, tab3, tab4 = st.tabs(["📷 사진 진단", "🎙️ 음성 상담", "💊 약제 체크", "📊 케어 이력"])

# ========================================
# Tab 1: 사진 진단
# ========================================
with tab1:
    uploaded = st.file_uploader("잎 사진", type=["jpg", "jpeg", "png"], key="diagnose")
    
    if not uploaded:
        animated_boonz("default", f"{nickname} 사진 줘. 내가 봐줌")
    
    if uploaded:
        animated_boonz("loading", "잠깐, 얘 얘기 좀 들어보고 있어...")
        
        try:
            files = {"file": (uploaded.name, uploaded.getvalue(), uploaded.type)}
            response = requests.post(
                f"{FASTAPI_URL}/diagnose",
                files=files,
                data={"nickname": nickname}
            )
            result = response.json()
            
            # SAM 오버레이 (좌: 원본, 우: 오버레이)
            col1, col2 = st.columns(2)
            with col1:
                st.image(uploaded, caption="원본", use_container_width=True)
            with col2:
                if result.get("overlay_image"):
                    # base64 디코딩해서 표시
                    import base64 as b64
                    overlay_bytes = b64.b64decode(result["overlay_image"])
                    st.image(overlay_bytes, caption="SAM 분석", use_container_width=True)
            
            # 진단 결과 카드
            disease = result.get("disease", {})
            lesion = result.get("lesion", {})
            species_info = result.get("species", {})
            ratio = lesion.get("ratio", 0) * 100
            
            # 프로그레스 바 색상 분기
            if ratio <= 10:
                bar_color = "#CCFF00"
            elif ratio <= 25:
                bar_color = "#FFD93D"
            else:
                bar_color = "#FF6B6B"
            
            st.markdown(f"""
            <div style="background:#1e2e1e; border:1px solid #2a3a2a; border-radius:4px 24px 4px 24px; padding:16px; margin:8px 0;">
                <div style="color:#CCFF00; font-weight:500; font-size:16px;">{nickname}: {species_info.get('name', '?')}</div>
                <div style="color:#e0e0d0; margin:4px 0;">증상: {disease.get('korean', '?')} ({disease.get('confidence', 0):.0%})</div>
                <div style="background:#0a1a0a; border-radius:8px; height:20px; margin:8px 0; overflow:hidden;">
                    <div style="background:{bar_color}; width:{ratio}%; height:100%; border-radius:8px; transition:width 0.5s;"></div>
                </div>
                <div style="color:#8a8a7a;">병변 {ratio:.1f}% — {lesion.get('severity', '?')}</div>
            </div>
            """, unsafe_allow_html=True)
            
            # 분즈 메시지 (병변% 분기)
            boonz = result.get("boonz", {})
            animated_boonz(boonz.get("mood", "default"), boonz.get("message", ""))
            
            # 케어 가이드 + TTS
            care = result.get("care_guide", {})
            if care.get("text"):
                st.markdown(f"""
                <div style="background:#1e2e1e; border-left:3px solid #CCFF00; padding:12px 16px; margin:8px 0; border-radius:0 8px 8px 0; color:#e0e0d0;">
                    {care['text']}
                </div>
                """, unsafe_allow_html=True)
            if care.get("audio_url"):
                st.audio(care["audio_url"])
            
            # 진단 결과 저장 (session_state + species 업데이트)
            st.session_state.last_diagnosis = {
                "disease": disease.get("name", ""),
                "lesion": lesion.get("ratio", 0)
            }
            if species_info.get("name"):
                update_species(nickname, species_info["name"])
        
        except Exception as e:
            animated_boonz("worried", "앗 나 버그남. 다시 해볼게")
            st.error(str(e))

# ========================================
# Tab 2: 음성 상담
# ========================================
with tab2:
    animated_boonz("default", f"뭐가 궁금해? 내가 {nickname}한테 물어볼게")
    
    input_mode = st.radio("입력 방식", ["🎙️ 음성", "💬 텍스트"], horizontal=True, label_visibility="collapsed")
    
    if input_mode == "🎙️ 음성":
        audio = st.audio_input("말해봐")
        if audio:
            try:
                files = {"file": ("audio.wav", audio.getvalue(), "audio/wav")}
                response = requests.post(
                    f"{FASTAPI_URL}/consult/voice",
                    files=files,
                    data={"nickname": nickname}
                )
                result = response.json()
                
                st.markdown(f"**내가 한 말:** {result.get('transcript', '')}")
                
                boonz = result.get("boonz", {})
                animated_boonz(boonz.get("mood", "happy"), boonz.get("message", ""))
                
                if result.get("answer", {}).get("audio_url"):
                    st.audio(result["answer"]["audio_url"])
            except Exception as e:
                animated_boonz("worried", "앗 나 버그남. 다시 해볼게")
    
    else:
        question = st.text_input("궁금한 거 적어봐", key="consult_text")
        if question:
            try:
                response = requests.post(
                    f"{FASTAPI_URL}/consult/text",
                    json={"question": question, "nickname": nickname}
                )
                result = response.json()
                
                boonz = result.get("boonz", {})
                animated_boonz(boonz.get("mood", "happy"), boonz.get("message", ""))
                
                if result.get("answer", {}).get("audio_url"):
                    st.audio(result["answer"]["audio_url"])
            except Exception as e:
                animated_boonz("worried", "앗 나 버그남. 다시 해볼게")

# ========================================
# Tab 3: 약제 체크
# ========================================
with tab3:
    uploaded_med = st.file_uploader("약제 라벨", type=["jpg", "jpeg", "png"], key="medicine")
    
    if not uploaded_med:
        animated_boonz("default", "뭐 사왔어? 보여줘")
    
    if uploaded_med:
        try:
            files = {"file": (uploaded_med.name, uploaded_med.getvalue(), uploaded_med.type)}
            response = requests.post(
                f"{FASTAPI_URL}/medicine",
                files=files,
                data={"nickname": nickname}
            )
            result = response.json()
            
            # OCR 추출 결과
            for ing in result.get("ingredients", []):
                st.markdown(f"""
                <div style="background:#1e2e1e; padding:8px 12px; margin:4px 0; border-radius:8px; color:#e0e0d0;">
                    {ing['text']} <span style="color:#8a8a7a;">(확신도: {ing['confidence']:.0%})</span>
                </div>
                """, unsafe_allow_html=True)
            
            # 분즈 메시지
            boonz = result.get("boonz", {})
            animated_boonz(boonz.get("mood", "default"), boonz.get("message", ""))
        
        except Exception as e:
            animated_boonz("worried", "앗 나 버그남. 다시 해볼게")

# ========================================
# Tab 4: 케어 이력
# ========================================
with tab4:
    st.markdown(f"### 🌱 {nickname}")
    
    # --- 원터치 케어 로그 ---
    st.markdown(f"오늘 {nickname}한테 뭐 해줬어?")
    
    care_actions = {
        "💧 물 줬음": "water",
        "☀️ 자리 옮김": "move",
        "✂️ 가지치기": "prune",
        "💊 약 줬음": "medicine",
        "🪴 분갈이": "repot",
        "🍃 잎 닦음": "clean",
        "😊 그냥 봄": "observe",
    }
    
    cols = st.columns(4)
    for i, (label, action) in enumerate(care_actions.items()):
        with cols[i % 4]:
            if st.button(label, key=f"care_{action}"):
                save_care_log(nickname, action)
                animated_boonz("happy", f"{nickname}한테 전해놨어!")
    
    st.divider()
    
    # --- 통합 타임라인 ---
    care_logs = load_care_log(nickname)
    
    action_emoji = {
        "water": "💧 물 줬음",
        "move": "☀️ 자리 옮김",
        "prune": "✂️ 가지치기",
        "medicine": "💊 약 줬음",
        "repot": "🪴 분갈이",
        "clean": "🍃 잎 닦음",
        "observe": "😊 그냥 봄",
    }
    
    if care_logs:
        st.markdown("#### 타임라인")
        for log in reversed(care_logs[-20:]):  # 최근 20개
            emoji = action_emoji.get(log["action"], log["action"])
            lesion_text = ""
            if log.get("lesion"):
                lesion_text = f" — 병변 {log['lesion']*100:.0f}%"
            st.markdown(f"""
            <div style="background:#1e2e1e; padding:8px 12px; margin:4px 0; border-radius:8px; color:#e0e0d0;">
                {log['date']} — {emoji}{lesion_text}
            </div>
            """, unsafe_allow_html=True)
    else:
        animated_boonz("default", f"아직 {nickname}이랑 기록이 없네. 위에 버튼 눌러봐")
    
    st.divider()
    
    # --- Plotly 추세선 차트 ---
    diagnosis_logs = [log for log in care_logs if log.get("lesion")]
    
    if len(diagnosis_logs) >= 2:
        st.markdown("#### 병변 추이")
        dates = [log["date"] for log in diagnosis_logs]
        ratios = [log["lesion"] * 100 for log in diagnosis_logs]
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=dates,
            y=ratios,
            mode='lines+markers',
            line=dict(color='#CCFF00', width=2),
            marker=dict(color='#CCFF00', size=8),
            name='병변 면적 %'
        ))
        fig.update_layout(
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(gridcolor='#2a3a2a', color='#8a8a7a'),
            yaxis=dict(gridcolor='#2a3a2a', color='#8a8a7a', title='병변 %'),
            font=dict(color='#e0e0d0'),
            height=300,
            margin=dict(l=40, r=20, t=20, b=40),
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)
    elif len(diagnosis_logs) == 1:
        animated_boonz("default", "진단 기록이 하나 더 쌓이면 추세선이 보여")
    
    st.divider()
    
    # --- 돌봄 패턴 분석 ---
    if st.button("🔍 돌봄 패턴 분석"):
        if len(care_logs) >= 10:
            try:
                response = requests.get(f"{FASTAPI_URL}/pattern/{nickname}")
                result = response.json()
                boonz = result.get("boonz", {})
                animated_boonz(boonz.get("mood", "happy"), boonz.get("message", ""))
            except Exception as e:
                animated_boonz("worried", "앗 나 버그남. 다시 해볼게")
        else:
            animated_boonz("default", f"아직 기록이 {len(care_logs)}개야. 조금만 더 쌓아줘")
```

---

## 6단계: FastAPI 엔드포인트 추가 (src/api/main.py)

기존 /diagnose, /consult, /medicine에 추가:

```python
@app.post("/api/care-log")
async def add_care_log(nickname: str, action: str):
    """원터치 케어 로그 저장"""
    # care_log.jsonl에 1줄 추가
    return {"saved": True, "boonz": {"mood": "happy", "message": f"{nickname}한테 전해놨어!"}}

@app.get("/api/timeline/{nickname}")
async def get_timeline(nickname: str):
    """통합 타임라인 (진단 + 케어 합산, 날짜순)"""
    # care_log.jsonl + diagnosis_history.jsonl 합쳐서 반환
    return {"entries": [...]}

@app.get("/api/pattern/{nickname}")
async def analyze_pattern(nickname: str):
    """돌봄 패턴 분석 (Ollama 로그 분석)"""
    # care_log.jsonl 전체를 Ollama pattern 프롬프트에 넣기
    return {"boonz": {"mood": "happy", "message": "분석 결과..."}}

@app.post("/api/plants")
async def register_plant(nickname: str):
    """식물 등록"""
    return {"nickname": nickname, "boonz": {"mood": "happy", "message": f"{nickname}? 잘 부탁해"}}

@app.get("/api/plants")
async def list_plants():
    """등록된 식물 목록"""
    return {"plants": [...]}

# 모든 응답에 boonz: {mood, message} 포함할 것
```

---

## 7단계: LLM 프롬프트 v2 (src/inference/llm.py)

docs/llm-prompt.md 읽고 적용.
핵심 변경:
- "식물 건강 전문가" → "분즈" 페르소나
- 존댓말 → 반말 (시크한 톤)
- 식물 별명 연동 ({plant_nickname})
- 케어 로그 컨텍스트 ({recent_care_log})
- 프롬프트 5종: care_guide, medicine, consult, pattern, greeting
- 3자 대화 구조: "초록이한테 물어봤는데", "초록이가 그러는데"

---

## 분즈 메시지 전체 목록

### Tab 1 사진 진단
- 업로드 전: "{nickname} 사진 줘. 내가 봐줌"
- 로딩 중: "잠깐, 얘 얘기 좀 들어보고 있어..."
- 병변 0~10%: "{nickname}한테 물어봤는데, 요즘 컨디션 좋대"
- 병변 10~25%: "{nickname}가 좀 힘들다는데? 약 좀 사다줘"
- 병변 25%+: "{nickname}가 많이 아프대... 빨리 도와줘야 할 거 같아"

### Tab 2 음성 상담
- 대기 중: "뭐가 궁금해? 내가 {nickname}한테 물어볼게"
- 응답 시: "{nickname}한테 물어봤어. " + LLM 답변

### Tab 3 약제 체크
- 업로드 전: "뭐 사왔어? 보여줘"
- 적합: "{nickname}한테 보여줬는데, 이거 괜찮대"
- 부적합: "{nickname}가 이건 별로래. 다른 거 찾아보자"

### Tab 4 케어 이력
- 케어 로그 후: "{nickname}한테 전해놨어!"
- 회복 추세: "봐봐, {nickname} 너랑 있으면서 점점 좋아지고 있어!"
- 악화 추세: "{nickname}가 요즘 좀 힘들어하고 있어. 더 자주 들여다봐줄래?"
- 이력 없음: "아직 {nickname}이랑 기록이 없네. 위에 버튼 눌러봐"
- 패턴 분석: "{nickname}가 그러는데, 너가 물 주는 타이밍 딱 좋대"
- 기록 부족: "아직 기록이 {n}개야. 조금만 더 쌓아줘"

### 공통
- 에러 시: "앗 나 버그남. 다시 해볼게"

### 규칙
- 분즈는 직접 판단하지 않고 "{nickname}한테 물어봤는데", "{nickname}가 그러는데" 형태로 전달
- 유저 ↔ 분즈 ↔ 식물, 3자 대화 구조
- 빈 화면 없음. 모든 상태에서 분즈가 한마디씩
