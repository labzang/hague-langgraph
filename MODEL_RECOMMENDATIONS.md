# 한국어 Llama 모델 추천 및 설정 가이드

## 추천 모델 순위

### 1. Polyglot-Ko (NHN Cloud) ⭐ 추천
- **모델명**: `nousresearch/polyglot-ko-1.3b`, `polyglot-ko-3.8b`, `polyglot-ko-5.8b`
- **특징**:
  - Llama 기반, 한국어에 특화
  - 다양한 크기 제공 (1.3B, 3.8B, 5.8B)
  - Hugging Face에서 바로 사용 가능
- **다운로드**: Hugging Face Hub
- **권장**: `polyglot-ko-3.8b` (성능과 속도 균형)

### 2. Solar-Ko (업스테이지)
- **모델명**: `upstage/solar-ko-1.1b-instruct`
- **특징**:
  - 최신 모델, 인스트럭션 튜닝 완료
  - 경량 모델 (1.1B)
  - 한국어 성능 우수
- **다운로드**: Hugging Face Hub

### 3. KULLM (고려대학교)
- **모델명**: `nlpai-lab/kullm-polyglot-5.8b-v2`
- **특징**:
  - 한국어 성능 우수
  - 대규모 모델 (5.8B)
  - 연구용으로 많이 사용
- **다운로드**: Hugging Face Hub

### 4. Llama-2-Korean
- **모델명**: `beomi/llama-2-ko-7b`, `beomi/llama-2-koen-13b`
- **특징**:
  - 커뮤니티 모델
  - 다양한 크기 제공
- **다운로드**: Hugging Face Hub

## 설정 방법

### 방법 1: Ollama 사용 (가장 간단) ⭐ 추천

1. **Ollama 설치**
   ```bash
   # Windows/Mac/Linux
   curl -fsSL https://ollama.ai/install.sh | sh
   ```

2. **한국어 모델 다운로드**
   ```bash
   # Polyglot-Ko (Ollama에서 사용 가능한 경우)
   ollama pull llama2:7b

   # 또는 커스텀 모델 사용
   ```

3. **환경 변수 설정**
   ```env
   USE_OLLAMA=true
   OLLAMA_BASE_URL=http://localhost:11434
   OLLAMA_MODEL=llama2
   ```

### 방법 2: Hugging Face Transformers 사용 (더 유연)

1. **모델 다운로드**
   ```python
   from transformers import AutoModelForCausalLM, AutoTokenizer

   model_name = "nousresearch/polyglot-ko-3.8b"
   model = AutoModelForCausalLM.from_pretrained(model_name)
   tokenizer = AutoTokenizer.from_pretrained(model_name)
   ```

2. **환경 변수 설정**
   ```env
   USE_HUGGINGFACE=true
   HF_MODEL_NAME=nousresearch/polyglot-ko-3.8b
   ```

## 파인튜닝 가이드

### 데이터 준비
- JSONL 형식의 한국어 대화 데이터
- 예시:
  ```json
  {"instruction": "질문", "input": "", "output": "답변"}
  ```

### 파인튜닝 도구
1. **PEFT (Parameter-Efficient Fine-Tuning)**
   - LoRA 사용 권장
   - 메모리 효율적

2. **Transformers + Trainer**
   - Hugging Face의 표준 방법

3. **Axolotl**
   - Llama 모델 파인튜닝에 최적화

## 권장 사양

- **최소**: 16GB RAM, GPU 8GB VRAM
- **권장**: 32GB RAM, GPU 16GB+ VRAM
- **모델 크기별**:
  - 1.3B: 8GB RAM, GPU 4GB VRAM
  - 3.8B: 16GB RAM, GPU 8GB VRAM
  - 5.8B: 32GB RAM, GPU 16GB VRAM




