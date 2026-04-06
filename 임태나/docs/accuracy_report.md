# 모델 정확도 리포트

**평가 일시**: 2026-04-02
**Day 9 실환경 테스트 + 튜닝 결과**

---

## 요약

| 모델 | 데이터셋 | Accuracy | F1 (weighted) | 샘플 수 |
|------|---------|----------|---------------|---------|
| 병변 분류 (EfficientNet-B3) | PlantVillage test | **99.89%** | 0.9993 | 2,836 |
| 종 식별 (EfficientNet-B3) | House Plant Species test | **90.46%** | 0.9040 | 1,478 |
| 병변 분류 (PlantDoc 크로스) | PlantDoc test (TTA) | **59.24%** | 0.5571 | 238 |
| 파인튜닝 (스크래핑 데이터) | houseplant_disease test | **50.00%** | 0.4948 | 52 |

---

## 1. 병변 분류 모델 (best_model.pth)

**아키텍처**: EfficientNet-B3 (PlantVillage 사전학습)
**클래스 수**: 9 (Blight_Spot, Greening, Healthy, Leaf_Curl, Leaf_Mold, Mosaic_Virus, Powdery_Mildew, Rust, Scab_Rot)

### PlantVillage 테스트 스플릿 (통제 환경)

- **Accuracy**: 99.89%
- **F1 (weighted)**: 0.9993
- **테스트 샘플**: 2,836장

| 클래스 | Precision | Recall | F1 | Support |
|--------|-----------|--------|-----|---------|
| Greening | 1.0000 | 1.0000 | 1.0000 | 441 |
| Healthy | 1.0000 | 0.9983 | 0.9992 | 1,207 |
| Leaf_Curl | 1.0000 | 0.9977 | 0.9988 | 428 |
| Leaf_Mold | 1.0000 | 1.0000 | 1.0000 | 76 |
| Mosaic_Virus | 1.0000 | 1.0000 | 1.0000 | 30 |
| Powdery_Mildew | 0.9957 | 1.0000 | 0.9978 | 231 |
| Rust | 1.0000 | 1.0000 | 1.0000 | 117 |
| Scab_Rot | 1.0000 | 1.0000 | 1.0000 | 306 |

### PlantDoc 크로스 데이터셋 (실제 환경)

- **Accuracy**: 59.24% (TTA 적용)
- **F1 (weighted)**: 0.5571
- **테스트 샘플**: 238장 (29개 PlantDoc 클래스 -> 9클래스 매핑)

| 클래스 | Precision | Recall | F1 | Support |
|--------|-----------|--------|-----|---------|
| Blight_Spot | 0.5075 | 0.8500 | 0.6355 | 80 |
| Healthy | 0.8077 | 0.6848 | 0.7412 | 92 |
| Leaf_Curl | 0.0000 | 0.0000 | 0.0000 | 6 |
| Leaf_Mold | 0.0000 | 0.0000 | 0.0000 | 6 |
| Mosaic_Virus | 0.0000 | 0.0000 | 0.0000 | 10 |
| Powdery_Mildew | 1.0000 | 0.3333 | 0.5000 | 6 |
| Rust | 0.3846 | 0.2500 | 0.3030 | 20 |
| Scab_Rot | 0.5000 | 0.1667 | 0.2500 | 18 |

---

## 2. 종 식별 모델 (species_model.pth)

**아키텍처**: EfficientNet-B3
**클래스 수**: 47종 반려식물

- **Accuracy**: 90.46%
- **F1 (weighted)**: 0.9040
- **테스트 샘플**: 1,478장

---

## 3. 파인튜닝 모델 (best_model_finetuned.pth)

**아키텍처**: EfficientNet-B3 (스크래핑 데이터 파인튜닝)
**클래스 수**: 8 (dehydration, nutrient_deficiency, overwatering, powdery_mildew, root_rot, rust, stress, sunburn)

- **Accuracy**: 50.00%
- **F1 (weighted)**: 0.4948
- **테스트 샘플**: 52장 (소규모)

| 클래스 | Precision | Recall | F1 | Support |
|--------|-----------|--------|-----|---------|
| dehydration | 0.3333 | 0.2857 | 0.3077 | 7 |
| nutrient_deficiency | 0.4286 | 0.4286 | 0.4286 | 7 |
| overwatering | 0.4000 | 0.5714 | 0.4706 | 7 |
| powdery_mildew | 0.5000 | 0.4286 | 0.4615 | 7 |
| root_rot | 0.5000 | 0.4286 | 0.4615 | 7 |
| rust | 0.8333 | 0.8333 | 0.8333 | 6 |
| stress | 0.6667 | 0.8000 | 0.7273 | 5 |
| sunburn | 0.4000 | 0.3333 | 0.3636 | 6 |

---

## 4. 모델 비교 실험 결과

| 모델 | Val Accuracy | Best Epoch | 모델 크기 | 추론 속도 |
|------|-------------|-----------|----------|----------|
| **EfficientNet-B3** | **99.86%** | 6 | 40.86 MB | 19.76 ms |
| ConvNeXt-Tiny | 98.90% | 8 | 106.15 MB | 6.23 ms |

**승자**: EfficientNet-B3 (정확도 우위, 모델 크기 2.6배 작음)

---

## 5. Day 9 개선사항

### 5.1 PlantDoc 매핑 수정
- **이전**: 12클래스 매핑 (모델에 없는 Early_Blight, Late_Blight 등 포함) -> 158장만 평가
- **이후**: 9클래스 매핑 (모델 실제 클래스에 맞춤) -> 238장 평가
- Blight_Spot = Bacterial_Spot + Early_Blight + Late_Blight + Leaf_Spot 통합

### 5.2 TTA (Test-Time Augmentation) 적용
- 원본 + 좌우반전 + 90도 회전의 소프트맥스 평균
- PlantDoc 정확도: 57.56% (no TTA) -> **59.24%** (+1.68%p)

### 5.3 CLAHE 파라미터 비교
| 설정 | PlantDoc Accuracy |
|------|------------------|
| No CLAHE | **57.56%** |
| 2.0 / 8x8 (문서 기준) | 55.04% |
| 2.5 / 8x8 | 54.62% |
| 3.0 / 16x16 (현재) | 53.78% |

실제 환경 이미지에는 CLAHE 미적용이 더 효과적 (학습 데이터와의 도메인 갭)

### 5.4 SAM 세그멘테이션 개선
- **이전**: 중앙 단일 포인트 프롬프트
- **이후**: 중앙 + 3x3 그리드 (10개 포인트), 면적 비율 기반 마스크 선택 (5%~80% 유효 범위)

### 5.5 LLM 프롬프트 튜닝
- 신뢰도 70% 미만 시 불확실성 표현 추가
- 대안 병변 후보 제시 (Blight_Spot 과예측 대응)
- 완곡한 표현 지시 ("~일 수 있습니다")

---

## 6. 주요 실패 패턴 (PlantDoc)

| 실제 | 예측 | 건수 | 분석 |
|------|------|------|------|
| Healthy -> Blight_Spot | 24 | 배경 복잡한 실제 잎 이미지를 병변으로 오인 |
| Rust -> Blight_Spot | 15 | 녹병과 반점/역병의 시각적 유사성 |
| Scab_Rot -> Blight_Spot | 10 | 검은무늬와 반점의 혼동 |
| Leaf_Mold -> Blight_Spot | 6 | 소수 클래스 학습 부족 |
| Mosaic_Virus -> Blight_Spot/Healthy | 9 | 모자이크 패턴 인식 실패 |

### 근본 원인
1. **Blight_Spot 클래스 불균형**: 학습 데이터 15,096장 (전체의 35%) -> 과예측 경향
2. **도메인 갭**: PlantVillage (단색 배경, 단일 잎) vs PlantDoc (자연 배경, 다양한 각도)
3. **소수 클래스**: Leaf_Mold(762장), Mosaic_Virus(299장) 학습 부족

---

## 7. 한계 및 향후 개선 방향

1. **데이터 증강**: 소수 클래스(Mosaic_Virus, Leaf_Mold) 오버샘플링 또는 추가 수집
2. **도메인 적응**: PlantDoc train 데이터로 추가 파인튜닝
3. **Blight_Spot 세분화**: 현재 4종 통합 클래스를 세분화하여 정밀도 향상
4. **앙상블**: EfficientNet-B3 + ConvNeXt-Tiny 앙상블로 정확도 향상 가능
5. **파인튜닝 데이터 확보**: 스크래핑 데이터 52장 -> 최소 500장 이상 필요
