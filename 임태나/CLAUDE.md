# PlantCare AI

반려식물 건강 진단 + 맞춤 케어 시스템. 7개 AI 모델 파이프라인.

## 기술 스택
- Backend: FastAPI / Frontend: Streamlit (4탭)
- ML: PyTorch + torchvision (RTX 5070 로컬)
- Vision: EfficientNet-B3 / ConvNeXt-Tiny, SAM, EasyOCR
- Audio: Whisper large-v3 (로컬), gTTS
- LLM: Ollama qwen2.5:14b (로컬)
- 환경: Windows, Python 3.12, uv 가상환경

## 프로젝트 문서
- 데이터 전략: @docs/data-strategy.md
- 모델 아키텍처: @docs/model-architecture.md
- 코딩 순서: @docs/coding-order.md
- API 설계: @docs/api-spec.md
- LLM 프롬프트: @docs/llm-prompt.md
- 브랜드 에센스: @docs/brand-essence.md
- 10일 스프린트: @docs/sprint-plan.md

## 핵심 규칙
- Roboflow 사용하지 않음 (무료 제한)
- Claude API 사용하지 않음 → Ollama 로컬
- 이미지 전처리에 CLAHE 필수
- 한국어 우선 (OCR, STT, TTS, UI 모두)
- 모든 설정값은 src/config.py에 집중

## 파일 편집 규칙
- 파일 수정 전에 항상 `find` 또는 `ls`로 실제 파일명을 확인한다. app.py vs app_final.py처럼 유사한 이름이 있을 수 있다.
- 존재하지 않는 파일을 수정하지 않는다. 파일이 없으면 사용자에게 알린다.
- 여러 파일을 수정할 때는 각 파일의 전체 경로를 명시하고 수정 전 확인한다.

## 커뮤니케이션 규칙
- 사용자가 질문하면 코드를 수정하지 않는다. 설명만 제공한다.
- 모호한 요청은 실행 전에 "설명할까요, 아니면 수정할까요?"라고 확인한다.
- 각 단계 완료 후 출력 결과물이 실제로 존재하고 비어 있지 않은지 검증한다. 검증 없이 성공 보고 금지.
- 사용자가 "질문:" 또는 "Q:" 로 시작하면 설명만, "실행:" 또는 "Do:" 로 시작하면 바로 수행한다.

## 한국어 & 페르소나 규칙
- 분즈(Boonz) 캐릭터: 반말, 짧고 직관적, 감동 팔이 없음, 시크하지만 허당
- 식물 기본 이름: "마리". 사용자가 지정하지 않으면 임의로 변경하지 않는다.
- 한국어 UI 텍스트 작성 시 어색한 표현(예: "해볼게즈")은 사용하지 않는다.
- 페르소나 톤이나 이름을 바꿀 때는 반드시 사용자 확인 후 수정한다.

## 외부 리소스 규칙
- HuggingFace 데이터셋 ID는 실제 존재 여부를 확인 후 사용한다.
- API 엔드포인트 URL은 추측하지 않는다. 문서나 사용자 제공 값만 사용한다.
- 데이터 다운로드 후 파일 수, 용량, 형식을 검증한다.

## 파이프라인 검증 규칙
- ML 파이프라인의 각 단계(다운로드 → 전처리 → 학습 → 평가) 완료 시 결과물을 검증한다.
- 모델 학습 후 모든 모델을 모든 테스트셋으로 평가한다. 평가 단계를 건너뛰지 않는다.
- 파일 생성(PDF, 번역, 리포트) 후 파일이 비어 있지 않은지 확인한다.
