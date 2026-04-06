# 수정 결과

| # | 수정 | 상태 | 비고 |
|---|------|------|------|
| 1 | 탭1 원터치 | ✅ | 진단 결과 후 케어 로그 버튼 7개 삽입 |
| 2 | 12클래스 | ✅ | app.py 이미 적용, diagnose.py korean 필드 이미 포함 |
| 3 | API URL | ✅ | /medicine, /consult/voice, /consult/text 이미 구현됨 |
| 4 | 탭3 안내 | ✅ | 진단 없으면 boonz("worried") 메시지로 교체 |
| 5 | 동적 메시지 | ✅ | 시간대별(아침/낮/저녁/밤) + 공백(3일/7일+) 인사 |
| 6 | 관계 성장 | ✅ | 식물 카드에 케어 로그 수 기반 4단계 표시 |
| 7 | 채팅 이력 | ✅ | chat_history 세션 유지, 말풍선 교차 표시 |
| 8 | 단계별 로딩 | ⏭ 스킵 | |
| 9 | 맥락 참조 | ✅ | diagnosis_context Form 파라미터 추가, 프론트→API 전달 |
| 10 | 음성 개선 | ⏭ 스킵 | |
| 11 | 탭4 레이아웃 | ✅ | 이미 올바른 순서 (태그→프로그레스→타임라인→추세선→패턴) |
| A | Whisper turbo | ✅ | stt.py 이미 turbo |
| B | Qwen3-TTS | ✅ | tts.py 3단계 폴백 이미 구현됨 |
| C | LLM 한국어 | ✅ | system 메시지에 "반말로. 짧게." 추가 |
| D | 체크포인트 | ✅ | diagnose.py 이미 model_state_dict 패턴 사용 |
| E | 한글 경로 | ✅ | inference/*.py cv2.imread 없음, 이미 PIL 사용 |
| SIM | 시연 데이터 | ✅ | scripts/generate_demo_data.py 생성+실행, 33개 항목 추가 |
