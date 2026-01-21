# 실행 방법 가이드

## 문제 해결

`ModuleNotFoundError: No module named 'app'` 오류가 발생하는 경우, 다음 방법 중 하나를 사용하세요.

## 방법 1: 프로젝트 루트에서 실행 (권장)

```powershell
# 프로젝트 루트로 이동
cd C:\Users\hi\Documents\hague\RAG

# 모듈로 실행
python -m app.main

# 또는 직접 실행
python app/main.py
```

## 방법 2: app 폴더에서 직접 실행

```powershell
# app 폴더에서
cd C:\Users\hi\Documents\hague\RAG\app

# 직접 실행 (경로 자동 추가됨)
python main.py
```

## 방법 3: uvicorn으로 실행

```powershell
# 프로젝트 루트에서
cd C:\Users\hi\Documents\hague\RAG

# uvicorn으로 실행
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

## 주의사항

- ❌ `python -m main.py` (잘못된 명령)
- ✅ `python -m app.main` (올바른 명령)
- ✅ `python main.py` (app 폴더에서 직접 실행)
- ✅ `python app/main.py` (프로젝트 루트에서 실행)

## 실행 후 확인

서버가 시작되면 다음 URL로 접속할 수 있습니다:
- API 문서: http://127.0.0.1:8000/docs
- 헬스체크: http://127.0.0.1:8000/health
- 루트: http://127.0.0.1:8000/

