# EXAONE-2.4B 스팸메일 판단 에이전트 SFT 학습 과정

## 개요
ETL(Extract, Transform, Load) 방식으로 한국우편사업진흥원 스팸메일 데이터셋을 사용하여 EXAONE-2.4B 모델을 스팸메일 판단 에이전트로 파인튜닝하는 전체 프로세스입니다.

---

## 1. Extract (데이터 추출)

### 1.1 소스 데이터 확인
- **입력 파일**: `app/data/한국우편사업진흥원_스팸메일 수신차단 목록_20241231.sft.jsonl`
- **데이터 형식**: JSONL (JSON Lines)
- **샘플 수**: 약 24,572개 (중복 제거 후)
- **데이터 구조**:
  ```json
  {
    "instruction": "다음 이메일 메타데이터를 분석하여 스팸 여부를 판정하고 JSON 형식으로만 답하세요.",
    "input": {
      "subject": "이메일 제목",
      "attachments": ["첨부파일 목록"],
      "received_at": "수신 일시"
    },
    "output": {
      "action": "BLOCK" | "ALLOW",
      "reason": "판정 근거",
      "confidence": 0.0-1.0
    }
  }
  ```

### 1.2 데이터 로드 전략
- JSONL 파일을 한 줄씩 읽어서 파싱
- 데이터 검증 (필수 필드 존재 여부 확인)
- 데이터셋 객체로 변환 (HuggingFace `datasets` 라이브러리 사용)

---

## 2. Transform (데이터 변환 및 전처리)

### 2.1 데이터 포맷 변환
**목적**: SFT 학습에 적합한 텍스트 형식으로 변환

**변환 규칙**:
- `instruction`, `input`, `output` 필드를 하나의 프롬프트 텍스트로 결합
- EXAONE 모델의 프롬프트 템플릿 형식에 맞게 변환
- 예시 변환 형식:
  ```
  ### Instruction:
  {instruction}

  ### Input:
  {input 내용을 JSON 문자열로 변환}

  ### Response:
  {output 내용을 JSON 문자열로 변환}
  ```

### 2.2 데이터 품질 검증
- **필수 필드 검증**: instruction, input, output 존재 확인
- **데이터 타입 검증**: 각 필드의 타입이 올바른지 확인
- **빈 값 처리**: 필수 필드가 비어있는 샘플 제거 또는 기본값 처리
- **JSON 유효성 검증**: output 필드가 유효한 JSON인지 확인

### 2.3 토크나이징 준비
- EXAONE-2.4B 모델의 토크나이저 로드
- 텍스트를 토큰으로 변환하여 길이 확인
- 최대 시퀀스 길이 설정 (예: 2048 토큰)
- 긴 시퀀스는 자르거나 제외

### 2.4 데이터 분할 (선택사항)
- **Train/Validation 분할**:
  - Train: 80-90% (약 19,658-22,115개)
  - Validation: 10-20% (약 2,457-4,914개)
- **Stratified Split**: BLOCK/ALLOW 비율 유지
- Validation 세트는 학습 중 성능 평가용

---

## 3. Load (모델 학습)

### 3.1 모델 및 토크나이저 로드
- **모델 경로**: `app/model/exaone-2.4b`
- **모델 로드**: `AutoModelForCausalLM.from_pretrained()` 사용
- **토크나이저 로드**: `AutoTokenizer.from_pretrained()` 사용
- **메모리 최적화**:
  - 4-bit 양자화 (BitsAndBytesConfig) - 메모리 절약
  - `device_map="auto"` - GPU/CPU 자동 할당

### 3.2 PEFT/LoRA 설정
**목적**: 전체 모델 파인튜닝 대신 파라미터 효율적 파인튜닝

**설정 항목**:
- **LoRA Rank (r)**: 32-64 (기본값: 64)
- **LoRA Alpha**: 16 (rank의 0.25배)
- **LoRA Dropout**: 0.1
- **Target Modules**: EXAONE 모델의 attention 레이어 (예: `q_proj`, `v_proj`, `k_proj`, `o_proj`)
- **Task Type**: CAUSAL_LM

### 3.3 학습 하이퍼파라미터 설정
- **학습 방법**: Supervised Fine-Tuning (SFT)
- **학습 프레임워크**: TRL의 `SFTTrainer` 사용
- **에포크 수**: 3-5 (데이터 양에 따라 조정)
- **배치 크기**:
  - `per_device_train_batch_size`: 4-8 (GPU 메모리에 따라)
  - `gradient_accumulation_steps`: 4-8 (효과적 배치 크기 = 16-64)
- **학습률**: 2e-4 ~ 5e-4 (LoRA 학습률은 일반적으로 높게)
- **워밍업 스텝**: 100-200 (전체 스텝의 10% 정도)
- **최대 시퀀스 길이**: 2048 토큰
- **옵티마이저**: `paged_adamw_32bit` (메모리 효율적)
- **학습률 스케줄러**: `cosine` (점진적 감소)
- **Mixed Precision**: FP16 활성화 (메모리 절약 및 속도 향상)

### 3.4 학습 실행
1. **모델 준비**:
   - `prepare_model_for_kbit_training()`: 4-bit 학습 준비
   - PEFT 모델로 래핑

2. **Trainer 초기화**:
   - `SFTTrainer` 생성
   - 모델, 토크나이저, 데이터셋, 학습 인자 전달
   - Data Collator 설정 (Language Modeling용)

3. **학습 실행**:
   - `trainer.train()` 호출
   - 학습 중 로깅 (loss, learning rate 등)
   - 정기적 체크포인트 저장 (예: 500 스텝마다)

4. **체크포인트 관리**:
   - `save_steps`: 500 (체크포인트 저장 간격)
   - `save_total_limit`: 3 (최대 체크포인트 수)
   - 최종 모델 저장

### 3.5 어댑터 저장
- **LoRA 어댑터만 저장**: 전체 모델 대신 어댑터만 저장 (용량 절약)
- **저장 경로**: `app/model/exaone-2.4b-spam-detector-adapter/` (예시)
- **저장 내용**:
  - `adapter_config.json`: LoRA 설정
  - `adapter_model.safetensors`: 학습된 가중치
  - `tokenizer` 파일들 (필요시)

---

## 4. 검증 및 평가 (선택사항)

### 4.1 검증 세트 평가
- Validation 세트로 성능 평가
- 메트릭: Loss, Accuracy (BLOCK/ALLOW 예측 정확도)

### 4.2 테스트 세트 평가 (선택사항)
- 별도 테스트 세트로 최종 성능 평가
- Confusion Matrix 분석
- Precision, Recall, F1-Score 계산

---

## 5. 배포 준비

### 5.1 모델 로드 및 테스트
- 학습된 어댑터를 기본 모델에 로드
- 샘플 입력으로 추론 테스트
- 출력 형식 검증 (JSON 형식 준수 여부)

### 5.2 프로덕션 통합
- `app/core/llm/providers/exaone_local.py`에 어댑터 경로 설정
- 또는 `chat_service.py`의 QLoRAChatService에 어댑터 경로 전달
- API 엔드포인트를 통한 테스트

---

## 6. 주의사항 및 최적화 팁

### 6.1 메모리 관리
- **4-bit 양자화**: GPU 메모리 부족 시 필수
- **Gradient Checkpointing**: 메모리 절약 (속도는 느려짐)
- **배치 크기 조정**: 메모리에 맞게 동적 조정

### 6.2 학습 안정성
- **Gradient Clipping**: 그래디언트 폭발 방지 (max_grad_norm: 1.0)
- **Learning Rate 조정**: 너무 높으면 불안정, 너무 낮으면 학습 느림
- **Warmup Steps**: 초기 학습 안정화

### 6.3 데이터 품질
- **데이터 균형**: BLOCK/ALLOW 비율 확인
- **데이터 다양성**: 다양한 스팸 패턴 포함 확인
- **데이터 정확성**: 라벨 품질 검토

### 6.4 성능 최적화
- **Mixed Precision Training**: FP16 사용
- **DataLoader 최적화**: `num_workers` 설정
- **컴파일 최적화**: PyTorch 2.0+ `torch.compile()` 사용 (선택사항)

---

## 7. 예상 소요 리소스

### 7.1 하드웨어 요구사항
- **GPU 메모리**: 최소 8GB (4-bit 양자화 시)
- **시스템 메모리**: 최소 16GB
- **디스크 공간**:
  - 모델: 약 5GB
  - 체크포인트: 약 1-2GB (어댑터만)
  - 데이터: 약 100MB

### 7.2 학습 시간 (예상)
- **에포크당 시간**: GPU에 따라 다름 (예: RTX 3090 기준 30분-1시간)
- **전체 학습 시간**: 3 에포크 기준 1.5-3시간

---

## 8. 파일 구조 (학습 후)

```
app/
├── model/
│   ├── exaone-2.4b/              # 원본 모델 (변경 없음)
│   └── exaone-2.4b-spam-adapter/ # 학습된 LoRA 어댑터
│       ├── adapter_config.json
│       └── adapter_model.safetensors
├── data/
│   └── 한국우편사업진흥원_스팸메일 수신차단 목록_20241231.sft.jsonl
└── checkpoints/                   # 학습 중 체크포인트 (선택사항)
    ├── checkpoint-500/
    ├── checkpoint-1000/
    └── ...
```

---

## 9. 다음 단계 (선택사항)

1. **하이퍼파라미터 튜닝**: Learning rate, LoRA rank 등 실험
2. **데이터 증강**: 추가 데이터 수집 또는 생성
3. **앙상블**: 여러 어댑터 조합 실험
4. **평가 메트릭 개선**: 더 정교한 평가 기준 도입
5. **프로덕션 모니터링**: 실제 사용 환경에서의 성능 추적

