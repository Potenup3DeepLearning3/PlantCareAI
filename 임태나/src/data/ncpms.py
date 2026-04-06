"""NCPMS 병해충 도감 API 연동.

공공데이터포털 API로 화훼 병해충 정보를 수집하여 JSON 지식 베이스를 구축한다.
"""

import json
import os
from pathlib import Path

import requests
from loguru import logger

from src.config import DATA_RAW_DIR

NCPMS_DIR = DATA_RAW_DIR / "ncpms_knowledge"
NCPMS_DIR.mkdir(parents=True, exist_ok=True)

DATAGO_API_KEY = os.getenv("DATAGO_API_KEY", "")

# NCPMS 병해충 도감 API (단일 엔드포인트, serviceCode로 분기)
API_URL = "http://ncpms.rda.go.kr/npmsAPI/service"


def fetch_disease_list(crop_name: str = "화훼류", num_rows: int = 100) -> list[dict]:
    """병해충 목록 조회.

    Args:
        crop_name: 작물명 (기본: 화훼류).
        num_rows: 조회 행 수.

    Returns:
        병해충 목록 딕셔너리 리스트.
    """
    if not DATAGO_API_KEY:
        logger.error("DATAGO_API_KEY가 설정되지 않았습니다.")
        return []

    params = {
        "apiKey": DATAGO_API_KEY,
        "serviceCode": "SVC01",
        "cropName": crop_name,
        "numOfRows": num_rows,
    }

    try:
        resp = requests.get(API_URL, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        service = data.get("service", data)
        items = service.get("list", [])
        if isinstance(items, dict):
            items = [items]
        logger.info(f"NCPMS 목록 조회: {crop_name} → {len(items)}건")
        return items
    except Exception as e:
        logger.error(f"NCPMS 목록 조회 실패: {e}")
        return []


def fetch_disease_detail(sick_key: str) -> dict:
    """병해충 상세 정보 조회.

    Args:
        sick_key: 병해충 키.

    Returns:
        상세 정보 딕셔너리.
    """
    params = {
        "apiKey": DATAGO_API_KEY,
        "serviceCode": "SVC05",
        "sickKey": sick_key,
    }

    try:
        resp = requests.get(API_URL, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data.get("service", data)
    except Exception as e:
        logger.warning(f"NCPMS 상세 조회 실패 (sickKey={sick_key}): {e}")
        return {}


def build_knowledge_base(crop_names: list[str] | None = None) -> list[dict]:
    """NCPMS 지식 베이스 구축.

    Args:
        crop_names: 조회할 작물 목록. None이면 기본 목록 사용.

    Returns:
        병해충 지식 리스트.
    """
    if crop_names is None:
        crop_names = ["화훼류", "관엽식물", "선인장", "난"]

    knowledge = []
    seen_keys = set()

    for crop in crop_names:
        diseases = fetch_disease_list(crop)
        for item in diseases:
            sick_key = item.get("sickKey", "")
            if not sick_key or sick_key in seen_keys:
                continue
            seen_keys.add(sick_key)

            detail = fetch_disease_detail(sick_key)
            entry = {
                "sick_key": sick_key,
                "crop_name": item.get("cropName", crop),
                "disease_name": item.get("sickNameKor", ""),
                "disease_name_en": item.get("sickNameEng", ""),
                "symptoms": detail.get("symptoms", item.get("developmentCondition", "")),
                "environment": detail.get("developmentCondition", ""),
                "treatment": detail.get("preventionMethod", ""),
            }
            knowledge.append(entry)

    return knowledge


def save_knowledge_base(knowledge: list[dict], output_path: Path | None = None) -> Path:
    """지식 베이스를 JSON 파일로 저장."""
    output_path = output_path or NCPMS_DIR / "ncpms_knowledge.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(knowledge, f, ensure_ascii=False, indent=2)
    logger.info(f"NCPMS 지식 베이스 저장: {output_path} ({len(knowledge)}건)")
    return output_path


def load_knowledge_base(path: Path | None = None) -> list[dict]:
    """저장된 지식 베이스 로드."""
    path = path or NCPMS_DIR / "ncpms_knowledge.json"
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def search_knowledge(disease_name: str, knowledge: list[dict] | None = None) -> dict | None:
    """질병명으로 지식 베이스 검색."""
    if knowledge is None:
        knowledge = load_knowledge_base()
    for entry in knowledge:
        if disease_name.lower() in entry.get("disease_name", "").lower():
            return entry
        if disease_name.lower() in entry.get("disease_name_en", "").lower():
            return entry
    return None


def main() -> None:
    """NCPMS 지식 베이스 구축 실행."""
    logger.info("=== NCPMS 지식 베이스 구축 시작 ===")
    knowledge = build_knowledge_base()
    if knowledge:
        save_knowledge_base(knowledge)
    else:
        logger.warning("수집된 데이터 없음. API 키/네트워크를 확인해주세요.")
    logger.info("=== NCPMS 완료 ===")


if __name__ == "__main__":
    main()
