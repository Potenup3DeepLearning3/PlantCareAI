"""FastAPI 메인 앱.

엔드포인트:
  /diagnose
  /care-guide          ← DB 기반 케어 가이드
  /consult/text        ← DB 팁 참조 챗봇
  /pattern/{nickname}  ← 돌봄 패턴 분석
  /api/plants, /api/care-log, /api/timeline/{nickname}
"""

import json

from fastapi import Body, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes import diagnose, plants
from src.config import CARE_LOG_JSONL

app = FastAPI(
    title="PlantCare AI",
    description="반려식물 건강 진단 + 맞춤 케어 시스템",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(diagnose.router)
app.include_router(plants.router)


@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.2.0"}


# ── /care-guide ────────────────────────────────────────────────────

@app.post("/care-guide")
async def care_guide(request: dict = Body(...)):
    """DB 조회 → LLM 톤 변환 케어 가이드.

    Body: {"nickname": str, "disease": str, "lesion_ratio": float}
    """
    nickname         = request.get("nickname", "식물")
    disease          = request.get("disease", "")
    lesion_ratio     = float(request.get("lesion_ratio", 0))
    clip_description = request.get("clip_description", "")

    from src.inference.llm import generate_care_guide_from_db
    guide = generate_care_guide_from_db(disease, lesion_ratio, nickname, clip_description)

    return {
        "care_guide": {"text": guide, "source": "db"},
        "boonz": {"mood": "happy", "message": guide},
    }


# ── /consult/text ──────────────────────────────────────────────────

@app.post("/consult/text")
async def consult_text(request: dict = Body(...)):
    """DB 팁 참조 → LLM 톤 변환 챗봇.

    Body: {"question": str, "nickname": str, "diagnosis_context": str}
    """
    question  = request.get("question", "")
    nickname  = request.get("nickname", "식물")
    diag_ctx  = request.get("diagnosis_context", "")

    from src.inference.llm import answer_care_question_from_db
    answer = answer_care_question_from_db(question, nickname, diag_ctx)

    return {"boonz": {"mood": "happy", "message": answer}}


# ── /pattern/{nickname} ────────────────────────────────────────────

@app.get("/pattern/{nickname}")
async def pattern(nickname: str):
    """돌봄 패턴 분석.

    Returns: {"boonz": {"mood": str, "message": str}}
    """
    logs = []
    if CARE_LOG_JSONL.exists():
        for line in CARE_LOG_JSONL.read_text(encoding="utf-8").strip().splitlines():
            try:
                entry = json.loads(line)
                if entry.get("plant") == nickname:
                    logs.append(entry)
            except Exception:
                pass

    if len(logs) < 5:
        return {
            "boonz": {
                "mood": "default",
                "message": f"기록이 {len(logs)}개야. 5개 이상 쌓이면 패턴이 보일 거야",
            }
        }

    log_text = "\n".join(
        f"{l.get('date','')[:10]} {l.get('action','')} lesion={l.get('lesion',0)}"
        for l in logs[-20:]
    )

    from src.inference.llm import analyze_care_pattern
    msg = analyze_care_pattern(nickname, log_text)

    return {"boonz": {"mood": "happy", "message": msg or f"{nickname} 데이터 분석 중이야. 잠깐만"}}
