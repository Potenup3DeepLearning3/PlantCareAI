# 모델 비교 실험 결과

**실험 일시**: 2026-03-31 19:53
**최종 선택**: efficientnet_b3

## 비교 테이블

| 항목 | EfficientNet-B3 | ConvNeXt-Tiny |
|------|----------------|---------------|
| Val Accuracy | 0.9986 | 0.9890 |
| 모델 크기 (MB) | 40.86 | 106.15 |
| 추론 속도 (ms) | 19.76 | 6.23 |

## 선택 근거

Validation accuracy 기준으로 **efficientnet_b3**를 최종 모델로 선택하였다.
EfficientNet-B3이 정확도, 모델 크기 모두에서 우위.

## 종 식별 모델

| 항목 | 값 |
|------|----|
| 아키텍처 | EfficientNet-B3 |
| 클래스 수 | 47종 |
| Val Accuracy | 88.15% |
