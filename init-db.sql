-- PostgreSQL 데이터베이스 초기화 스크립트
-- pgvector 확장 활성화

-- pgvector 확장 생성
CREATE EXTENSION IF NOT EXISTS vector;

-- 기본 테이블 생성 (LangChain이 자동으로 생성하지만 미리 준비)
-- 이 스크립트는 pgvector 확장만 활성화하고 나머지는 LangChain이 처리합니다.

-- 연결 테스트용 간단한 테이블
CREATE TABLE IF NOT EXISTS connection_test (
    id SERIAL PRIMARY KEY,
    message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 테스트 데이터 삽입
INSERT INTO connection_test (message) VALUES
    ('LangChain + pgvector 연동 테스트 성공!'),
    ('PostgreSQL 데이터베이스가 정상적으로 초기화되었습니다.');

-- 권한 설정
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO langchain_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO langchain_user;
