"""
EfficientNet 이미지 분류 모델 학습 스크립트
- Optuna 하이퍼파라미터 최적화
- 80:20 train/test 분할
- TensorBoard 로깅
- tqdm 진행 상황 표시
- 조기 종료 (Early Stopping)
- 최상 모델 저장
"""

import os
import time
import warnings
from pathlib import Path
from typing import Tuple, Dict, Any

import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, Dataset, Subset
from torchvision import transforms, models
from PIL import Image
from tqdm import tqdm
from sklearn.model_selection import train_test_split
import optuna
from optuna.visualization import plot_optimization_history, plot_param_importances
from torch.utils.tensorboard import SummaryWriter

warnings.filterwarnings('ignore')


class PlantDataset(Dataset):
    """식물 이미지 데이터셋 클래스"""
    
    def __init__(self, root_dir: str, transform=None):
        self.root_dir = Path(root_dir)
        self.transform = transform
        self.images = []
        self.labels = []
        self.class_names = []
        
        # 클래스 이름 가져오기
        class_dirs = sorted([d for d in self.root_dir.iterdir() if d.is_dir()])
        self.class_names = [d.name for d in class_dirs]
        self.class_to_idx = {name: idx for idx, name in enumerate(self.class_names)}
        
        # 이미지와 레이블 수집
        for class_dir in class_dirs:
            class_name = class_dir.name
            label = self.class_to_idx[class_name]
            
            for img_path in sorted(class_dir.glob("*.png")) + sorted(class_dir.glob("*.jpg")) + sorted(class_dir.glob("*.jpeg")):
                self.images.append(img_path)
                self.labels.append(label)
    
    def __len__(self):
        return len(self.images)
    
    def __getitem__(self, idx):
        img_path = self.images[idx]
        image = Image.open(img_path).convert('RGB')
        label = self.labels[idx]
        
        if self.transform:
            image = self.transform(image)
        
        return image, label
    
    def get_class_names(self):
        return self.class_names


class EfficientNetModel(nn.Module):
    """EfficientNet 기반 분류 모델"""
    
    def __init__(self, num_classes: int, dropout_rate: float = 0.3):
        super(EfficientNetModel, self).__init__()
        # EfficientNet-B3 사용 (가장 가벼운 버전)
        self.backbone = models.efficientnet_b3(weights=models.EfficientNet_B3_Weights.IMAGENET1K_V1)
        
        # 분류기 수정
        in_features = self.backbone.classifier[1].in_features
        self.backbone.classifier = nn.Sequential(
            nn.Dropout(p=dropout_rate, inplace=True),
            nn.Linear(in_features, num_classes)
        )
    
    def forward(self, x):
        return self.backbone(x)


class EarlyStopping:
    """조기 종료를 위한 클래스"""
    
    def __init__(self, patience: int = 7, min_delta: float = 0.001, mode: str = 'min'):
        self.patience = patience
        self.min_delta = min_delta
        self.mode = mode
        self.counter = 0
        self.best_value = None
        self.early_stop = False
    
    def __call__(self, value: float) -> bool:
        if self.best_value is None:
            self.best_value = value
        elif self.mode == 'min':
            if value > self.best_value - self.min_delta:
                self.counter += 1
                if self.counter >= self.patience:
                    self.early_stop = True
            else:
                self.best_value = value
                self.counter = 0
        else:  # mode == 'max'
            if value < self.best_value + self.min_delta:
                self.counter += 1
                if self.counter >= self.patience:
                    self.early_stop = True
            else:
                self.best_value = value
                self.counter = 0
        
        return self.early_stop


def train_epoch(model, dataloader, criterion, optimizer, device, epoch, writer, global_step):
    """한 에포크 학습"""
    model.train()
    running_loss = 0.0
    correct = 0
    total = 0
    
    pbar = tqdm(dataloader, desc=f'Epoch {epoch+1} [Train]', leave=False)
    for inputs, labels in pbar:
        inputs, labels = inputs.to(device), labels.to(device)
        
        optimizer.zero_grad()
        outputs = model(inputs)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()
        
        running_loss += loss.item()
        _, predicted = outputs.max(1)
        total += labels.size(0)
        correct += predicted.eq(labels).sum().item()
        
        pbar.set_postfix({'loss': f'{loss.item():.4f}', 'acc': f'{100.*correct/total:.2f}%'})
        global_step += 1
    
    epoch_loss = running_loss / len(dataloader)
    epoch_acc = 100. * correct / total
    
    writer.add_scalar('Loss/train', epoch_loss, epoch)
    writer.add_scalar('Accuracy/train', epoch_acc, epoch)
    
    return epoch_loss, epoch_acc, global_step


def validate_epoch(model, dataloader, criterion, device, epoch, writer):
    """한 에포크 검증"""
    model.eval()
    running_loss = 0.0
    correct = 0
    total = 0
    
    with torch.no_grad():
        pbar = tqdm(dataloader, desc=f'Epoch {epoch+1} [Val]  ', leave=False)
        for inputs, labels in pbar:
            inputs, labels = inputs.to(device), labels.to(device)
            
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            
            running_loss += loss.item()
            _, predicted = outputs.max(1)
            total += labels.size(0)
            correct += predicted.eq(labels).sum().item()
            
            pbar.set_postfix({'loss': f'{loss.item():.4f}', 'acc': f'{100.*correct/total:.2f}%'})
    
    epoch_loss = running_loss / len(dataloader)
    epoch_acc = 100. * correct / total
    
    writer.add_scalar('Loss/val', epoch_loss, epoch)
    writer.add_scalar('Accuracy/val', epoch_acc, epoch)
    
    return epoch_loss, epoch_acc


def train_model(trial=None, log_dir='logs', model_save_dir='models', max_epochs=50):
    """모델 학습 함수 (Optuna trial 지원)"""
    
    # 하이퍼파라미터 설정
    if trial is not None:
        # Optuna 하이퍼파라미터 제안
        lr = trial.suggest_float('lr', 1e-5, 1e-2, log=True)
        batch_size = trial.suggest_categorical('batch_size', [16, 32, 64])
        weight_decay = trial.suggest_float('weight_decay', 1e-5, 1e-2, log=True)
        dropout_rate = trial.suggest_float('dropout_rate', 0.2, 0.5)
        momentum = trial.suggest_float('momentum', 0.85, 0.99)
    else:
        # 기본 하이퍼파라미터
        lr = 1e-3
        batch_size = 32
        weight_decay = 1e-4
        dropout_rate = 0.3
        momentum = 0.9
    
    # 장치 설정
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")
    
    # 데이터셋 로드
    data_dir = Path('./data/house_plant_species')
    print(f"Loading dataset from {data_dir}")
    
    full_dataset = PlantDataset(root_dir=data_dir)
    class_names = full_dataset.get_class_names()
    num_classes = len(class_names)
    
    print(f"Found {len(class_names)} classes, {len(full_dataset)} total images")
    
    # 80:20 train/test 분할
    indices = list(range(len(full_dataset)))
    train_indices, val_indices = train_test_split(
        indices, test_size=0.2, random_state=42, stratify=full_dataset.labels
    )
    
    print(f"Train samples: {len(train_indices)}, Val samples: {len(val_indices)}")
    
    # 데이터 증강
    train_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.RandomHorizontalFlip(p=0.5),
        transforms.RandomRotation(degrees=15),
        transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])
    
    val_transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])
    
    # Subset 생성
    train_dataset = Subset(full_dataset, train_indices)
    val_dataset = Subset(full_dataset, val_indices)
    
    # Subset의 transform 설정을 위해 custom collate
    class SubsetTransformed:
        def __init__(self, subset, transform):
            self.subset = subset
            self.transform = transform
        
        def __getitem__(self, idx):
            img, label = self.subset[idx]
            return self.transform(img), label
        
        def __len__(self):
            return len(self.subset)
    
    train_dataset = SubsetTransformed(
        Subset(full_dataset, train_indices), train_transform
    )
    val_dataset = SubsetTransformed(
        Subset(full_dataset, val_indices), val_transform
    )
    
    # DataLoader 생성
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False, num_workers=0)
    
    # 모델 생성
    model = EfficientNetModel(num_classes=num_classes, dropout_rate=dropout_rate)
    model = model.to(device)
    
    # 손실 함수 및 옵티마이저
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.SGD(
        model.parameters(),
        lr=lr,
        momentum=momentum,
        weight_decay=weight_decay
    )
    
    # 학습률 스케줄러
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode='min', factor=0.5, patience=5
    )
    
    # TensorBoard 설정
    if trial is not None:
        trial_id = trial.number
        run_name = f"trial_{trial_id}"
    else:
        run_name = f"best_model_{int(time.time())}"
    
    run_log_dir = os.path.join(log_dir, run_name)
    writer = SummaryWriter(log_dir=run_log_dir)
    
    if trial is not None:
        writer.add_text('Hyperparameters', str(trial.params))
    
    # 조기 종료 설정
    early_stopping = EarlyStopping(patience=10, min_delta=0.001, mode='min')
    
    # 최상 모델 저장 경로
    os.makedirs(model_save_dir, exist_ok=True)
    best_model_path = os.path.join(model_save_dir, f"best_model_{run_name}.pth")
    best_val_loss = float('inf')
    
    # 학습 루프
    global_step = 0
    print("\nStarting training...")
    
    for epoch in range(max_epochs):
        # 학습
        train_loss, train_acc, global_step = train_epoch(
            model, train_loader, criterion, optimizer, device, epoch, writer, global_step
        )
        
        # 검증
        val_loss, val_acc = validate_epoch(
            model, val_loader, criterion, device, epoch, writer
        )
        
        # 학습률 스케줄러 업데이트
        scheduler.step(val_loss)
        
        # 현재 학습률 기록
        current_lr = optimizer.param_groups[0]['lr']
        writer.add_scalar('LearningRate', current_lr, epoch)
        
        # 결과 출력
        print(f"\nEpoch {epoch+1}/{max_epochs}")
        print(f"  Train Loss: {train_loss:.4f}, Train Acc: {train_acc:.2f}%")
        print(f"  Val Loss: {val_loss:.4f}, Val Acc: {val_acc:.2f}%")
        print(f"  Learning Rate: {current_lr:.6f}")
        
        # 최상 모델 저장
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'val_loss': val_loss,
                'val_acc': val_acc,
                'hyperparameters': trial.params if trial else {}
            }, best_model_path)
            print(f"  ✓ Model saved (val_loss: {val_loss:.4f})")
        
        # 조기 종료 확인
        if early_stopping(val_loss):
            print(f"\nEarly stopping triggered at epoch {epoch+1}")
            break
        
        # Optuna의 경우 중간 보고
        if trial is not None:
            trial.report(val_loss, epoch)
            
            # Optuna의 조기 종료
            if trial.should_prune():
                raise optuna.TrialPruned()
    
    writer.close()
    
    return best_val_loss, val_acc


def objective(trial):
    """Optuna 목적 함수"""
    try:
        val_loss, val_acc = train_model(
            trial=trial,
            log_dir='logs/optuna',
            model_save_dir='models/optuna',
            max_epochs=30  # Optuna 탐색 시 에포크 수
        )
        return val_loss  # 손실 최소화
    except optuna.TrialPruned:
        raise
    except Exception as e:
        print(f"Trial {trial.number} failed: {e}")
        return float('inf')


def main():
    """메인 함수"""
    print("=" * 60)
    print("EfficientNet 식물 분류 모델 학습")
    print("=" * 60)
    
    # 1. Optuna 하이퍼파라미터 최적화
    print("\n[1/3] Optuna 하이퍼파라미터 최적화 시작...")
    
    study = optuna.create_study(
        direction='minimize',
        study_name='efficientnet_plant_classification',
        storage=None,  # 메모리 상에서 실행
        load_if_exists=False
    )
    
    # 20번의 trial로 최적화 (필요시 조정)
    n_trials = 20
    print(f"Running {n_trials} trials...")
    
    try:
        study.optimize(objective, n_trials=n_trials, timeout=3600*3, n_jobs=1)  # 최대 3시간, 순차 실행
    except KeyboardInterrupt:
        print("\nOptimization interrupted by user")
    
    print("\n" + "=" * 60)
    print("Optuna 최적화 완료!")
    print(f"Best trial:")
    print(f"  Value: {study.best_trial.value:.4f}")
    print(f"  Params: {study.best_trial.params}")
    print("=" * 60)
    
    # Optuna 시각화 저장
    try:
        fig1 = plot_optimization_history(study)
        fig1.write_image("optuna_optimization_history.png")
        
        fig2 = plot_param_importances(study)
        fig2.write_image("optuna_param_importances.png")
        print("Optuna 시각화 그래프 저장 완료")
    except Exception as e:
        print(f"시각화 저장 실패: {e}")
    
    # 2. 최상 하이퍼파라미터로 재학습
    print("\n[2/3] 최상 하이퍼파라미터로 재학습 시작...")
    
    best_params = study.best_trial.params
    print(f"Best parameters: {best_params}")
    
    # Optuna에서 찾은 최상 파라미터로 더 많은 에포크로 재학습
    val_loss, val_acc = train_model(
        trial=None,  # 기본 파라미터 사용
        log_dir='logs/final',
        model_save_dir='models/final',
        max_epochs=100  # 더 많은 에포크로 학습
    )
    
    # 3. 결과 요약
    print("\n" + "=" * 60)
    print("학습 완료!")
    print(f"최종 검증 손실: {val_loss:.4f}")
    print(f"최종 검증 정확도: {val_acc:.2f}%")
    print("=" * 60)
    
    # TensorBoard 실행 방법 안내
    print("\nTensorBoard 확인 방법:")
    print("  tensorboard --logdir=logs")
    print("  브라우저에서 http://localhost:6006 접속")


if __name__ == "__main__":
    main()