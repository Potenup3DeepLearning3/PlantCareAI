# 모델 아키텍처 (7개)

## 비전 (4개)
| 모델 | 역할 | 학습 방식 |
|------|------|----------|
| EfficientNet-B3 / ConvNeXt-Tiny | 병변 유형 7클래스 분류 | PlantVillage 재분류 사전학습 → 스크래핑 데이터 파인튜닝 |
| 종 식별 모델 (동일 백본) | 47종 반려식물 분류 | House Plant Species 학습 |
| SAM / FastSAM | 병변 세그멘테이션 + 면적 비율 | 사전학습 그대로 |
| EasyOCR | 약제 라벨 성분 추출 (한국어) | 사전학습 그대로 |

## 텍스트/음성 (3개)
| 모델 | 역할 | 실행 방식 |
|------|------|----------|
| Ollama qwen2.5:14b | 케어 가이드 생성 | 로컬 localhost:11434 |
| Whisper large-v3 | 음성 → 텍스트 (한국어) | 로컬 (RTX 5070) |
| gTTS | 텍스트 → 음성 | API (무료, 키 불필요) |

## 모델 비교 실험
- EfficientNet-B3 vs ConvNeXt-Tiny 동일 조건 학습
- 비교 항목: val_accuracy, val_f1, 학습 시간, 추론 속도
- 결과 → models/comparison/comparison_results.json
- 높은 쪽 → models/disease/best_model.pth

## Transfer Learning 절차
1. PlantVillage 재분류(7클래스)로 전체 모델 학습
2. Day 4 스크래핑 데이터로 마지막 층 교체 + 파인튜닝
3. 차등 학습률: 새 층 lr=1e-3, 기존 층 lr=1e-5

## 전처리
- CLAHE: clipLimit=2.0, tileGridSize=(8,8)
- 리사이즈: 224x224
- 정규화: ImageNet mean/std
- 학습 증강: RandomHorizontalFlip, RandomRotation(15), ColorJitter(0.3, 0.3, 0.2)
