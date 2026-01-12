"""RAG 체인 설정 및 관리.

이 모듈은 **LLM을 외부에서 주입**받도록 설계되어 있습니다.

- 기본 동작: `llm` 인자를 전달하지 않으면 기존처럼 OpenAI API 키를
  기준으로 체인을 구성하거나, 키가 없을 때는 더미 체인을 반환합니다.
- 주입 방식: 사용자는 `app.core.llm` 패키지에서 생성한 LLM 인스턴스를
  `create_rag_chain(vectorstore, llm=my_llm)` 형태로 전달해 사용할 수 있습니다.
"""

from typing import Optional

from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.output_parsers import StrOutputParser
from langchain_core.language_models.base import BaseLanguageModel
from langchain_openai import ChatOpenAI
from langchain_community.vectorstores import PGVector

from app.config import settings


def create_rag_chain(
    vectorstore,
    llm: Optional[BaseLanguageModel] = None,
):
    """RAG (Retrieval-Augmented Generation) 체인 생성.

    Args:
        vectorstore: 검색에 사용할 PGVector 인스턴스.
        llm: 선택적 LLM 인스턴스. 주입하지 않으면 기존 설정을 사용합니다.

    Returns:
        LangChain Runnable 객체 (invoke(question: str) 지원).
    """
    # 프롬프트 템플릿
    prompt = ChatPromptTemplate.from_template(
        """
다음 컨텍스트를 바탕으로 질문에 답해주세요:

컨텍스트: {context}

질문: {question}

답변:
"""
    )

    # 검색기 설정
    retriever = vectorstore.as_retriever(search_kwargs={"k": 2})

    # 1) 외부에서 LLM을 직접 주입한 경우
    if llm is not None:
        rag_chain = (
            {"context": retriever, "question": RunnablePassthrough()}
            | prompt
            | llm
            | StrOutputParser()
        )
        return rag_chain

    # 2) 주입된 LLM이 없을 때: 기존 동작을 유지 (OpenAI 또는 더미 체인)
    if settings.openai_api_key:
        default_llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0)
        rag_chain = (
            {"context": retriever, "question": RunnablePassthrough()}
            | prompt
            | default_llm
            | StrOutputParser()
        )
        return rag_chain

    # 3) OpenAI 설정이 없을 때: 벡터 검색 결과만 보여주는 더미 체인
    def dummy_rag_function(question: str) -> str:
        """OpenAI API 키가 없을 때 사용하는 더미 RAG 함수."""
        docs = retriever.invoke(question)
        context = "\n".join([f"- {doc.page_content}" for doc in docs])

        return f"""🔍 검색된 관련 문서들:
{context}

💡 더미 응답: 위의 문서들이 '{question}' 질문과 관련된 내용입니다.
실제 AI 응답을 받으려면 OpenAI API 키를 설정해주세요.
하지만 벡터 검색 기능은 정상적으로 작동하고 있습니다!"""

    return RunnableLambda(dummy_rag_function)

