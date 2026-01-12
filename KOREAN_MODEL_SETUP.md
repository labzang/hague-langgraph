# 한국어 Llama 모델 설정 가이드

## 추천 모델

### 1. Polyglot-Ko 3.8B (가장 추천) ⭐
- **모델명**: `nousresearch/polyglot-ko-3.8b`
- **특징**:
  - 한국어 성능 우수
  - 크기와 성능의 균형
  - Hugging Face에서 바로 사용 가능
- **요구사항**: 16GB RAM, GPU 8GB VRAM (양자화 시 4GB)

### 2. Solar-Ko 1.1B
- **모델명**: `upstage/solar-ko-1.1b-instruct`
- **특징**: 경량 모델, 빠른 응답
- **요구사항**: 8GB RAM, GPU 4GB VRAM

### 3. Polyglot-Ko 5.8B
- **모델명**: `nousresearch/polyglot-ko-5.8b`
- **특징**: 더 큰 모델, 더 나은 성능
- **요구사항**: 32GB RAM, GPU 16GB VRAM

## 빠른 시작

### 1. 의존성 설치

```bash
# Hugging Face 모델 사용 시
pip install transformers torch accelerate sentence-transformers

# 양자화 지원 (GPU 메모리 절약)
pip install bitsandbytes

# Ollama 사용 시 (선택사항)
pip install langchain-ollama
```

### 2. 환경 변수 설정

`.env` 파일을 생성하고 다음 내용을 추가:

```env
# Hugging Face 모델 사용
USE_HUGGINGFACE=true
HF_MODEL_NAME=nousresearch/polyglot-ko-3.8b
USE_QUANTIZATION=true  # GPU 메모리 절약

# 한국어 임베딩 모델
USE_OPENAI_EMBEDDINGS=false
EMBEDDING_MODEL_NAME=BAAI/bge-small-ko-v1.5
```

### 3. 모델 다운로드

첫 실행 시 자동으로 모델이 다운로드됩니다.
또는 수동으로 다운로드:

```python
from transformers import AutoModelForCausalLM, AutoTokenizer

model_name = "nousresearch/polyglot-ko-3.8b"
model = AutoModelForCausalLM.from_pretrained(model_name)
tokenizer = AutoTokenizer.from_pretrained(model_name)
```

### 4. 서버 실행

```bash
# Docker 사용
docker-compose up -d

# 또는 로컬 실행
cd app
python api_server.py
```

## 모델 비교

| 모델 | 크기 | RAM 요구사항 | GPU VRAM | 한국어 성능 |
|------|------|-------------|----------|------------|
| Polyglot-Ko 1.3B | 1.3B | 8GB | 4GB | ⭐⭐⭐ |
| Solar-Ko 1.1B | 1.1B | 8GB | 4GB | ⭐⭐⭐ |
| Polyglot-Ko 3.8B | 3.8B | 16GB | 8GB | ⭐⭐⭐⭐ |
| Polyglot-Ko 5.8B | 5.8B | 32GB | 16GB | ⭐⭐⭐⭐⭐ |

## 파인튜닝 가이드

### 데이터 준비

JSONL 형식의 한국어 대화 데이터:

```json
{"instruction": "질문", "input": "", "output": "답변"}
{"instruction": "다른 질문", "input": "", "output": "다른 답변"}
```

### 파인튜닝 스크립트 예시

```python
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    TrainingArguments,
    Trainer,
    DataCollatorForLanguageModeling
)
from datasets import load_dataset

# 모델 및 토크나이저 로드
model_name = "nousresearch/polyglot-ko-3.8b"
model = AutoModelForCausalLM.from_pretrained(model_name)
tokenizer = AutoTokenizer.from_pretrained(model_name)

# 데이터셋 로드
dataset = load_dataset("json", data_files="your_data.jsonl")

# 학습 설정
training_args = TrainingArguments(
    output_dir="./results",
    num_train_epochs=3,
    per_device_train_batch_size=4,
    gradient_accumulation_steps=4,
    learning_rate=2e-5,
    fp16=True,
    logging_steps=10,
    save_steps=500,
)

# Trainer 설정 및 학습
trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=dataset["train"],
    data_collator=DataCollatorForLanguageModeling(
        tokenizer=tokenizer, mlm=False
    ),
)

trainer.train()
trainer.save_model("./fine-tuned-model")
```

## 문제 해결

### GPU 메모리 부족
- `USE_QUANTIZATION=true` 설정 (4-bit 양자화)
- 더 작은 모델 사용 (1.3B 또는 1.1B)
- 배치 크기 줄이기

### 모델 다운로드 실패
- Hugging Face 토큰 설정:
  ```bash
  huggingface-cli login
  ```

### 느린 응답 속도
- GPU 사용 확인
- 양자화 활성화
- 더 작은 모델 사용

## 추가 리소스

- [Polyglot-Ko GitHub](https://github.com/nlpai-lab/KULLM)
- [Hugging Face 한국어 모델](https://huggingface.co/models?language=ko)
- [LangChain 한국어 가이드](https://python.langchain.com/docs/integrations/llms/)




