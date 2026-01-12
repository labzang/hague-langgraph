# RAG 챗봇 프론트엔드

Next.js 기반 RAG 챗봇 UI입니다.

## 개발 환경 설정

```bash
# 의존성 설치
npm install

# 개발 서버 실행
npm run dev
```

브라우저에서 http://localhost:3000 접속

## 빌드

```bash
# 프로덕션 빌드
npm run build

# 프로덕션 서버 실행
npm start
```

## 환경 변수

`.env.local` 파일을 생성하여 다음 변수를 설정하세요:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## 주요 기능

- 실시간 채팅 인터페이스
- 참조 문서 표시
- 반응형 디자인
- Tailwind CSS 스타일링

