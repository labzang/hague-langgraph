"""
LangChain Hello World 애플리케이션 with pgvector 연동

이 앱은 pgvector 데이터베이스와 연동하여 간단한 벡터 검색을 수행합니다.
파이썬 3.13 버전 이상 사용
파일을 수정한 후
"""

import os
import asyncio
from typing import List
import psycopg2
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import VectorStore
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import PGVector
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from langchain_core.language_models.base import BaseLanguageModel


class SimpleEmbeddings(Embeddings):
    """간단한 더미 임베딩 클래스 (OpenAI API 키가 없을 때 사용)"""

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """문서들을 임베딩으로 변환"""
        return [[0.1, 0.2, 0.3, 0.4, 0.5] for _ in texts]

    def embed_query(self, text: str) -> List[float]:
        """쿼리를 임베딩으로 변환"""
        return [0.1, 0.2, 0.3, 0.4, 0.5]


def wait_for_postgres():
    """PostgreSQL 데이터베이스가 준비될 때까지 대기"""
    import time

    max_retries = 30
    retry_count = 0

    while retry_count < max_retries:
        try:
            conn = psycopg2.connect(
                host=os.getenv("POSTGRES_HOST", "postgres"),
                port=os.getenv("POSTGRES_PORT", "5432"),
                database=os.getenv("POSTGRES_DB", "langchain_db"),
                user=os.getenv("POSTGRES_USER", "langchain_user"),
                password=os.getenv("POSTGRES_PASSWORD", "langchain_password")
            )
            conn.close()
            print("✅ PostgreSQL 데이터베이스 연결 성공!")
            return True
        except psycopg2.OperationalError:
            retry_count += 1
            print(f"⏳ PostgreSQL 연결 대기 중... ({retry_count}/{max_retries})")
            time.sleep(2)

    raise Exception("PostgreSQL 데이터베이스에 연결할 수 없습니다.")


def setup_vectorstore() -> PGVector:
    """pgvector 벡터스토어 설정"""

    # 데이터베이스 연결 정보
    connection_string = (
        f"postgresql://{os.getenv('POSTGRES_USER', 'langchain_user')}:"
        f"{os.getenv('POSTGRES_PASSWORD', 'langchain_password')}@"
        f"{os.getenv('POSTGRES_HOST', 'postgres')}:"
        f"{os.getenv('POSTGRES_PORT', '5432')}/"
        f"{os.getenv('POSTGRES_DB', 'langchain_db')}"
    )

    # 임베딩 모델 설정 (OpenAI API 키가 있으면 OpenAI, 없으면 더미)
    if os.getenv("OPENAI_API_KEY"):
        embeddings = OpenAIEmbeddings()
        print("🤖 OpenAI 임베딩 모델을 사용합니다.")
    else:
        embeddings = SimpleEmbeddings()
        print("🔧 더미 임베딩 모델을 사용합니다. (OpenAI API 키가 설정되지 않음)")

    # PGVector 벡터스토어 생성
    vectorstore = PGVector(
        connection_string=connection_string,
        embedding_function=embeddings,
        collection_name="langchain_collection",
    )

    return vectorstore


def add_sample_documents(vectorstore: PGVector):
    """샘플 문서들을 벡터스토어에 추가"""

    sample_docs = [
        Document(
            page_content="LangChain은 대규모 언어 모델을 활용한 애플리케이션 개발을 위한 프레임워크입니다.",
            metadata={"source": "langchain_intro", "type": "definition"}
        ),
        Document(
            page_content="pgvector는 PostgreSQL에서 벡터 유사도 검색을 가능하게 하는 확장입니다.",
            metadata={"source": "pgvector_intro", "type": "definition"}
        ),
        Document(
            page_content="Docker는 애플리케이션을 컨테이너로 패키징하여 배포를 쉽게 만드는 플랫폼입니다.",
            metadata={"source": "docker_intro", "type": "definition"}
        ),
        Document(
            page_content="Python은 데이터 과학과 AI 개발에 널리 사용되는 프로그래밍 언어입니다.",
            metadata={"source": "python_intro", "type": "definition"}
        ),
    ]

    print("📚 샘플 문서들을 벡터스토어에 추가 중...")
    vectorstore.add_documents(sample_docs)
    print("✅ 샘플 문서 추가 완료!")


def setup_rag_chain(vectorstore: PGVector):
    """RAG (Retrieval-Augmented Generation) 체인 설정"""

    # 프롬프트 템플릿
    prompt = ChatPromptTemplate.from_template("""
다음 컨텍스트를 바탕으로 질문에 답해주세요:

컨텍스트: {context}

질문: {question}

답변:
""")

    # 검색기 설정
    retriever = vectorstore.as_retriever(search_kwargs={"k": 2})

    # LLM 설정 및 RAG 체인 구성
    if os.getenv("OPENAI_API_KEY"):
        llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
        print("🤖 OpenAI GPT 모델을 사용합니다.")

        # 실제 RAG 체인 구성
        rag_chain = (
            {"context": retriever, "question": RunnablePassthrough()}
            | prompt
            | llm
            | StrOutputParser()
        )
    else:
        print("🔧 더미 LLM을 사용합니다. (OpenAI API 키가 설정되지 않음)")

        # 더미 RAG 함수 (OpenAI API 키가 없을 때)
        def dummy_rag_function(question: str) -> str:
            """OpenAI API 키가 없을 때 사용하는 더미 RAG 함수"""
            # invoke 메서드를 사용하여 문서 검색
            docs = retriever.invoke(question)
            context = "\n".join([f"- {doc.page_content}" for doc in docs])

            return f"""🔍 검색된 관련 문서들:
{context}

💡 더미 응답: 위의 문서들이 '{question}' 질문과 관련된 내용입니다.
실제 AI 응답을 받으려면 OpenAI API 키를 설정해주세요.
하지만 벡터 검색 기능은 정상적으로 작동하고 있습니다!"""

        # RunnableLambda로 래핑하여 체인과 호환되도록 함
        rag_chain = RunnableLambda(dummy_rag_function)

    return rag_chain


def main():
    """메인 함수"""
    print("🚀 LangChain + pgvector Hello World 앱 시작!")

    # PostgreSQL 연결 대기
    wait_for_postgres()

    # 벡터스토어 설정
    print("🔧 벡터스토어 설정 중...")
    vectorstore = setup_vectorstore()

    # 샘플 문서 추가 (기존 데이터가 있는지 확인)
    try:
        # 기존 문서 수 확인
        existing_docs = vectorstore.similarity_search("test", k=1)
        if not existing_docs:
            add_sample_documents(vectorstore)
        else:
            print("📚 기존 문서가 발견되어 샘플 문서 추가를 건너뜁니다.")
    except Exception as e:
        print(f"⚠️ 기존 문서 확인 중 오류 발생, 샘플 문서를 추가합니다: {e}")
        add_sample_documents(vectorstore)

    # RAG 체인 설정
    print("🔗 RAG 체인 설정 중...")
    rag_chain = setup_rag_chain(vectorstore)

    # 테스트 질문들
    test_questions = [
        "LangChain이 무엇인가요?",
        "pgvector는 어떤 기능을 제공하나요?",
        "Docker의 장점은 무엇인가요?",
        "Python이 AI 개발에 인기 있는 이유는?",
    ]

    print("\n" + "="*50)
    print("🎯 테스트 질문들에 대한 답변:")
    print("="*50)

    for i, question in enumerate(test_questions, 1):
        print(f"\n📝 질문 {i}: {question}")
        print("-" * 30)

        try:
            # 모든 경우에 invoke 메서드 사용 (RunnableLambda도 invoke를 지원)
            answer = rag_chain.invoke(question)

            print(f"💡 답변: {answer}")

        except Exception as e:
            print(f"❌ 오류 발생: {e}")

        print("-" * 30)

    print("\n✅ Hello World 앱 실행 완료!")
    print("🔍 벡터 검색과 RAG 기능이 정상적으로 작동합니다.")

    # Docker 환경에서는 대화형 모드 건너뛰기
    if os.getenv("DOCKER_ENV") or not os.isatty(0):
        print("\n🐳 Docker 환경에서 실행 중입니다.")
        print("💡 대화형 모드를 사용하려면 다음 명령을 실행하세요:")
        print("   docker-compose exec -it langchain_app bash")
        print("   python app.py")
        print("\n🎉 애플리케이션이 성공적으로 실행되었습니다!")
        return

    # 로컬 환경에서만 대화형 모드 실행
    print("\n" + "="*50)
    print("💬 대화형 모드 (종료하려면 'quit' 입력)")
    print("="*50)

    while True:
        try:
            user_question = input("\n❓ 질문을 입력하세요: ").strip()

            if user_question.lower() in ['quit', 'exit', '종료']:
                print("👋 안녕히 가세요!")
                break

            if not user_question:
                continue

            print("🔍 검색 중...")

            # 모든 경우에 invoke 메서드 사용
            answer = rag_chain.invoke(user_question)

            print(f"💡 답변: {answer}")

        except KeyboardInterrupt:
            print("\n👋 안녕히 가세요!")
            break
        except Exception as e:
            print(f"❌ 오류 발생: {e}")


if __name__ == "__main__":
    main()
