"""식물 등록 + 케어 로그 + 타임라인 + 패턴 분석 엔드포인트."""

import json
from datetime import datetime

from fastapi import APIRouter, HTTPException
from loguru import logger

from src.api.schemas import (
    BoonzResponse,
    CareLogRequest,
    CareLogResponse,
    PatternResponse,
    PlantItem,
    PlantRegisterRequest,
    TimelineItem,
    TimelineResponse,
)
from src.config import CARE_LOG_JSONL, DIAGNOSIS_HISTORY_JSONL, PLANTS_JSON
from src.inference.llm import analyze_care_pattern, generate_greeting, get_boonz_mood

router = APIRouter(prefix="/api")


def _load_plants() -> list[dict]:
    if not PLANTS_JSON.exists():
        return []
    return json.loads(PLANTS_JSON.read_text(encoding="utf-8"))


def _save_plants(plants: list[dict]) -> None:
    PLANTS_JSON.parent.mkdir(parents=True, exist_ok=True)
    PLANTS_JSON.write_text(
        json.dumps(plants, ensure_ascii=False, indent=2), encoding="utf-8"
    )


@router.post("/plants", response_model=PlantItem)
async def register_plant(req: PlantRegisterRequest) -> PlantItem:
    """식물 등록."""
    plants = _load_plants()
    if any(p["nickname"] == req.nickname for p in plants):
        raise HTTPException(
            status_code=409, detail=f"'{req.nickname}'은 이미 등록된 별명입니다."
        )

    now = datetime.now().isoformat()
    greeting = generate_greeting(req.nickname, req.species_name)
    plants.append({
        "nickname": req.nickname,
        "species_name": req.species_name,
        "registered_at": now,
        "greeting": greeting,
    })
    _save_plants(plants)
    logger.info(f"식물 등록: {req.nickname}")
    return PlantItem(
        nickname=req.nickname,
        species_name=req.species_name,
        registered_at=now,
    )


@router.get("/plants", response_model=list[PlantItem])
async def list_plants() -> list[PlantItem]:
    """등록된 식물 목록."""
    return [
        PlantItem(
            nickname=p["nickname"],
            species_name=p.get("species_name", p.get("species", "")),
            registered_at=p.get("registered_at", p.get("registered", "")),
        )
        for p in _load_plants()
    ]


@router.post("/care-log", response_model=CareLogResponse)
async def add_care_log(req: CareLogRequest) -> CareLogResponse:
    """원터치 케어 로그 추가."""
    entry = {
        "timestamp": datetime.now().isoformat(),
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "plant": req.nickname,
        "action": req.action,
        "disease": req.disease,
        "lesion": req.lesion_ratio,
    }
    CARE_LOG_JSONL.parent.mkdir(parents=True, exist_ok=True)
    with open(CARE_LOG_JSONL, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    logger.info(f"케어 로그: {req.nickname} - {req.action}")

    mood, _ = get_boonz_mood(req.lesion_ratio, req.nickname)
    return CareLogResponse(
        saved=True,
        boonz=BoonzResponse(mood=mood, message=f"{req.nickname}한테 전해놨어!"),
    )


@router.get("/timeline/{nickname}", response_model=TimelineResponse)
async def get_timeline(nickname: str) -> TimelineResponse:
    """통합 타임라인 (진단 + 케어 로그, 날짜순)."""
    items: list[TimelineItem] = []

    if DIAGNOSIS_HISTORY_JSONL.exists():
        for line in DIAGNOSIS_HISTORY_JSONL.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
                plant_key = entry.get("plant") or entry.get("nickname", "")
                if plant_key == nickname:
                    items.append(TimelineItem(
                        timestamp=entry.get("timestamp", entry.get("date", "")),
                        type="diagnosis",
                        nickname=nickname,
                        disease=entry.get("disease", {}).get("korean", "")
                                if isinstance(entry.get("disease"), dict)
                                else entry.get("disease", ""),
                        lesion_ratio=entry.get("lesion", {}).get("ratio")
                                     if isinstance(entry.get("lesion"), dict)
                                     else entry.get("lesion"),
                    ))
            except (json.JSONDecodeError, AttributeError):
                continue

    if CARE_LOG_JSONL.exists():
        for line in CARE_LOG_JSONL.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
                plant_key = entry.get("plant") or entry.get("nickname", "")
                if plant_key == nickname:
                    items.append(TimelineItem(
                        timestamp=entry.get("timestamp", entry.get("date", "")),
                        type="care",
                        nickname=nickname,
                        action=entry.get("action", ""),
                        disease=entry.get("disease", ""),
                        lesion_ratio=entry.get("lesion") or entry.get("lesion_ratio"),
                    ))
            except (json.JSONDecodeError, AttributeError):
                continue

    items.sort(key=lambda x: x.timestamp)
    mood, message = get_boonz_mood(nickname=nickname)
    return TimelineResponse(
        nickname=nickname,
        items=items,
        boonz=BoonzResponse(mood=mood, message=message),
    )


@router.get("/pattern/{nickname}", response_model=PatternResponse)
async def get_pattern(nickname: str) -> PatternResponse:
    """돌봄 패턴 분석 (Ollama)."""
    entries: list[dict] = []
    if CARE_LOG_JSONL.exists():
        for line in CARE_LOG_JSONL.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
                plant_key = entry.get("plant") or entry.get("nickname", "")
                if plant_key == nickname:
                    entries.append(entry)
            except json.JSONDecodeError:
                continue

    if len(entries) < 10:
        n = len(entries)
        msg = f"아직 기록이 {n}개야. 조금만 더 쌓아줘"
        return PatternResponse(
            nickname=nickname,
            analysis=msg,
            boonz=BoonzResponse(mood="default", message=msg),
        )

    log_text = "\n".join(
        f"{e.get('date', e.get('timestamp', ''))[:10]} {e.get('action', '')}"
        + (f" 병변 {e['lesion'] * 100:.0f}%" if e.get("lesion") else "")
        for e in entries
    )
    analysis = analyze_care_pattern(nickname, log_text)
    return PatternResponse(
        nickname=nickname,
        analysis=analysis,
        boonz=BoonzResponse(mood="happy", message=analysis[:80] + "..."),
    )
