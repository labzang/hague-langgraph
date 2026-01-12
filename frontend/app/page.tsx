'use client'

import ChatBot from '@/components/ChatBot'

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-4">
      <div className="w-full max-w-4xl">
        <div className="mb-8 text-center">
          <h1 className="text-4xl font-bold text-gray-800 mb-2">
            RAG 챗봇
          </h1>
          <p className="text-gray-600">
            LangChain과 pgvector를 사용한 지식 기반 챗봇
          </p>
        </div>
        <ChatBot />
      </div>
    </main>
  )
}

