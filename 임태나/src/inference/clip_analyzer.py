"""
CLIP 기반 식물 상태 분석.
EfficientNet 신뢰도가 낮을 때 폴백으로 사용.
이미지를 텍스트 설명으로 변환하여 LLM에 전달.
"""
import logging
import torch
from PIL import Image
from pathlib import Path
from transformers import CLIPProcessor, CLIPModel

logger = logging.getLogger(__name__)

# 모델 싱글턴
_model = None
_processor = None
_device = None


def _load_clip():
    """CLIP 모델 로드 (최초 1회)"""
    global _model, _processor, _device
    if _model is not None:
        return

    _device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info(f"CLIP 로딩 중... (device: {_device})")

    _model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(_device)
    _processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
    _model.eval()
    logger.info("CLIP 로드 완료")


# ==========================================
# 식물 상태 후보 텍스트 (CLIP이 비교할 대상)
# ==========================================
PLANT_CONDITIONS = [
    # 병변 관련
    "a healthy green plant leaf",
    "a plant leaf with brown spots and blight disease",
    "a plant leaf with white powdery mildew fungus",
    "a plant leaf with yellow mosaic virus pattern",
    "a plant leaf with orange rust spots on the underside",
    "a plant leaf curling and deformed",
    "a plant leaf with gray mold on the surface",
    "a plant leaf with bacterial dark spots and holes",
    "a plant leaf with scab and rot damage",
    # 상태 관련
    "a wilting drooping plant that needs water",
    "a plant with yellowing leaves from overwatering",
    "a plant with brown crispy leaf tips from dryness",
    "a plant with leggy stretched growth from low light",
    "a plant with sunburned bleached leaves",
    "a plant with pest insects on leaves",
    "a plant with root rot and mushy stems",
    "a plant with nutrient deficiency pale leaves",
    "a newly repotted plant in fresh soil",
]

# 한글 매핑
CONDITION_KOREAN = {
    "a healthy green plant leaf": "건강한 녹색 잎",
    "a plant leaf with brown spots and blight disease": "갈색 반점과 마름병",
    "a plant leaf with white powdery mildew fungus": "흰가루병 (곰팡이)",
    "a plant leaf with yellow mosaic virus pattern": "모자이크 바이러스 패턴",
    "a plant leaf with orange rust spots on the underside": "녹병 (주황색 포자)",
    "a plant leaf curling and deformed": "잎 말림/변형",
    "a plant leaf with gray mold on the surface": "잿빛곰팡이",
    "a plant leaf with bacterial dark spots and holes": "세균성 반점 (구멍)",
    "a plant leaf with scab and rot damage": "딱지병/부패",
    "a wilting drooping plant that needs water": "시들고 처진 상태 (물 부족)",
    "a plant with yellowing leaves from overwatering": "과습으로 잎이 노랗게",
    "a plant with brown crispy leaf tips from dryness": "건조해서 잎 끝이 갈변",
    "a plant with leggy stretched growth from low light": "빛 부족으로 웃자람",
    "a plant with sunburned bleached leaves": "직사광 화상",
    "a plant with pest insects on leaves": "벌레/해충",
    "a plant with root rot and mushy stems": "뿌리 무름",
    "a plant with nutrient deficiency pale leaves": "영양 부족 (잎 창백)",
    "a newly repotted plant in fresh soil": "새로 분갈이한 식물",
}


def analyze_image(image_path: str, top_k: int = 3) -> list[dict]:
    """
    이미지를 CLIP으로 분석하여 상위 k개 상태 반환.

    Args:
        image_path: 이미지 파일 경로
        top_k: 반환할 상위 결과 수

    Returns:
        [{"condition": "갈색 반점과 마름병", "confidence": 0.82, "en": "..."}, ...]
    """
    _load_clip()

    # 이미지 로드 (한글 경로 대응)
    image = Image.open(image_path).convert("RGB")

    # CLIP 추론
    inputs = _processor(
        text=PLANT_CONDITIONS,
        images=image,
        return_tensors="pt",
        padding=True
    ).to(_device)

    with torch.no_grad():
        outputs = _model(**inputs)
        logits = outputs.logits_per_image[0]  # [num_texts]
        probs = logits.softmax(dim=0)

    # 상위 k개
    top_probs, top_indices = probs.topk(top_k)

    results = []
    for prob, idx in zip(top_probs, top_indices):
        en_text = PLANT_CONDITIONS[idx.item()]
        results.append({
            "condition": CONDITION_KOREAN.get(en_text, en_text),
            "condition_en": en_text,
            "confidence": round(prob.item(), 3),
        })

    return results


def describe_plant_state(image_path: str) -> str:
    """
    이미지를 분석하여 한글 텍스트 설명 반환.
    LLM 프롬프트에 바로 넣을 수 있는 형태.

    Returns:
        "CLIP 분석 결과: 갈색 반점과 마름병(82%), 과습으로 잎이 노랗게(12%)"
    """
    results = analyze_image(image_path, top_k=3)

    if not results:
        return "식물 상태를 분석하지 못했습니다."

    parts = []
    for r in results:
        if r["confidence"] >= 0.05:  # 5% 이상만
            parts.append(f"{r['condition']}({r['confidence']*100:.0f}%)")

    if not parts:
        return "식물 상태가 명확하지 않습니다."

    return f"CLIP 분석 결과: {', '.join(parts)}"


# ==========================================
# 테스트
# ==========================================
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("사용법: python -m src.inference.clip_analyzer <이미지경로>")
        sys.exit(1)

    path = sys.argv[1]
    print(f"분석 중: {path}")
    results = analyze_image(path)
    for r in results:
        print(f"  {r['condition']}: {r['confidence']*100:.1f}%")
    print()
    print(describe_plant_state(path))
