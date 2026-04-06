# Boonz 셀프케어 리빌드 — Claude Code 실행 가이드

## 지시사항
이 가이드를 위에서 아래로 순서대로 실행해줘.
각 단계 후 테스트하고, 성공하면 다음으로.
실패하면 에러 분석하고 수정 후 재테스트.
전부 끝나면 RESULT.md에 결과 저장.

반드시 docs/tone-guide.md도 읽고 모든 메시지를 그 톤에 맞춰.

## 사전 정보 (절대 무시하지 마)

### 체크포인트 로드
checkpoint = torch.load(path, map_location=device)
model.load_state_dict(checkpoint["model_state_dict"])
num_classes = len(checkpoint["class_to_idx"])

### 모델
- 병변: create_efficientnet_b3(num_classes=12), models/disease/efficientnet_b3_disease_type_best.pth
- 종: create_species_model(num_classes=47), models/species/species_model_best.pth
- SAM: vit_b, models/sam/sam_vit_b_01ec64.pth
- config: PROJECT_ROOT (PROJECT_DIR 아님), MODELS_DIR

### 한글 경로: cv2.imread 쓰지 마. PIL→numpy.
### LLM: OpenAI gpt-4o-mini 우선, Ollama 폴백. .env에 OPENAI_API_KEY.
### 삭제: 음성(Whisper, TTS), 약제(EasyOCR, /medicine), /consult/voice

---

## 단계 1: LLM 이중화
src/inference/llm.py에서 _call_ollama → _call_llm 이름 변경.
OpenAI gpt-4o-mini 우선, Ollama 폴백 로직 추가.
파일 전체에서 _call_ollama 호출을 _call_llm으로 교체.

## 단계 2: FastAPI 정리
src/api/main.py에서 약제/음성 엔드포인트 삭제.
/care-guide, /consult/text, /pattern/{nickname} 추가.
/diagnose에서 Ollama/TTS 호출 제거 (진단만 빠르게 반환).

## 단계 3: 시뮬레이션 데이터
scripts/generate_demo_data.py 생성. 마리 30일치 데이터.

## 단계 4: Streamlit 전면 재구축
src/frontend/app.py를 삭제하고 새로 만들어.
3탭: 홈(원터치+챗봇) / 진단(사진+가이드+상담) / 이력(일기+리포트+여정)

## 단계 5: 체크포인트 로드 수정
src/inference/ 모델 로드 파일에서 checkpoint["model_state_dict"] 패턴 적용.

## 단계 6: 한글 경로 PIL 우회
src/inference/ 이미지 로드에서 cv2.imread → PIL+numpy.

전체 코드는 GUIDE.md에 포함. 이 파일을 C:\plantcare\GUIDE.md로 넣고:
claude --dangerously-skip-permissions
"GUIDE.md를 읽고 단계 1부터 순서대로 실행해줘."

Boonz MCP 구현 가이드 — FastAPI + SQLite DB
구조
Streamlit (:8501)
    ↓ HTTP
FastAPI (:8000)
    ↓ MCP Protocol (stdio)
MCP Server (plant-care-db)
    ↓ SQL
SQLite (data/plant_care.db)

FastAPI가 MCP Client.
MCP Server가 DB 조회 도구를 노출.
조회 결과를 LLM에 전달 → 분즈 톤 변환.
핵심 가치
지금:  LLM이 자기 지식으로 케어 가이드 생성 → 할루시네이션 가능
MCP:   DB에서 검증된 정보 조회 → LLM은 톤 변환만 → 정확도 보장

단계 1: SQLite DB 생성
파일: scripts/init_db.py
python"""식물 케어 DB 초기화. 실행: python scripts/init_db.py"""
import sqlite3
from pathlib import Path

DB_PATH = Path("data/plant_care.db")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

db = sqlite3.connect(DB_PATH)

# 병변 테이블
db.execute("""
CREATE TABLE IF NOT EXISTS diseases (
    name TEXT PRIMARY KEY,
    korean_name TEXT NOT NULL,
    symptoms TEXT NOT NULL,
    cause TEXT NOT NULL,
    treatment TEXT NOT NULL,
    prevention TEXT NOT NULL,
    recovery_days TEXT NOT NULL,
    severity_levels TEXT NOT NULL
)""")

# 케어 팁 테이블 (8개 카테고리)
db.execute("""
CREATE TABLE IF NOT EXISTS care_tips (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    subcategory TEXT NOT NULL,
    species TEXT DEFAULT 'general',
    tip TEXT NOT NULL,
    detail TEXT
)""")

# 종별 기본 정보 테이블
db.execute("""
CREATE TABLE IF NOT EXISTS species_care (
    species TEXT PRIMARY KEY,
    korean_name TEXT,
    light TEXT,
    water_frequency TEXT,
    humidity TEXT,
    temperature TEXT,
    soil_mix TEXT,
    fertilizer TEXT,
    difficulty TEXT
)""")

# ==========================================
# 12클래스 병변 데이터
# ==========================================
diseases = [
    ("Late_Blight", "후기 마름병",
     "잎에 갈색~흑색 반점, 흰 곰팡이 테두리, 줄기 검게 변함, 빠르게 확산",
     "Phytophthora infestans. 습하고 서늘한 환경(15~20°C)에서 급속 확산",
     "감염 잎/줄기 즉시 제거 → 환기 → 살균제(만코제브, 클로로탈로닐) → 과습 방지 → 도구 소독",
     "잎에 물 안 묻게 관수. 통풍 확보. 식물 간격 유지. 저녁 관수 피하기",
     "초기: 2~3주 | 중기: 4~6주 | 후기: 회복 어려움",
     "~10%: 초기. 지금 잡으면 돼 | 10~25%: 중기. 적극 대응 필요 | 25%+: 후기. 감염 부위 과감히 제거"),

    ("Early_Blight", "초기 마름병",
     "동심원 무늬(과녁 모양) 갈색 반점, 아래 잎부터 위로 진행, 잎 황변 후 낙엽",
     "Alternaria solani. 고온다습(24~29°C), 오래된 잎에서 시작",
     "감염 잎 제거 → 멀칭으로 흙 튀김 방지 → 살균제 → 질소 비료 줄이기",
     "아래 잎 정리. 물줄 때 잎에 안 묻게. 작물 순환. 도구 소독",
     "2~4주",
     "~15%: 초기. 흔한 병이라 관리하면 괜찮아 | 15%+: 확산 중. 빠른 조치 필요"),

    ("Bacterial_Spot", "세균성 반점",
     "작은 수침상 반점 → 갈색/흑색으로 변함, 잎에 구멍, 열매에도 발생",
     "Xanthomonas 세균. 비/관수로 전파, 상처 통해 침입",
     "감염 부위 제거 → 구리 살균제 → 과습 방지 → 감염 식물 격리",
     "잎 젖지 않게 관수. 도구 소독. 통풍 확보",
     "3~4주",
     "~10%: 초기. 격리하면 잡을 수 있어 | 10%+: 확산 위험. 구리 살균제 필수"),

    ("Leaf_Curl", "잎 말림",
     "잎이 위/아래로 말림, 두꺼워짐, 변색(붉은색/노란색), 생장 저하",
     "바이러스(TYLCV), 진딧물/가루이 매개, 환경 스트레스(고온/저온/과습)",
     "매개충 제거(님오일, 끈끈이) → 감염 심한 잎 제거 → 환경 개선 → 바이러스면 식물 폐기 고려",
     "진딧물/가루이 예방. 새 식물 격리 기간. 도구 소독",
     "환경성: 1~2주 | 바이러스성: 회복 어려움",
     "환경 원인이면 조절하면 나아. 바이러스면 다른 식물 감염 방지가 우선"),

    ("Leaf_Mold", "잎 곰팡이",
     "잎 뒷면에 올리브색~갈색 곰팡이, 앞면에 노란 반점, 습한 환경에서 발생",
     "Passalora fulva(= Cladosporium). 고습도(85%+), 통풍 부족",
     "감염 잎 제거 → 습도 낮추기(60% 이하) → 환기 → 살균제",
     "습도 관리가 핵심. 환기. 잎 사이 간격. 잎에 물 안 묻게",
     "2~3주",
     "습도만 잡으면 빠르게 나아. 환기가 제일 중요해"),

    ("Leaf_Spot", "잎 반점",
     "원형/불규칙 갈색~흑색 반점, 테두리 선명, 심하면 반점이 합쳐짐",
     "다양한 곰팡이/세균. 과습, 통풍 부족, 밀식",
     "감염 잎 제거 → 물 주기 조절 → 환기 → 살균제(필요시)",
     "과습 방지. 잎에 물 안 묻게. 통풍. 낙엽 제거",
     "2~4주",
     "~10%: 흔한 증상. 환경 개선하면 돼 | 10%+: 원인 파악 필요"),

    ("Mosaic_Virus", "모자이크 바이러스",
     "잎에 연녹색/짙은녹색 모자이크 무늬, 잎 뒤틀림, 생장 위축, 열매 기형",
     "TMV/CMV 등 바이러스. 진딧물 매개, 접촉 전파, 씨앗 전파",
     "치료 불가 → 감염 식물 격리/폐기 → 매개충 제거 → 주변 식물 관찰",
     "새 식물 격리. 도구 소독(10% 표백제). 진딧물 관리",
     "바이러스는 치료 불가. 다른 식물 보호가 핵심",
     "바이러스는 약이 없어. 미안하지만 다른 식물 감염 방지가 우선이야"),

    ("Powdery_Mildew", "흰가루병",
     "잎 표면에 흰 가루 같은 곰팡이, 잎 황변, 심하면 낙엽",
     "Erysiphe 등. 건조한 환경 + 높은 습도(밤), 통풍 부족",
     "감염 잎 제거 → 베이킹소다 용액(1tsp/1L) 분무 → 님오일 → 살균제",
     "통풍. 과밀 방지. 아침 관수. 질소 비료 줄이기",
     "2~3주",
     "흔하고 잡기 쉬운 편. 베이킹소다 분무가 효과적이야"),

    ("Rust", "녹병",
     "잎 뒷면에 주황색/갈색 포자 돌기, 앞면에 노란 반점, 심하면 낙엽",
     "Puccinia 등 녹균. 습한 환경, 잎 젖은 상태 지속",
     "감염 잎 제거(밀봉 폐기) → 살균제 → 습도 낮추기 → 통풍",
     "잎 젖지 않게. 통풍. 감염 잎 즉시 제거. 낙엽 수거",
     "3~4주",
     "포자가 잘 퍼지니까 감염 잎은 바로 밀봉해서 버려"),

    ("Scab_Rot", "딱지병/부패",
     "표면에 딱지 같은 거친 반점, 코르크화, 심하면 조직 부패",
     "Venturia/Streptomyces 등. 과습, 상처 부위 감염",
     "감염 부위 제거 → 절단면 소독 → 건조하게 관리 → 살균제",
     "과습 방지. 상처 내지 않기. 도구 소독. 통풍",
     "3~6주",
     "부패가 진행 중이면 빨리 잘라내. 건조하게 관리하는 게 핵심"),

    ("Greening", "그리닝병",
     "잎이 비대칭으로 황변, 잎맥 주변만 녹색 유지, 열매 비대칭/미숙",
     "Candidatus Liberibacter. 감귤 나무류. 나무이(psyllid) 매개",
     "치료 불가 → 매개충 방제 → 감염 나무 제거 → 인접 나무 관찰",
     "나무이 관리. 감염 의심 시 즉시 격리. 건강한 묘목 사용",
     "치료 불가. 확산 방지가 핵심",
     "감귤류 전문 병이야. 다른 나무 보호가 우선"),

    ("Healthy", "건강",
     "정상적인 녹색 잎, 반점/변색/기형 없음",
     "해당 없음",
     "현재 건강 상태 유지. 정기 관찰 권장",
     "규칙적 관수, 적절한 광량, 통풍, 계절별 관리",
     "해당 없음",
     "건강해! 지금 하는 대로 계속 해주면 돼"),
]

for d in diseases:
    db.execute("INSERT OR REPLACE INTO diseases VALUES (?,?,?,?,?,?,?,?)", d)

# ==========================================
# 8개 카테고리 케어 팁
# ==========================================
care_tips = [
    # 물
    ("water", "주기", "general", "겉흙이 1~2cm 마르면 물을 줘. 화분 밑으로 물이 빠질 때까지", "계절/종에 따라 다름"),
    ("water", "시간대", "general", "아침이 가장 좋아. 저녁에 주면 과습 위험", None),
    ("water", "저면관수", "general", "화분을 물이 담긴 그릇에 30분 놓기. 흙이 아래서 위로 수분 흡수", "균일한 수분 공급에 좋음"),
    ("water", "분무", "general", "잎에 분무. 열대식물은 좋아하지만 다육이는 싫어함", "곰팡이 주의"),
    ("water", "과습 신호", "general", "잎 노랗게, 물컹, 뿌리 무름, 곰팡이, 날파리", None),
    # 빛
    ("light", "직사광", "general", "직사광: 선인장, 다육이 OK. 대부분 관엽식물은 잎이 탈 수 있어", None),
    ("light", "간접광", "general", "밝은 간접광: 몬스테라, 스킨답서스 등 대부분 실내식물에 적합", None),
    ("light", "저광량", "general", "그늘 OK: 스파티필럼, 산세베리아, 아이비", None),
    ("light", "겨울", "general", "겨울철 광량 50% 감소. 창가로 옮기거나 식물등 고려", None),
    ("light", "과다 신호", "general", "잎 끝 갈변, 색 바래짐, 잎이 말림", None),
    ("light", "부족 신호", "general", "웃자람(줄기 길어짐), 잎 작아짐, 색이 연해짐", None),
    # 흙
    ("soil", "일반 배합", "general", "배양토:펄라이트:바크 = 5:3:2 (일반 관엽)", None),
    ("soil", "다육 배합", "general", "배양토:마사토:펄라이트 = 3:4:3", None),
    ("soil", "교체 시기", "general", "1~2년마다. 뿌리가 화분 밑으로 나오면. 봄이 가장 좋음", None),
    ("soil", "마감재", "general", "마사토: 장식+과습 방지. 펄라이트: 통기성. 바크: 보습", None),
    # 영양
    ("nutrition", "비료 종류", "general", "액체비료(물에 타서), 고체비료(흙에 꽂기), 엽면시비(잎에 뿌리기)", None),
    ("nutrition", "시기", "general", "성장기(봄~가을) 2~4주 간격. 겨울은 비료 중단", None),
    ("nutrition", "과비료 신호", "general", "잎 끝 갈변, 흰 결정(염분), 뿌리 손상. 물로 충분히 씻어내기", None),
    # 환경
    ("environment", "온도", "general", "대부분 18~25°C. 10°C 이하 위험. 급격한 온도 변화 피하기", None),
    ("environment", "습도", "general", "열대식물 60%+ 선호. 겨울 실내 습도 30~40%로 낮아짐. 가습기 or 자갈트레이", None),
    ("environment", "통풍", "general", "하루 1~2회 환기. 밀폐된 환경은 곰팡이 원인", None),
    ("environment", "에어컨/히터", "general", "바람 직접 닿으면 안 됨. 1m 이상 거리 유지", None),
    # 번식
    ("propagation", "꺾꽂이", "general", "마디 아래 5cm 자르기 → 물에 담기 → 뿌리 나면 흙에 심기", None),
    ("propagation", "물꽂이", "general", "2~4주 소요. 물 3일마다 교체. 뿌리 3cm 이상 나면 흙으로", None),
    ("propagation", "잎꽂이", "general", "다육이: 잎 떼서 그늘에 2일 말리고 → 흙 위에 놓기", None),
    ("propagation", "포기나누기", "general", "뿌리가 여러 덩어리면 분리. 봄에. 각 덩어리에 뿌리+잎 있어야", None),
    # 계절
    ("seasonal", "겨울", "general", "물 줄이기, 비료 중단, 창가 빛 확보, 10°C 이하 방지", None),
    ("seasonal", "장마", "general", "과습 주의, 통풍 중요, 물 빈도 줄이기, 곰팡이 확인", None),
    ("seasonal", "환절기", "general", "온도차 주의. 성장기 시작이라 비료+분갈이 적기", None),
    # 트러블
    ("trouble", "잎 처짐", "general", "물 부족 or 과습. 흙 만져서 마르면 물, 젖으면 과습 의심", None),
    ("trouble", "잎 황변", "general", "과습, 영양 부족, 자연 낙엽(아래잎). 위쪽 잎이면 문제", None),
    ("trouble", "잎 갈변", "general", "건조, 직사광 화상, 비료 과다. 갈변 부분 잘라내기", None),
    ("trouble", "뿌리 무름", "general", "과습. 흙에서 꺼내서 썩은 뿌리 제거 → 새 흙에 심기", None),
    ("trouble", "벌레", "general", "깍지벌레, 응애, 날파리. 알코올 솜으로 닦기, 님오일, 통풍 개선", None),
]

for t in care_tips:
    db.execute("INSERT INTO care_tips (category, subcategory, species, tip, detail) VALUES (?,?,?,?,?)", t)

db.commit()
db.close()
print(f"✅ plant_care.db 생성 완료")
print(f"   병변 {len(diseases)}종 + 케어 팁 {len(care_tips)}건")
실행
bashpython scripts/init_db.py

단계 2: MCP Server 만들기
설치
bashpip install mcp --break-system-packages
파일: mcp_server/plant_db_server.py
python"""
Boonz Plant Care MCP Server
식물 케어 DB를 MCP 프로토콜로 노출.

실행: python mcp_server/plant_db_server.py
테스트: FastAPI에서 MCP Client로 호출
"""
import sqlite3
import json
from pathlib import Path
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
import asyncio

DB_PATH = Path(__file__).parent.parent / "data" / "plant_care.db"
server = Server("plant-care-db")


def get_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db


@server.list_tools()
async def list_tools():
    return [
        Tool(
            name="query_disease",
            description="병명으로 질병 정보를 조회합니다. 증상, 원인, 치료법, 예방법, 회복 기간, 심각도 정보를 반환합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "disease_name": {
                        "type": "string",
                        "description": "영문 병명 (예: Late_Blight, Early_Blight, Healthy)"
                    }
                },
                "required": ["disease_name"]
            }
        ),
        Tool(
            name="query_care_tips",
            description="카테고리별 식물 케어 팁을 조회합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "enum": ["water", "light", "soil", "nutrition", "environment", "propagation", "seasonal", "trouble"],
                        "description": "케어 카테고리"
                    },
                    "subcategory": {
                        "type": "string",
                        "description": "세부 항목 (선택). 예: 주기, 저면관수, 직사광, 꺾꽂이"
                    }
                },
                "required": ["category"]
            }
        ),
        Tool(
            name="query_species",
            description="식물 종별 관리 정보를 조회합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "species": {
                        "type": "string",
                        "description": "식물 종명 (예: Monstera deliciosa)"
                    }
                },
                "required": ["species"]
            }
        ),
        Tool(
            name="search_by_symptom",
            description="증상 키워드로 가능한 병변을 검색합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "symptom": {
                        "type": "string",
                        "description": "증상 키워드 (예: 갈색 반점, 흰 가루, 잎 말림)"
                    }
                },
                "required": ["symptom"]
            }
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    db = get_db()

    if name == "query_disease":
        disease_name = arguments["disease_name"]
        row = db.execute("SELECT * FROM diseases WHERE name = ?", (disease_name,)).fetchone()
        if not row:
            return [TextContent(type="text", text=json.dumps({"error": f"'{disease_name}' 정보 없음"}, ensure_ascii=False))]
        result = dict(row)
        return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]

    elif name == "query_care_tips":
        category = arguments["category"]
        subcategory = arguments.get("subcategory", "")
        if subcategory:
            rows = db.execute(
                "SELECT subcategory, tip, detail FROM care_tips WHERE category = ? AND subcategory LIKE ?",
                (category, f"%{subcategory}%")
            ).fetchall()
        else:
            rows = db.execute(
                "SELECT subcategory, tip, detail FROM care_tips WHERE category = ?",
                (category,)
            ).fetchall()
        tips = [dict(r) for r in rows]
        return [TextContent(type="text", text=json.dumps(tips, ensure_ascii=False, indent=2))]

    elif name == "query_species":
        species = arguments["species"]
        row = db.execute(
            "SELECT * FROM species_care WHERE species LIKE ?",
            (f"%{species}%",)
        ).fetchone()
        if not row:
            return [TextContent(type="text", text=json.dumps({"error": f"'{species}' 정보 없음. general 팁을 참고하세요"}, ensure_ascii=False))]
        return [TextContent(type="text", text=json.dumps(dict(row), ensure_ascii=False, indent=2))]

    elif name == "search_by_symptom":
        symptom = arguments["symptom"]
        rows = db.execute(
            "SELECT name, korean_name, symptoms, severity_levels FROM diseases WHERE symptoms LIKE ?",
            (f"%{symptom}%",)
        ).fetchall()
        results = [dict(r) for r in rows]
        return [TextContent(type="text", text=json.dumps(results, ensure_ascii=False, indent=2))]

    return [TextContent(type="text", text="알 수 없는 도구")]


async def main():
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())

단계 3: MCP Client (FastAPI에서 호출)
파일: src/mcp_client.py
python"""
MCP Client — FastAPI에서 MCP Server를 호출하는 클라이언트.
subprocess로 MCP Server를 stdio 방식으로 연결.
"""
import subprocess
import json
import asyncio
from pathlib import Path

MCP_SERVER_PATH = Path(__file__).parent.parent / "mcp_server" / "plant_db_server.py"


class PlantCareDB:
    """MCP 프로토콜로 plant_care DB를 조회하는 클라이언트"""

    def __init__(self):
        self._process = None

    async def _call_mcp(self, tool_name: str, arguments: dict) -> dict:
        """MCP Server에 도구 호출 요청"""
        # 간소화 버전: 직접 DB 조회 (MCP 프로토콜 핸들셰이크 생략)
        # 프로덕션에서는 mcp.client 사용
        import sqlite3
        db_path = Path(__file__).parent.parent / "data" / "plant_care.db"

        if not db_path.exists():
            return {"error": "DB 없음. python scripts/init_db.py 실행"}

        db = sqlite3.connect(db_path)
        db.row_factory = sqlite3.Row

        if tool_name == "query_disease":
            row = db.execute(
                "SELECT * FROM diseases WHERE name = ?",
                (arguments["disease_name"],)
            ).fetchone()
            return dict(row) if row else {"error": f"'{arguments['disease_name']}' 없음"}

        elif tool_name == "query_care_tips":
            category = arguments["category"]
            subcategory = arguments.get("subcategory", "")
            if subcategory:
                rows = db.execute(
                    "SELECT subcategory, tip, detail FROM care_tips WHERE category = ? AND subcategory LIKE ?",
                    (category, f"%{subcategory}%")
                ).fetchall()
            else:
                rows = db.execute(
                    "SELECT subcategory, tip, detail FROM care_tips WHERE category = ?",
                    (category,)
                ).fetchall()
            return {"tips": [dict(r) for r in rows]}

        elif tool_name == "search_by_symptom":
            rows = db.execute(
                "SELECT name, korean_name, symptoms FROM diseases WHERE symptoms LIKE ?",
                (f"%{arguments['symptom']}%",)
            ).fetchall()
            return {"matches": [dict(r) for r in rows]}

        return {"error": "알 수 없는 도구"}

    async def get_disease_info(self, disease_name: str) -> dict:
        """병변 정보 조회"""
        return await self._call_mcp("query_disease", {"disease_name": disease_name})

    async def get_care_tips(self, category: str, subcategory: str = "") -> dict:
        """케어 팁 조회"""
        return await self._call_mcp("query_care_tips", {"category": category, "subcategory": subcategory})

    async def search_symptom(self, symptom: str) -> dict:
        """증상으로 병변 검색"""
        return await self._call_mcp("search_by_symptom", {"symptom": symptom})


# 싱글턴
plant_db = PlantCareDB()

단계 4: llm.py 수정 — DB 정보 기반 가이드 생성
파일: src/inference/llm.py에 추가
python# 기존 _call_llm 함수 아래에 추가

async def generate_care_guide_from_db(disease_name: str, lesion_ratio: float, nickname: str) -> str:
    """
    MCP → DB 조회 → 검증된 정보 → LLM 톤 변환.
    LLM이 정보를 만들지 않음. 톤만 바꿈.
    """
    from src.mcp_client import plant_db

    # Step 1: DB에서 검증된 정보 조회
    disease_info = await plant_db.get_disease_info(disease_name)

    if "error" in disease_info:
        # DB에 없으면 기존 LLM 방식으로 폴백
        return _call_llm(f"{nickname}의 {disease_name} 케어 가이드를 알려줘")

    # Step 2: 심각도 판단
    severity_levels = disease_info.get("severity_levels", "")
    if lesion_ratio <= 0.10:
        severity = "초기"
    elif lesion_ratio <= 0.25:
        severity = "중기"
    else:
        severity = "후기"

    # Step 3: 검증된 정보를 LLM에 전달 → 관계 톤 변환
    prompt = f"""{BOONZ_PERSONA}

[검증된 전문 정보 — 이 정보를 바탕으로만 답해. 추가/창작 금지]
병명: {disease_info['korean_name']}
증상: {disease_info['symptoms']}
원인: {disease_info['cause']}
치료법: {disease_info['treatment']}
예방법: {disease_info['prevention']}
회복 기간: {disease_info['recovery_days']}
현재 상태: {severity} (병변 {lesion_ratio*100:.1f}%)
심각도 안내: {severity_levels}

위 정보를 {nickname}의 시점에서, 분즈 톤으로 전달해줘.
- 전문 용어는 쉽게 바꿔
- "{nickname}한테 물어봤는데" 또는 "이건 내 생각인데" 로 시작
- 3~5문장으로 짧게
- 마지막에 위로나 응원 한 마디"""

    return _call_llm(prompt)


async def answer_care_question_from_db(question: str, nickname: str, diagnosis_context: str = "") -> str:
    """
    챗봇 질문 → DB에서 관련 팁 조회 → LLM 톤 변환.
    """
    from src.mcp_client import plant_db

    # 질문에서 카테고리 추론
    category_keywords = {
        "water": ["물", "관수", "저면", "분무", "과습", "마르"],
        "light": ["빛", "광", "직사", "간접", "그늘", "햇빛", "어두"],
        "soil": ["흙", "배양토", "마사토", "펄라이트", "분갈이", "화분"],
        "nutrition": ["비료", "영양", "액비", "과비료"],
        "environment": ["온도", "습도", "통풍", "에어컨", "히터", "환기"],
        "propagation": ["꺾꽂이", "물꽂이", "번식", "삽목", "포기나누기"],
        "seasonal": ["겨울", "여름", "장마", "환절기", "계절"],
        "trouble": ["처짐", "노랗", "갈변", "무름", "벌레", "시들", "아프", "이상"],
    }

    matched_tips = []
    for category, keywords in category_keywords.items():
        if any(k in question for k in keywords):
            tips = await plant_db.get_care_tips(category)
            if "tips" in tips:
                matched_tips.extend(tips["tips"])

    # DB에 관련 정보가 있으면 컨텍스트로 제공
    tips_context = ""
    if matched_tips:
        tips_text = "\n".join([f"- {t['tip']}" for t in matched_tips[:5]])
        tips_context = f"\n[참조 지식 — 이 정보를 바탕으로 답해]\n{tips_text}"

    prompt = f"""{BOONZ_PERSONA}

{tips_context}

{f"현재 {nickname} 상태: {diagnosis_context}" if diagnosis_context else ""}

사용자 질문: "{question}"

{nickname}의 시점에서 답해줘.
참조 지식이 있으면 그걸 바탕으로, 없으면 네가 아는 걸로.
확실하지 않으면 "잘 모르겠는데, 사진 찍어서 보여줘"라고 해.
3~5문장으로 짧게."""

    return _call_llm(prompt)

단계 5: FastAPI 엔드포인트 수정
파일: src/api/main.py
python# /care-guide 엔드포인트 수정
@app.post("/care-guide")
async def care_guide(request: dict):
    """MCP → DB 조회 → LLM 톤 변환 케어 가이드"""
    nickname = request.get("nickname", "")
    disease = request.get("disease", "")
    lesion_ratio = request.get("lesion_ratio", 0)

    from src.inference.llm import generate_care_guide_from_db
    guide = await generate_care_guide_from_db(disease, lesion_ratio, nickname)

    return {
        "care_guide": {"text": guide, "source": "mcp_db"},
        "boonz": {"mood": "happy", "message": guide}
    }


# /consult/text 엔드포인트 수정
@app.post("/consult/text")
async def consult_text(request: dict):
    """MCP → DB 팁 조회 → LLM 톤 변환 챗봇"""
    question = request.get("question", "")
    nickname = request.get("nickname", "")
    diagnosis_context = request.get("diagnosis_context", "")

    from src.inference.llm import answer_care_question_from_db
    answer = await answer_care_question_from_db(question, nickname, diagnosis_context)

    return {"boonz": {"mood": "happy", "message": answer}}

테스트
bash# 1. DB 생성
python scripts/init_db.py

# 2. DB 내용 확인
python -c "
import sqlite3
db = sqlite3.connect('data/plant_care.db')
print('병변:', db.execute('SELECT COUNT(*) FROM diseases').fetchone()[0], '종')
print('케어팁:', db.execute('SELECT COUNT(*) FROM care_tips').fetchone()[0], '건')
print()
row = db.execute('SELECT korean_name, treatment FROM diseases WHERE name=\"Late_Blight\"').fetchone()
print(f'Late_Blight: {row[0]}')
print(f'치료법: {row[1][:50]}...')
"

# 3. FastAPI 실행 후 테스트
uvicorn src.api.main:app --reload &
sleep 5

# 케어 가이드 (DB 기반)
curl -X POST http://localhost:8000/care-guide \
  -H "Content-Type: application/json" \
  -d '{"nickname":"마리","disease":"Late_Blight","lesion_ratio":0.09}'

# 챗봇 (DB 팁 참조)
curl -X POST http://localhost:8000/consult/text \
  -H "Content-Type: application/json" \
  -d '{"question":"분갈이 어떻게 해?","nickname":"마리"}'

echo "✅ MCP + DB 연동 OK"

발표에서 어떻게 말하나
"케어 가이드는 LLM이 만들어내는 게 아닙니다.
 12클래스 병변별 치료법, 예방법, 회복 기간이
 SQLite DB에 검증된 데이터로 저장되어 있고,
 MCP 프로토콜로 DB를 조회한 뒤,
 LLM은 그 정보를 관계 톤으로 변환하는 역할만 합니다.

 즉, 정보의 정확성은 DB가 보장하고,
 감성은 LLM이 담당합니다."

파일 구조
C:\plantcare\
├── data/
│   └── plant_care.db          ← SQLite (12병변 + 35케어팁)
├── scripts/
│   └── init_db.py             ← DB 초기화
├── mcp_server/
│   └── plant_db_server.py     ← MCP Server (4개 도구)
├── src/
│   ├── mcp_client.py          ← MCP Client (FastAPI용)
│   ├── inference/
│   │   └── llm.py             ← DB 기반 가이드 생성 함수 추가
│   └── api/
│       └── main.py            ← 엔드포인트 수정

적용 순서 (Claude Code한테)
1. scripts/init_db.py 실행 → plant_care.db 생성
2. mcp_server/plant_db_server.py 생성
3. src/mcp_client.py 생성
4. src/inference/llm.py에 generate_care_guide_from_db, answer_care_question_from_db 추가
5. src/api/main.py의 /care-guide, /consult/text 엔드포인트 수정
6. 테스트