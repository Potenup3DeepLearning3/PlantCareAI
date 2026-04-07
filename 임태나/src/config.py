"""PlantCare AI 중앙 설정 모듈.

모든 경로, 하이퍼파라미터, 환경변수를 한 곳에서 관리한다.
"""

import os
import random
from pathlib import Path

import numpy as np
import torch
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

# ── 경로 ──────────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DATA_RAW_DIR = DATA_DIR / "raw"
DATA_PROCESSED_DIR = DATA_DIR / "processed"
DATA_SPLITS_DIR = DATA_DIR / "splits"

MODELS_DIR = PROJECT_ROOT / "models"
DISEASE_MODEL_DIR = MODELS_DIR / "disease"
SPECIES_MODEL_DIR = MODELS_DIR / "species"
COMPARISON_DIR = MODELS_DIR / "comparison"

DOCS_DIR = PROJECT_ROOT / "docs"

# ── 이미지 전처리 ─────────────────────────────────────────────
IMAGE_SIZE = 224
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]
CLAHE_CLIP_LIMIT = 3.0
CLAHE_TILE_GRID_SIZE = (16, 16)

# ── 학습 하이퍼파라미터 ───────────────────────────────────────
SEED = 42
BATCH_SIZE = 32
PRETRAIN_EPOCHS = 20
FINETUNE_EPOCHS = 30
LR_FC = 1e-3
LR_BACKBONE = 1e-5
EARLY_STOPPING_PATIENCE = 5

# ── 클래스 수 ─────────────────────────────────────────────────
PLANTVILLAGE_NUM_CLASSES = 38
HEALTHY_WILTED_NUM_CLASSES = 2
SPECIES_NUM_CLASSES = 47

# ── SAM 세그멘테이션 ──────────────────────────────────────────
SAM_MODEL_TYPE = "vit_b"
SAM_CHECKPOINT_PATH = MODELS_DIR / "sam" / "sam_vit_b_01ec64.pth"
SAM_CHECKPOINT_URL = "https://dl.fbaipublicfiles.com/segment_anything/sam_vit_b_01ec64.pth"

SEVERITY_THRESHOLDS = {
    "초기": (0.0, 0.10),
    "중기": (0.10, 0.25),
    "후기": (0.25, 1.0),
}

# ── 질병별 심각도 테이블 (면적 비율 임계값) ──────────────────
DISEASE_SEVERITY_THRESHOLDS: dict[str, dict[str, tuple[float, float]]] = {
    "Mosaic_Virus":       {"초기": (0.0, 0.03), "중기": (0.03, 0.10), "후기": (0.10, 1.0)},
    "Powdery_Mildew":     {"초기": (0.0, 0.08), "중기": (0.08, 0.20), "후기": (0.20, 1.0)},
    "Scab_Rot":           {"초기": (0.0, 0.05), "중기": (0.05, 0.15), "후기": (0.15, 1.0)},
    "Rust":               {"초기": (0.0, 0.05), "중기": (0.05, 0.15), "후기": (0.15, 1.0)},
    "Leaf_Curl":          {"초기": (0.0, 0.10), "중기": (0.10, 0.30), "후기": (0.30, 1.0)},
    "Greening":           {"초기": (0.0, 0.03), "중기": (0.03, 0.10), "후기": (0.10, 1.0)},
    "Early_Blight":       {"초기": (0.0, 0.08), "중기": (0.08, 0.20), "후기": (0.20, 1.0)},
    "Late_Blight":        {"초기": (0.0, 0.08), "중기": (0.08, 0.20), "후기": (0.20, 1.0)},
    "Bacterial_Spot":     {"초기": (0.0, 0.08), "중기": (0.08, 0.20), "후기": (0.20, 1.0)},
    "Septoria_Leaf_Spot": {"초기": (0.0, 0.08), "중기": (0.08, 0.20), "후기": (0.20, 1.0)},
    "Target_Spot":        {"초기": (0.0, 0.08), "중기": (0.08, 0.20), "후기": (0.20, 1.0)},
    "Other_Leaf_Spot":    {"초기": (0.0, 0.10), "중기": (0.10, 0.25), "후기": (0.25, 1.0)},
    "Leaf_Mold":          {"초기": (0.0, 0.08), "중기": (0.08, 0.20), "후기": (0.20, 1.0)},
}

# ── 신뢰도 등급 임계값 ───────────────────────────────────────
CONFIDENCE_HIGH = 0.80
CONFIDENCE_MEDIUM = 0.60

OVERLAY_COLOR = (0, 255, 0)  # BGR 초록색
OVERLAY_ALPHA = 0.4

# ── SAM 세그멘테이션 고급 설정 ───────────────────────────────
SAM_NEGATIVE_MARGIN = 10          # 모서리 negative 포인트 여백 (px)
SAM_MASK_RATIO_MIN = 0.05         # 유효 마스크 최소 면적 비율
SAM_MASK_RATIO_MAX = 0.80         # 유효 마스크 최대 면적 비율
SAM_MORPH_KERNEL_SIZE = 5         # 후처리 morphology 커널 크기
SAM_MORPH_OPEN_ITER = 2           # opening 반복 (노이즈 제거)
SAM_MORPH_CLOSE_ITER = 2          # closing 반복 (구멍 메우기)
SAM_MIN_COMPONENT_RATIO = 0.01    # 최소 연결 성분 비율 (이하 제거)

# ── 종-질병 호환성 (블랙리스트 방식) ─────────────────────────
# 해당 종에 절대 발생하지 않는 질병 목록
SPECIES_DISEASE_BLACKLIST: dict[str, set[str]] = {
    "Sansevieria": {"Powdery_Mildew", "Rust", "Mosaic_Virus", "Greening", "Leaf_Curl"},
    "Monstera": {"Rust", "Greening", "Scab_Rot"},
    "Pothos": {"Rust", "Greening", "Scab_Rot", "Mosaic_Virus"},
    "Ficus": {"Rust", "Greening", "Mosaic_Virus"},
    "Succulent": {"Powdery_Mildew", "Late_Blight", "Greening", "Leaf_Mold"},
    "Cactus": {"Powdery_Mildew", "Late_Blight", "Leaf_Mold", "Leaf_Curl", "Rust"},
    "Calathea": {"Greening", "Scab_Rot", "Rust"},
    "Spathiphyllum": {"Rust", "Greening", "Scab_Rot"},
    "Dracaena": {"Powdery_Mildew", "Rust", "Greening", "Leaf_Curl"},
    "Philodendron": {"Rust", "Greening", "Scab_Rot"},
    "Alocasia": {"Rust", "Greening", "Scab_Rot"},
    "Begonia": {"Greening", "Scab_Rot"},
    "Zamioculcas": {"Powdery_Mildew", "Rust", "Greening", "Leaf_Curl", "Mosaic_Virus"},
}

# ── 파인튜닝 혼합 배치 설정 ──────────────────────────────────
FINETUNE_SOURCE_MIX_RATIO = 0.2  # PlantVillage 데이터 혼합 비율 (catastrophic forgetting 방지)
DATALOADER_NUM_WORKERS = 4       # DataLoader 병렬 로딩 프로세스 수

# ── 데이터 파일 경로 ──────────────────────────────────────────
PLANTS_JSON = DATA_DIR / "plants.json"
CARE_LOG_JSONL = DATA_DIR / "care_log.jsonl"
DIAGNOSIS_HISTORY_JSONL = DATA_DIR / "diagnosis_history.jsonl"

# ── Ollama (로컬 LLM) ────────────────────────────────────────
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma3:4b")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# ── 외부 API 키 ──────────────────────────────────────────────
# Roboflow 제거됨 — 추후 병변 세분류 데이터 확보 시 추가 가능
KAGGLE_USERNAME = os.getenv("KAGGLE_USERNAME", "")
KAGGLE_KEY = os.getenv("KAGGLE_KEY", "")
HUGGINGFACE_API = os.getenv("HUGGINGFACE_API", "")


def set_seed(seed: int = SEED) -> None:
    """재현성을 위한 시드 고정."""
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = False


def get_device() -> torch.device:
    """사용 가능한 최적 디바이스 반환."""
    if torch.cuda.is_available():
        device = torch.device("cuda")
        logger.info(f"GPU 사용: {torch.cuda.get_device_name(0)}")
    else:
        device = torch.device("cpu")
        logger.warning("GPU를 찾을 수 없습니다. CPU로 실행합니다.")
    return device


def setup_logging() -> None:
    """loguru 로깅 설정."""
    logger.add(
        PROJECT_ROOT / "logs" / "plantcare_{time:YYYY-MM-DD}.log",
        rotation="1 day",
        retention="7 days",
        level="INFO",
        encoding="utf-8",
    )


def ensure_dirs() -> None:
    """필요한 디렉토리 자동 생성."""
    dirs = [
        DATA_RAW_DIR,
        DATA_PROCESSED_DIR,
        DATA_SPLITS_DIR,
        DISEASE_MODEL_DIR,
        SPECIES_MODEL_DIR,
        COMPARISON_DIR,
        MODELS_DIR / "sam",
        DOCS_DIR,
        PROJECT_ROOT / "logs",
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)


ensure_dirs()
