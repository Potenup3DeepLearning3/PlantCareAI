# API 설계

## POST /diagnose
- Input: UploadFile (잎 사진)
- Output:
```json
{
  "species": {"name": "Monstera Deliciosa", "confidence": 0.94, "korean": "몬스테라"},
  "disease": {"name": "Powdery Mildew", "confidence": 0.87, "korean": "흰가루병"},
  "lesion": {"ratio": 0.23, "severity": "중기", "overlay_base64": "..."},
  "care_guide": {"text": "...", "audio_url": "/audio/guide_xxx.mp3"}
}
```

## POST /check-medicine
- Input: UploadFile (약제 라벨 사진)
- Output:
```json
{
  "ocr_result": {"raw_text": "...", "ingredients": [{"name": "만코제브", "concentration": "80%"}]},
  "compatibility": {"is_compatible": true, "reason": "흰가루병에 적합"},
  "current_diagnosis": "powdery_mildew"
}
```

## POST /voice-consult
- Input: UploadFile (음성 wav/mp3/m4a, 60초 제한)
- Output:
```json
{
  "transcript": "잎이 노랗게 변하고 있어요",
  "response": {"text": "...", "audio_url": "/audio/resp_xxx.mp3"},
  "suggested_action": "사진을 올려주시면 더 정확한 진단이 가능합니다"
}
```

## 공통 규칙
- 모든 응답에 korean 필드 필수
- 이미지 10MB, 음성 60초 제한
- 에러는 HTTPException + 한국어 detail
- CORS 허용 (Streamlit ↔ FastAPI)
- 진단 결과 세션 캐시 (약제 체크 시 참조)
