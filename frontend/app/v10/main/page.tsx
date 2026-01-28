'use client'

import { useState } from 'react'
import { Send, Loader2 } from 'lucide-react'

/**
 * V10 Main 페이지 컴포넌트
 *
 * @remarks
 * - 챗GPT 스타일의 자연어 질의응답 인터페이스
 * - 축구 관련 질문에 대한 AI 답변 제공
 */
export default function V10Main() {
    const [question, setQuestion] = useState('')
    const [answer, setAnswer] = useState('')
    const [isLoading, setIsLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()

        if (!question.trim() || isLoading) return

        setIsLoading(true)
        setError(null)
        setAnswer('')

        try {
            const response = await fetch(`${API_URL}/api/v10/soccer/chat/query`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    question: question.trim(),
                }),
            })

            if (!response.ok) {
                const errorText = await response.text()
                throw new Error(`HTTP ${response.status}: ${errorText}`)
            }

            const data = await response.json()
            // 응답 구조: { success, question, result: { message, domain, classification, ... } }
            const result = data.result || {}
            const answer = result.message ||
                `질문이 ${result.routed_domain || '알 수 없는'} 도메인으로 라우팅되었습니다.` ||
                '질문이 전달되었습니다.'
            setAnswer(answer)
            setQuestion('') // 입력창 초기화
        } catch (err: any) {
            console.error('API 호출 오류:', err)
            setError(err.message || '답변을 가져오는 중 오류가 발생했습니다.')
        } finally {
            setIsLoading(false)
        }
    }

    const handleKeyPress = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        // Shift + Enter는 줄바꿈, Enter만 누르면 전송
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            handleSubmit(e)
        }
    }

    return (
        <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 flex flex-col">
            {/* 헤더 */}
            <header className="bg-gray-800 border-b border-gray-700 shadow-lg">
                <div className="container mx-auto px-4 py-4">
                    <h1 className="text-2xl font-bold text-white">축구 AI 프로그램</h1>
                </div>
            </header>

            {/* 메인 컨텐츠 영역 */}
            <main className="flex-1 container mx-auto px-4 py-2 max-w-4xl flex flex-col">
                {/* 답변 표시 영역 */}
                <div className="flex-1 mb-2">
                    {answer ? (
                        <div className="bg-gray-800 rounded-lg shadow-lg p-6 border border-gray-700">
                            <div className="flex items-start gap-3">
                                <div className="flex-shrink-0 w-8 h-8 bg-blue-600 rounded-full flex items-center justify-center">
                                    <span className="text-white text-sm font-bold">AI</span>
                                </div>
                                <div className="flex-1">
                                    <div className="prose prose-sm max-w-none prose-invert">
                                        <p className="text-gray-100 whitespace-pre-wrap leading-relaxed">
                                            {answer}
                                        </p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    ) : error ? (
                        <div className="bg-red-900/30 border border-red-700 rounded-lg p-6">
                            <p className="text-red-200">{error}</p>
                        </div>
                    ) : (
                        <div className="bg-gray-800 rounded-lg shadow-lg p-12 border border-gray-700 text-center">
                            <p className="text-gray-300 text-lg">
                                축구에 대해 궁금한 것을 물어보세요!
                            </p>
                            <p className="text-gray-400 text-sm mt-1">
                                예: "손흥민의 등번호는?", "토트넘의 최근 경기 결과는?"
                            </p>
                        </div>
                    )}
                </div>

                {/* 입력 영역 */}
                <form onSubmit={handleSubmit} className="bg-gray-800 rounded-lg shadow-lg border border-gray-700 p-3">
                    <div className="flex gap-3">
                        <textarea
                            value={question}
                            onChange={(e) => setQuestion(e.target.value)}
                            onKeyPress={handleKeyPress}
                            placeholder="질문을 입력하세요... (Enter: 전송, Shift+Enter: 줄바꿈)"
                            className="flex-1 min-h-[120px] max-h-[300px] px-4 py-3 bg-gray-900 border border-gray-600 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-y text-gray-100 placeholder-gray-500"
                            disabled={isLoading}
                        />
                        <button
                            type="submit"
                            disabled={!question.trim() || isLoading}
                            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-700 disabled:text-gray-500 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2 font-medium"
                        >
                            {isLoading ? (
                                <>
                                    <Loader2 className="w-5 h-5 animate-spin" />
                                    <span className="hidden sm:inline">처리 중...</span>
                                </>
                            ) : (
                                <>
                                    <Send className="w-5 h-5" />
                                    <span className="hidden sm:inline">전송</span>
                                </>
                            )}
                        </button>
                    </div>
                </form>
            </main>
        </div>
    )
}
