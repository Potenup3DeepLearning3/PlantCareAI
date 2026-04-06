# src/data/download.py
# 이 파일은 인터넷에서 데이터를 다운 받아서 data/raw/폴더에 저장

from datasets import load_dataset
from pathlib import Path
import os
from src.config import RAW_DIR

def download_plantvillage():
    """
    "PlantVillage 데이터셋 다운로드.

    54,000장의 식물 잎 사진. 38개 클래스 (토마토_역병, 사과_흰가루병 등).
    이미 다운받았으면 건너뛰어요.
    """
    save_dir = RAW_DIR / "plantvillage"

# 이미 있는지 확인 - 있으면 
    if save_dir.exists() and len(list(save_dir.glob("*/*.jpg"))) > 100:
        print(f"Plantvillage 이미 존재 ({save_dir}). 건너뜀")
        return
    
    print("PlantVillage 다운로드 시작... ")

    # HuggingFace에서 데이터셋 불러오기
    ds = load_dataset("BrandonFors/Plant-Diseases-PlantVillage-Dataset")

    # 이미지를 클래스별 폴더에 저장 
