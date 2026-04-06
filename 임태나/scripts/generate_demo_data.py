"""시연용 데이터 생성 스크립트.

마리 식물 30일치 데이터 생성:
- 병변 비율: 15% → 12% → 8% → 5% → 2% (완화 추세)
- 매일 케어 로그 포함
- plants.json / care_log.jsonl 형식에 맞게 생성
"""

import json
from datetime import date, timedelta
from pathlib import Path

from loguru import logger

PLANTS_FILE = Path("data/plants.json")
CARE_LOG_FILE = Path("data/care_log.jsonl")

NICKNAME = "마리"
START_DATE = date(2026, 3, 7)  # 30일 전

# 병변 비율 완화 추세 (30일치 ~ 5구간)
LESION_SCHEDULE: list[tuple[int, int, float]] = [
    (0,  5,  0.15),
    (5,  10, 0.12),
    (10, 18, 0.08),
    (18, 24, 0.05),
    (24, 30, 0.02),
]

DAILY_ACTIONS: list[list[str]] = [
    ["water"],
    ["observe"],
    ["water", "clean"],
    ["observe"],
    ["medicine"],
    ["water"],
    ["observe"],
]


def _get_lesion(day_offset: int) -> float:
    """day_offset → 병변 비율 반환."""
    for start, end, ratio in LESION_SCHEDULE:
        if start <= day_offset < end:
            return ratio
    return 0.02


def generate_plants() -> None:
    """plants.json에 마리 식물 등록 (없으면 추가)."""
    PLANTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    plants: list[dict] = []
    if PLANTS_FILE.exists():
        plants = json.loads(PLANTS_FILE.read_text(encoding="utf-8"))

    if not any(p["nickname"] == NICKNAME for p in plants):
        plants.append({
            "nickname": NICKNAME,
            "species": "Begonia (Begonia spp.)",
            "registered": START_DATE.isoformat(),
        })
        PLANTS_FILE.write_text(
            json.dumps(plants, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        logger.info(f"plants.json: {NICKNAME} 등록 완료")
    else:
        logger.info(f"plants.json: {NICKNAME} 이미 존재, 스킵")


def generate_care_logs() -> None:
    """care_log.jsonl에 30일치 케어 로그 생성."""
    CARE_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    existing_lines: list[str] = []
    if CARE_LOG_FILE.exists():
        existing_lines = [
            line for line in CARE_LOG_FILE.read_text(encoding="utf-8").strip().split("\n")
            if line
        ]

    existing_dates: set[str] = set()
    for line in existing_lines:
        try:
            entry = json.loads(line)
            if entry.get("plant") == NICKNAME:
                existing_dates.add(entry.get("date", "")[:10])
        except json.JSONDecodeError:
            pass

    new_entries: list[str] = []
    for day_offset in range(30):
        current_date = START_DATE + timedelta(days=day_offset)
        date_str = current_date.isoformat()

        if date_str in existing_dates:
            continue

        lesion = _get_lesion(day_offset)
        actions = DAILY_ACTIONS[day_offset % len(DAILY_ACTIONS)]

        for action in actions:
            entry: dict = {
                "date": f"{date_str} 09:00",
                "plant": NICKNAME,
                "action": action,
            }
            if day_offset % 5 == 0:
                entry["disease"] = "Powdery_Mildew"
                entry["lesion"] = lesion
            new_entries.append(json.dumps(entry, ensure_ascii=False))

    if new_entries:
        with open(CARE_LOG_FILE, "a", encoding="utf-8") as f:
            for line in new_entries:
                f.write(line + "\n")
        logger.info(f"care_log.jsonl: {len(new_entries)}개 항목 추가 완료")
    else:
        logger.info("care_log.jsonl: 추가할 데이터 없음 (이미 존재)")


def main() -> None:
    """시연 데이터 생성 메인 함수."""
    generate_plants()
    generate_care_logs()
    logger.info("시연 데이터 생성 완료")


if __name__ == "__main__":
    main()
