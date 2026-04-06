"""병변 분류 모델 정의.

EfficientNet-B3과 ConvNeXt-Tiny 모델을 정의하고, 전이 학습을 위한
분류층 교체 및 차등 학습률 파라미터 그룹을 제공한다.
"""

import torch.nn as nn
from torchvision import models
from torchvision.models import ConvNeXt_Tiny_Weights, EfficientNet_B3_Weights

from src.config import LR_BACKBONE, LR_FC


def create_efficientnet_b3(num_classes: int, pretrained: bool = True) -> nn.Module:
    """EfficientNet-B3 모델 생성.

    Args:
        num_classes: 출력 클래스 수.
        pretrained: ImageNet 사전학습 가중치 사용 여부.

    Returns:
        분류층이 교체된 EfficientNet-B3 모델.
    """
    weights = EfficientNet_B3_Weights.DEFAULT if pretrained else None
    model = models.efficientnet_b3(weights=weights)
    in_features = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(in_features, num_classes)
    return model


def create_convnext_tiny(num_classes: int, pretrained: bool = True) -> nn.Module:
    """ConvNeXt-Tiny 모델 생성.

    Args:
        num_classes: 출력 클래스 수.
        pretrained: ImageNet 사전학습 가중치 사용 여부.

    Returns:
        분류층이 교체된 ConvNeXt-Tiny 모델.
    """
    weights = ConvNeXt_Tiny_Weights.DEFAULT if pretrained else None
    model = models.convnext_tiny(weights=weights)
    in_features = model.classifier[2].in_features
    model.classifier[2] = nn.Linear(in_features, num_classes)
    return model


def replace_classifier_for_finetune(
    model: nn.Module, new_num_classes: int, architecture: str
) -> nn.Module:
    """파인튜닝을 위해 분류층 교체 (38→7 클래스 등).

    Args:
        model: 사전학습 완료된 모델.
        new_num_classes: 새 클래스 수.
        architecture: "efficientnet_b3" 또는 "convnext_tiny".

    Returns:
        분류층이 교체된 모델.
    """
    if architecture == "efficientnet_b3":
        in_features = model.classifier[1].in_features
        model.classifier[1] = nn.Linear(in_features, new_num_classes)
    elif architecture == "convnext_tiny":
        in_features = model.classifier[2].in_features
        model.classifier[2] = nn.Linear(in_features, new_num_classes)
    else:
        raise ValueError(f"지원하지 않는 아키텍처: {architecture}")
    return model


def get_parameter_groups(
    model: nn.Module,
    architecture: str,
    lr_fc: float = LR_FC,
    lr_backbone: float = LR_BACKBONE,
) -> list[dict]:
    """차등 학습률 파라미터 그룹 반환.

    Args:
        model: 대상 모델.
        architecture: "efficientnet_b3" 또는 "convnext_tiny".
        lr_fc: 분류층 학습률.
        lr_backbone: 백본 학습률.

    Returns:
        [{"params": backbone, "lr": lr_backbone}, {"params": fc, "lr": lr_fc}].
    """
    classifier_prefix = "classifier"
    backbone_params = []
    fc_params = []

    for name, param in model.named_parameters():
        if name.startswith(classifier_prefix):
            fc_params.append(param)
        else:
            backbone_params.append(param)

    return [
        {"params": backbone_params, "lr": lr_backbone},
        {"params": fc_params, "lr": lr_fc},
    ]
