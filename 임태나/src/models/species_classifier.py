"""종 식별 모델 정의.

House Plant Species 47종 식별을 위한 모델을 정의한다.
EfficientNet-B3을 재사용한다.
"""

import torch.nn as nn

from src.config import LR_BACKBONE, LR_FC, SPECIES_NUM_CLASSES
from src.models.disease_classifier import create_efficientnet_b3


def create_species_model(
    num_classes: int = SPECIES_NUM_CLASSES, pretrained: bool = True
) -> nn.Module:
    """종 식별 모델 생성.

    Args:
        num_classes: 종 클래스 수 (기본 47).
        pretrained: ImageNet 사전학습 가중치 사용 여부.

    Returns:
        EfficientNet-B3 기반 종 식별 모델.
    """
    return create_efficientnet_b3(num_classes, pretrained=pretrained)


def get_species_parameter_groups(
    model: nn.Module,
    lr_fc: float = LR_FC,
    lr_backbone: float = LR_BACKBONE,
) -> list[dict]:
    """종 식별 모델의 차등 학습률 파라미터 그룹 반환."""
    backbone_params = []
    fc_params = []

    for name, param in model.named_parameters():
        if name.startswith("classifier"):
            fc_params.append(param)
        else:
            backbone_params.append(param)

    return [
        {"params": backbone_params, "lr": lr_backbone},
        {"params": fc_params, "lr": lr_fc},
    ]
