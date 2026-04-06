"""식물 케어 DB 초기화. 실행: python scripts/init_db.py"""
import sqlite3
from pathlib import Path

DB_PATH = Path("data/plant_care.db")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

db = sqlite3.connect(DB_PATH)

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

db.execute("""
CREATE TABLE IF NOT EXISTS care_tips (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    subcategory TEXT NOT NULL,
    species TEXT DEFAULT 'general',
    tip TEXT NOT NULL,
    detail TEXT
)""")

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
     "Passalora fulva. 고습도(85%+), 통풍 부족",
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

care_tips = [
    ("water", "주기", "general", "겉흙이 1~2cm 마르면 물을 줘. 화분 밑으로 물이 빠질 때까지", "계절/종에 따라 다름"),
    ("water", "시간대", "general", "아침이 가장 좋아. 저녁에 주면 과습 위험", None),
    ("water", "저면관수", "general", "화분을 물이 담긴 그릇에 30분 놓기. 흙이 아래서 위로 수분 흡수", "균일한 수분 공급에 좋음"),
    ("water", "분무", "general", "잎에 분무. 열대식물은 좋아하지만 다육이는 싫어함", "곰팡이 주의"),
    ("water", "과습 신호", "general", "잎 노랗게, 물컹, 뿌리 무름, 곰팡이, 날파리", None),
    ("light", "직사광", "general", "직사광: 선인장, 다육이 OK. 대부분 관엽식물은 잎이 탈 수 있어", None),
    ("light", "간접광", "general", "밝은 간접광: 몬스테라, 스킨답서스 등 대부분 실내식물에 적합", None),
    ("light", "저광량", "general", "그늘 OK: 스파티필럼, 산세베리아, 아이비", None),
    ("light", "겨울", "general", "겨울철 광량 50% 감소. 창가로 옮기거나 식물등 고려", None),
    ("light", "과다 신호", "general", "잎 끝 갈변, 색 바래짐, 잎이 말림", None),
    ("light", "부족 신호", "general", "웃자람(줄기 길어짐), 잎 작아짐, 색이 연해짐", None),
    ("soil", "일반 배합", "general", "배양토:펄라이트:바크 = 5:3:2 (일반 관엽)", None),
    ("soil", "다육 배합", "general", "배양토:마사토:펄라이트 = 3:4:3", None),
    ("soil", "교체 시기", "general", "1~2년마다. 뿌리가 화분 밑으로 나오면. 봄이 가장 좋음", None),
    ("soil", "마감재", "general", "마사토: 장식+과습 방지. 펄라이트: 통기성. 바크: 보습", None),
    ("nutrition", "비료 종류", "general", "액체비료(물에 타서), 고체비료(흙에 꽂기), 엽면시비(잎에 뿌리기)", None),
    ("nutrition", "시기", "general", "성장기(봄~가을) 2~4주 간격. 겨울은 비료 중단", None),
    ("nutrition", "과비료 신호", "general", "잎 끝 갈변, 흰 결정(염분), 뿌리 손상. 물로 충분히 씻어내기", None),
    ("environment", "온도", "general", "대부분 18~25°C. 10°C 이하 위험. 급격한 온도 변화 피하기", None),
    ("environment", "습도", "general", "열대식물 60%+ 선호. 겨울 실내 습도 30~40%로 낮아짐. 가습기 or 자갈트레이", None),
    ("environment", "통풍", "general", "하루 1~2회 환기. 밀폐된 환경은 곰팡이 원인", None),
    ("environment", "에어컨/히터", "general", "바람 직접 닿으면 안 됨. 1m 이상 거리 유지", None),
    ("propagation", "꺾꽂이", "general", "마디 아래 5cm 자르기 → 물에 담기 → 뿌리 나면 흙에 심기", None),
    ("propagation", "물꽂이", "general", "2~4주 소요. 물 3일마다 교체. 뿌리 3cm 이상 나면 흙으로", None),
    ("propagation", "잎꽂이", "general", "다육이: 잎 떼서 그늘에 2일 말리고 → 흙 위에 놓기", None),
    ("propagation", "포기나누기", "general", "뿌리가 여러 덩어리면 분리. 봄에. 각 덩어리에 뿌리+잎 있어야", None),
    ("seasonal", "겨울", "general", "물 줄이기, 비료 중단, 창가 빛 확보, 10°C 이하 방지", None),
    ("seasonal", "장마", "general", "과습 주의, 통풍 중요, 물 빈도 줄이기, 곰팡이 확인", None),
    ("seasonal", "환절기", "general", "온도차 주의. 성장기 시작이라 비료+분갈이 적기", None),
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
import sys
sys.stdout.reconfigure(encoding="utf-8")
print(f"plant_care.db 생성 완료")
print(f"   병변 {len(diseases)}종 + 케어 팁 {len(care_tips)}건")
