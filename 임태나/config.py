# src/config.py
# 이 파일은 프로젝트의 설정 본부
# 모든 경로, API 키, 숫자 설정을 여기에 모음
# 다른 파일에서는 여기서 import 해서 쓰면 됨

from pathlib import Path
from dotenv import load_dotenv
import os

# .env 파일에서 비밀번호들 읽기
load_dotenv()

# 경로 설정
# Path(__file__)은 이 파일(config.py)의 위치
# .parent는 부모 폴더, .parent.parent는 부모의 부모 폴더
# config.py가 src/안에 있으니까, .parent.parent는 프로젝트 루프(c:\plantcare)임. 

PROJECT_DIR = Path(__file__).parent.parent
DATA_DIR = PROJECT_DIR / "data"
RAW_DIR = DATA_DIR/ "raw"
PROCESSED_DIR = DATA_DIR / "processed"
MODEL_DIR = "PROJECT_DIR" / "models"

# API 키
# os.getenv("이름", "기본값")은 ".env에서 이 이름의 값을 가져와. 없으면 기본값 써"
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")


# 모델 설정
IMAGE_SIZE = 224
BATCH_SIZE = 32
NUM_DISEASE = 7
NUM_SPECIES  = 47 


# 병변 유형 목록
DISEASE_TYPES = [
    "healthy", #건강
    "powdery_mildew",
    "rust",
    "leaf_curl",
    "blight_spot",
    "leaf__mold",
    "mosaic_virus",
    "scab_rot", 
]
