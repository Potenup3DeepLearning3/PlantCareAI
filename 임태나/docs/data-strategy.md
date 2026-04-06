# 데이터 전략

## Tier 1: 사전학습 + 병변 재분류
- PlantVillage 54,306장 (HuggingFace: BrandonFors/Plant-Diseases-PlantVillage-Dataset)
- 38클래스 → 병변 유형 7클래스로 재라벨링:
  - healthy, powdery_mildew, rust, leaf_curl, blight_spot, leaf_mold, mosaic_virus, scab_rot

## Tier 2: 종 식별
- House Plant Species 47종 ~8,000장 (HuggingFace: kakasher/house-plant-species)

## Tier 3: 건강/시듦 보강
- Kaggle Healthy/Wilted Houseplant 904장 (russellchan/healthy-and-wilted-houseplant-images)

## Tier 4: 반려식물 병변 (Day 4 자동 수집)
- Google Images 스크래핑 (icrawler)
- 검색어 20개 x 100~200장 = ~2,000장
- 수집 후 노이즈 필터링 → 파인튜닝용

## 테스트 전용
- PlantDoc 2,598장 (GitHub: pratikkayal/PlantDoc-Dataset)

## LLM 참조 지식
- NCPMS 병해충 도감 API (공공데이터포털, DATAGO_API_KEY)

## 사용하지 않음
- Roboflow (무료 계정 다운로드 제한)
- AI Hub 원예식물 생육 (승인 대기, 없어도 진행)
