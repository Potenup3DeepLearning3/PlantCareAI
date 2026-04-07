"""
식물 케어 DB 초기화.
diseases.json + care_tips.json → plant_care.db

실행: python scripts/init_db.py

출처:
  - Clemson University HGIC 2251 "Houseplant Diseases & Disorders"
  - RHS (Royal Horticultural Society) Advice Guides
  - Missouri Botanical Garden Houseplant Guides
  - Purdue University PPDL
  - University of Maryland Extension
  - OurHouseplants.com Disease & Care Guides
"""
import sqlite3
import json
from pathlib import Path

# 경로
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "plant_care.db"

DISEASES_JSON = DATA_DIR / "diseases.json"
CARE_TIPS_JSON = DATA_DIR / "care_tips.json"

def init_db():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    # 기존 DB 삭제 후 새로 생성
    if DB_PATH.exists():
        DB_PATH.unlink()
        print(f"기존 DB 삭제: {DB_PATH}")

    db = sqlite3.connect(DB_PATH)

    # ==========================================
    # 테이블 생성
    # ==========================================

    # 병변 테이블 (source 컬럼 추가)
    db.execute("""
    CREATE TABLE diseases (
        name TEXT PRIMARY KEY,
        korean_name TEXT NOT NULL,
        description TEXT,
        symptoms TEXT NOT NULL,
        cause TEXT NOT NULL,
        treatment TEXT NOT NULL,
        prevention TEXT NOT NULL,
        recovery_days TEXT NOT NULL,
        severity_levels TEXT NOT NULL,
        affected_houseplants TEXT,
        source TEXT NOT NULL
    )""")

    # 케어 팁 테이블 (source 컬럼 추가)
    db.execute("""
    CREATE TABLE care_tips (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category TEXT NOT NULL,
        subcategory TEXT NOT NULL,
        species TEXT DEFAULT 'general',
        tip TEXT NOT NULL,
        source TEXT NOT NULL
    )""")

    print("테이블 생성 완료")

    # ==========================================
    # JSON에서 데이터 로드
    # ==========================================

    # diseases.json
    if not DISEASES_JSON.exists():
        print(f"❌ {DISEASES_JSON} 없음! data/ 폴더에 diseases.json을 넣어주세요.")
        return

    with open(DISEASES_JSON, "r", encoding="utf-8") as f:
        diseases = json.load(f)

    for d in diseases:
        db.execute("""
        INSERT INTO diseases (name, korean_name, description, symptoms, cause,
                              treatment, prevention, recovery_days, severity_levels,
                              affected_houseplants, source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            d["name"], d["korean_name"], d.get("description", ""),
            d["symptoms"], d["cause"], d["treatment"], d["prevention"],
            d["recovery_days"], d["severity_levels"],
            d.get("affected_houseplants", ""), d["source"]
        ))

    print(f"✅ 병변 {len(diseases)}종 로드 완료")

    # care_tips.json
    if not CARE_TIPS_JSON.exists():
        print(f"❌ {CARE_TIPS_JSON} 없음! data/ 폴더에 care_tips.json을 넣어주세요.")
        return

    with open(CARE_TIPS_JSON, "r", encoding="utf-8") as f:
        care_tips = json.load(f)

    for t in care_tips:
        db.execute("""
        INSERT INTO care_tips (category, subcategory, species, tip, source)
        VALUES (?, ?, ?, ?, ?)
        """, (
            t["category"], t["subcategory"],
            t.get("species", "general"), t["tip"], t["source"]
        ))

    print(f"✅ 케어 팁 {len(care_tips)}건 로드 완료")

    # ==========================================
    # 검증
    # ==========================================
    db.commit()

    disease_count = db.execute("SELECT COUNT(*) FROM diseases").fetchone()[0]
    tip_count = db.execute("SELECT COUNT(*) FROM care_tips").fetchone()[0]
    categories = db.execute("SELECT DISTINCT category FROM care_tips").fetchall()

    print(f"\n{'='*40}")
    print(f"plant_care.db 생성 완료")
    print(f"  병변: {disease_count}종")
    print(f"  케어 팁: {tip_count}건")
    print(f"  카테고리: {', '.join(c[0] for c in categories)}")
    print(f"  경로: {DB_PATH}")
    print(f"{'='*40}")

    # 샘플 출력
    print(f"\n[샘플] 흰가루병 조회:")
    row = db.execute("SELECT korean_name, treatment, source FROM diseases WHERE name='Powdery_Mildew'").fetchone()
    if row:
        print(f"  병명: {row[0]}")
        print(f"  치료: {row[1][:60]}...")
        print(f"  출처: {row[2]}")

    print(f"\n[샘플] 물 관련 팁 조회:")
    rows = db.execute("SELECT subcategory, tip, source FROM care_tips WHERE category='water' LIMIT 3").fetchall()
    for r in rows:
        print(f"  [{r[0]}] {r[1][:50]}... ({r[2]})")

    db.close()


if __name__ == "__main__":
    init_db()
