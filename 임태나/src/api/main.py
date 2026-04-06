"""FastAPI 메인 앱.

엔드포인트:
  /diagnose
  /medicine
  /consult/voice
  /consult/text
  /api/plants, /api/care-log, /api/timeline/{nickname}, /api/pattern/{nickname}
  /audio/ (정적 파일)
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.api.routes import diagnose, medicine, plants, voice
from src.config import PROJECT_ROOT

app = FastAPI(
    title="PlantCare AI",
    description="반려식물 건강 진단 + 맞춤 케어 시스템",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(diagnose.router)
app.include_router(medicine.router)
app.include_router(voice.router)
app.include_router(plants.router)

audio_dir = PROJECT_ROOT / "audio"
audio_dir.mkdir(parents=True, exist_ok=True)
app.mount("/audio", StaticFiles(directory=str(audio_dir)), name="audio")


@app.get("/health")
async def health():
    return {"status": "ok"}
