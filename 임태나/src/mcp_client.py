"""
MCP Client — FastAPI에서 plant_care DB를 조회하는 클라이언트.
MCP 핸드셰이크 없이 직접 SQLite 조회 (경량 구현).
"""
import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "data" / "plant_care.db"

CATEGORY_KEYWORDS = {
    "water":       ["물", "관수", "저면", "분무", "과습", "마르"],
    "light":       ["빛", "광", "직사", "간접", "그늘", "햇빛", "어두"],
    "soil":        ["흙", "배양토", "마사토", "펄라이트", "분갈이", "화분"],
    "nutrition":   ["비료", "영양", "액비", "과비료"],
    "environment": ["온도", "습도", "통풍", "에어컨", "히터", "환기"],
    "propagation": ["꺾꽂이", "물꽂이", "번식", "삽목", "포기나누기"],
    "seasonal":    ["겨울", "여름", "장마", "환절기", "계절"],
    "trouble":     ["처짐", "노랗", "갈변", "무름", "벌레", "시들", "아프", "이상"],
}


class PlantCareDB:
    """plant_care SQLite DB를 직접 조회하는 클라이언트."""

    @contextmanager
    def _conn(self):
        if not DB_PATH.exists():
            raise FileNotFoundError(f"DB 없음. python scripts/init_db.py 실행: {DB_PATH}")
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def get_disease_info(self, disease_name: str) -> dict:
        with self._conn() as db:
            row = db.execute("SELECT * FROM diseases WHERE name = ?", (disease_name,)).fetchone()
        return dict(row) if row else {"error": f"'{disease_name}' 정보 없음"}

    def get_care_tips(self, category: str, subcategory: str = "") -> list[dict]:
        with self._conn() as db:
            if subcategory:
                rows = db.execute(
                    "SELECT subcategory, tip, source FROM care_tips WHERE category = ? AND subcategory LIKE ?",
                    (category, f"%{subcategory}%")
                ).fetchall()
            else:
                rows = db.execute(
                    "SELECT subcategory, tip, source FROM care_tips WHERE category = ?",
                    (category,)
                ).fetchall()
        return [dict(r) for r in rows]

    def search_symptom(self, symptom: str) -> list[dict]:
        with self._conn() as db:
            rows = db.execute(
                "SELECT name, korean_name, symptoms, severity_levels FROM diseases WHERE symptoms LIKE ?",
                (f"%{symptom}%",)
            ).fetchall()
        return [dict(r) for r in rows]

    def get_tips_for_question(self, question: str, max_tips: int = 5) -> list[dict]:
        """질문 텍스트에서 카테고리 추론 후 단일 쿼리로 관련 팁 반환."""
        matched_categories = [
            cat for cat, keywords in CATEGORY_KEYWORDS.items()
            if any(k in question for k in keywords)
        ]
        if not matched_categories:
            return []
        placeholders = ",".join("?" * len(matched_categories))
        with self._conn() as db:
            rows = db.execute(
                f"SELECT subcategory, tip, source FROM care_tips WHERE category IN ({placeholders}) LIMIT ?",
                (*matched_categories, max_tips)
            ).fetchall()
        return [dict(r) for r in rows]


# 싱글턴
plant_db = PlantCareDB()
