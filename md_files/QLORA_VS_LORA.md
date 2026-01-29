# QLoRA vs LoRA 설명

## 핵심 개념

### QLoRA (Quantized LoRA)
- **베이스 모델**: 4-bit 양자화 (BitsAndBytesConfig 사용)
- **어댑터**: LoRA 어댑터 (동일)
- **용도**: 메모리가 제한적인 환경 (예: RTX 3050 6GB VRAM)

### LoRA (Low-Rank Adaptation)
- **베이스 모델**: FP16 또는 FP32 (양자화 없음)
- **어댑터**: LoRA 어댑터 (동일)
- **용도**: 메모리가 충분한 환경 (예: RTX 4090 24GB VRAM)

## 중요한 포인트

**어댑터 자체는 동일한 LoRA 방식입니다!**

차이점은 **베이스 모델의 양자화 여부**입니다:
- 4-bit 양자화된 베이스 모델 + LoRA 어댑터 = **QLoRA**
- 일반 베이스 모델(FP16/FP32) + LoRA 어댑터 = **LoRA**

## RTX 3050 6GB VRAM에서의 선택

### 메모리 요구사항 (EXAONE-2.4B 기준)

| 방식 | 베이스 모델 메모리 | LoRA 어댑터 | 총 메모리 | RTX 3050 6GB 가능? |
|------|-------------------|------------|-----------|-------------------|
| **Full Fine-tuning** | ~5GB (FP16) | - | ~5GB | ⚠️ 매우 제한적 |
| **LoRA (FP16)** | ~5GB | ~50MB | ~5GB+ | ❌ 불가능 |
| **QLoRA (4-bit)** | ~1.5GB | ~50MB | ~2GB | ✅ **가능** |

### 결론

**RTX 3050 6GB에서는 QLoRA를 사용해야 합니다!**

1. **베이스 모델을 4-bit로 양자화** (메모리 절약)
2. **LoRA 어댑터 추가** (학습 효율성)
3. **총 메모리 사용량**: 약 2GB (학습 시 약 3-4GB)

## 코드에서의 구현

### 현재 구현 (`load_model.py`)

```python
# 4-bit 양자화 설정
quantization_config = BitsAndBytesConfig(
    load_in_4bit=True,  # ← 이것이 QLoRA의 핵심!
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_use_double_quant=True,
    bnb_4bit_quant_type="nf4",
)

# 모델 로드 (4-bit 양자화)
model = AutoModelForCausalLM.from_pretrained(
    model_dir,
    quantization_config=quantization_config,  # ← 4-bit 양자화
    ...
)

# 이후 LoRA 어댑터 추가 (chat_service.py 참고)
from peft import prepare_model_for_kbit_training, get_peft_model, LoraConfig

# 4-bit 모델을 학습 준비
model = prepare_model_for_kbit_training(model)  # ← QLoRA 필수!

# LoRA 설정
lora_config = LoraConfig(
    r=64,  # LoRA rank
    lora_alpha=16,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    ...
)

# LoRA 어댑터 추가
peft_model = get_peft_model(model, lora_config)
```

### 어댑터 저장

학습 후 저장되는 어댑터는 **LoRA 어댑터**입니다:
- `adapter_config.json`: LoRA 설정 (r, alpha, target_modules 등)
- `adapter_model.safetensors`: LoRA 가중치

이 어댑터는:
- 4-bit 양자화된 베이스 모델과 함께 사용 → **QLoRA**
- 일반 베이스 모델과 함께 사용 → **LoRA**

## 요약

### 질문: "양자화 시킨 후라서 qlora 어댑터가 아니라 lora 어댑터인건가?"

**답변**:
- 어댑터 자체는 **LoRA 어댑터**입니다 (동일한 방식)
- 하지만 베이스 모델이 **4-bit로 양자화**되어 있으면 **QLoRA**라고 부릅니다
- RTX 3050 6GB에서는 **4-bit 양자화가 필수**이므로 **QLoRA**를 사용해야 합니다

### RTX 3050 6GB 권장 설정

```python
# 1. 4-bit 양자화로 베이스 모델 로드 (QLoRA)
model, tokenizer = load_exaone_model(
    use_4bit=True,  # 필수!
    device_map="auto",
)

# 2. LoRA 어댑터 추가 (학습 시)
from peft import prepare_model_for_kbit_training, get_peft_model, LoraConfig

model = prepare_model_for_kbit_training(model)  # 4-bit 학습 준비
lora_config = LoraConfig(r=32, ...)  # 메모리 절약을 위해 r=32 권장
peft_model = get_peft_model(model, lora_config)
```

### 메모리 최적화 팁 (RTX 3050 6GB)

1. **4-bit 양자화 필수** (이미 구현됨)
2. **LoRA rank를 줄이기**: r=32 또는 r=16 (기본값 r=64보다 메모리 절약)
3. **배치 크기 줄이기**: per_device_train_batch_size=2, gradient_accumulation_steps=8
4. **Gradient checkpointing 활성화**: 메모리 절약 (속도는 느려짐)

