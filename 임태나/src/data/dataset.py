"""PyTorch Dataset 및 DataLoader 생성 모듈.

전처리된 이미지 폴더에서 Dataset을 생성하고, 학습/검증/테스트 DataLoader를 반환한다.
"""

import json
from pathlib import Path

import torch
from PIL import Image
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms

from src.config import BATCH_SIZE, IMAGE_SIZE, IMAGENET_MEAN, IMAGENET_STD


class PlantDataset(Dataset):
    """이미지 폴더 기반 PyTorch Dataset.

    Args:
        root_dir: 클래스별 서브폴더가 있는 루트 경로.
        transform: 이미지 변환 파이프라인.
        class_to_idx: 클래스명→인덱스 매핑. None이면 자동 생성.
    """

    IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

    def __init__(
        self,
        root_dir: Path,
        transform: transforms.Compose | None = None,
        class_to_idx: dict[str, int] | None = None,
    ) -> None:
        self.root_dir = Path(root_dir)
        self.transform = transform

        if class_to_idx is not None:
            self.class_to_idx = class_to_idx
        else:
            self.class_to_idx = self._build_class_to_idx()

        self.idx_to_class = {v: k for k, v in self.class_to_idx.items()}
        self.samples = self._collect_samples()

    def _build_class_to_idx(self) -> dict[str, int]:
        """서브디렉토리 이름으로 클래스 매핑 자동 생성."""
        class_names = sorted(
            d.name for d in self.root_dir.iterdir() if d.is_dir()
        )
        return {name: idx for idx, name in enumerate(class_names)}

    def _collect_samples(self) -> list[tuple[Path, int]]:
        """(이미지 경로, 라벨) 튜플 리스트 수집."""
        samples = []
        for class_name, class_idx in self.class_to_idx.items():
            class_dir = self.root_dir / class_name
            if not class_dir.exists():
                continue
            for img_path in class_dir.rglob("*"):
                if img_path.suffix.lower() in self.IMAGE_EXTENSIONS:
                    samples.append((img_path, class_idx))
        return samples

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, int]:
        img_path, label = self.samples[idx]
        image = Image.open(img_path).convert("RGB")
        if self.transform:
            image = self.transform(image)
        return image, label


def get_train_transforms(image_size: int = IMAGE_SIZE) -> transforms.Compose:
    """학습용 이미지 변환 파이프라인.

    CLAHE는 전처리 단계에서 이미 적용됨. 여기선 증강 + 정규화만.
    """
    return transforms.Compose([
        transforms.Resize((image_size, image_size)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomAffine(degrees=30, scale=(0.8, 1.2)),
        transforms.RandomPerspective(distortion_scale=0.2, p=0.3),
        transforms.ColorJitter(brightness=0.5, contrast=0.5, saturation=0.3, hue=0.1),
        transforms.GaussianBlur(kernel_size=3, sigma=(0.1, 2.0)),
        transforms.ToTensor(),
        transforms.RandomErasing(p=0.1),
        transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
    ])


def get_eval_transforms(image_size: int = IMAGE_SIZE) -> transforms.Compose:
    """평가용 이미지 변환 파이프라인 (증강 없음)."""
    return transforms.Compose([
        transforms.Resize((image_size, image_size)),
        transforms.ToTensor(),
        transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
    ])


def load_class_to_idx(splits_dir: Path) -> dict[str, int] | None:
    """splits 디렉토리에서 class_to_idx.json 로드."""
    mapping_path = splits_dir / "class_to_idx.json"
    if mapping_path.exists():
        with open(mapping_path, encoding="utf-8") as f:
            return json.load(f)
    return None


def create_dataloaders(
    splits_dir: Path,
    batch_size: int = BATCH_SIZE,
    num_workers: int = 0,
) -> dict[str, DataLoader]:
    """train/val/test DataLoader 생성.

    Args:
        splits_dir: 스플릿 디렉토리 (train/, val/, test/ 서브폴더 포함).
        batch_size: 배치 크기.
        num_workers: DataLoader 워커 수 (Windows 기본 0).

    Returns:
        {"train": DataLoader, "val": DataLoader, "test": DataLoader}.
    """
    class_to_idx = load_class_to_idx(splits_dir)
    use_cuda = torch.cuda.is_available()

    loaders = {}
    for split_name, is_train in [("train", True), ("val", False), ("test", False)]:
        split_path = splits_dir / split_name
        if not split_path.exists():
            continue

        transform = get_train_transforms() if is_train else get_eval_transforms()
        dataset = PlantDataset(split_path, transform=transform, class_to_idx=class_to_idx)

        loaders[split_name] = DataLoader(
            dataset,
            batch_size=batch_size,
            shuffle=is_train,
            num_workers=num_workers,
            pin_memory=use_cuda,
        )

    return loaders
