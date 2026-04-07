"""
CLIP 기반 식물 상태 분석.
EfficientNet 신뢰도가 낮을 때 폴백으로 사용.
clip_conditions.json (UC Davis IPM 출처) 기반 분석.
"""
import json
import logging
import torch
from PIL import Image
from pathlib import Path
from transformers import CLIPProcessor, CLIPModel

logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent.parent / "data"
CLIP_CONDITIONS_JSON = DATA_DIR / "clip_conditions.json"

# 모델 싱글턴
_model = None
_processor = None
_device = None
_conditions: list[dict] = []   # clip_conditions.json에서 로드


def _load_clip():
    """CLIP 모델 + clip_conditions.json 로드 (최초 1회)"""
    global _model, _processor, _device, _conditions
    if _model is not None:
        return

    _device = "cuda" if torch.cuda.is_available() else "cpu"
    logger.info(f"CLIP 로딩 중... (device: {_device})")

    _model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(_device)
    _processor = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
    _model.eval()

    # clip_conditions.json 로드
    if CLIP_CONDITIONS_JSON.exists():
        with open(CLIP_CONDITIONS_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
        _conditions = data.get("conditions", [])
        logger.info(f"clip_conditions.json 로드 완료 ({len(_conditions)}개 조건, UC Davis IPM 출처)")
    else:
        logger.warning(f"clip_conditions.json 없음: {CLIP_CONDITIONS_JSON}")
        _conditions = _get_fallback_conditions()

    logger.info("CLIP 로드 완료")


def _get_fallback_conditions() -> list[dict]:
    """clip_conditions.json이 없을 때 기본 후보 목록."""
    return [
        {"id": c[0], "clip_text_en": c[1], "condition_kr": c[2],
         "symptoms": "", "treatment": "", "source": "fallback"}
        for c in [
            ("overwatering",  "a houseplant with yellowing leaves from overwatering", "과습 (물 과다)"),
            ("underwatering", "a wilting drooping houseplant with dry crispy soil",    "건조 (물 부족)"),
            ("powdery_mildew","a plant leaf with white powdery mildew fungus",         "흰가루병"),
            ("healthy",       "a healthy vibrant green houseplant",                    "건강한 식물"),
            ("pest",          "a houseplant with pest insects on leaves",               "벌레/해충"),
            ("low_light",     "a houseplant with leggy stretched thin stems from insufficient light", "빛 부족"),
            ("sunburn",       "a houseplant with bleached scorched leaves from direct sunlight",      "직사광 화상"),
            ("root_rot",      "a plant with root rot and mushy soft stems",            "뿌리 무름"),
        ]
    ]


def analyze_image(image_path: str, top_k: int = 3) -> list[dict]:
    """이미지를 CLIP으로 분석하여 상위 k개 상태 반환.

    Returns:
        [{"condition_kr": "과습", "confidence": 0.82, "symptoms": "...",
          "treatment": "...", "source": "UC Davis IPM"}]
    """
    _load_clip()

    image = Image.open(image_path).convert("RGB")
    texts = [c["clip_text_en"] for c in _conditions]

    inputs = _processor(
        text=texts,
        images=image,
        return_tensors="pt",
        padding=True,
    ).to(_device)

    with torch.no_grad():
        probs = _model(**inputs).logits_per_image[0].softmax(dim=0)

    top_probs, top_indices = probs.topk(min(top_k, len(_conditions)))

    results = []
    for prob, idx in zip(top_probs, top_indices):
        if prob.item() < 0.05:
            continue
        c = _conditions[idx.item()]
        results.append({
            "id": c.get("id", ""),
            "condition_kr": c.get("condition_kr", ""),
            "confidence": round(prob.item(), 3),
            "symptoms": c.get("symptoms", ""),
            "treatment": c.get("treatment", ""),
            "source": c.get("source", ""),
        })

    return results


def describe_plant_state(image_path: str) -> tuple[str, list[dict]]:
    """이미지를 분석하여 (한글 설명 텍스트, 상세 결과 리스트) 반환.

    Returns:
        ("CLIP 분석: 과습(65%), 빛부족(20%)", [{"condition_kr":..., "treatment":...}])
    """
    results = analyze_image(image_path, top_k=3)

    if not results:
        return "상태를 파악하기 어려움", []

    description = "CLIP 분석: " + ", ".join(
        f"{r['condition_kr']}({r['confidence']*100:.0f}%)" for r in results
    )
    return description, results


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
