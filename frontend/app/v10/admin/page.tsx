'use client'

import { useState } from 'react'
import { Menu, X, LayoutDashboard, Ticket, TrendingUp, Package, Users, ArrowLeft, Upload } from 'lucide-react'
import Link from 'next/link'
import { cn } from '@/lib/utils'

type TabType = 'dashboard' | 'matches' | 'betting' | 'products' | 'members'

/**
 * V10 Admin 페이지 컴포넌트 (모바일 퍼스트)
 *
 * @remarks
 * - SHADCN_POLICY에 따라 하나의 컴포넌트로 모바일/데스크톱 모두 처리
 * - 모바일: 햄버거 메뉴 → Sheet 스타일 사이드 메뉴 + 하단 탭 네비게이션
 * - 데스크톱: 가로 네비게이션 (하단 탭 숨김)
 * - Tailwind CSS의 responsive variant만 사용하여 반응형 처리
 * - 접근성(a11y)과 hydration 에러를 고려한 구현
 */
export default function V10Admin() {
    const [activeTab, setActiveTab] = useState<TabType>('dashboard')
    const [isMenuOpen, setIsMenuOpen] = useState(false)

    const tabs = [
        { id: 'dashboard' as TabType, label: '대시보드', icon: LayoutDashboard },
        { id: 'matches' as TabType, label: '경기 예매', icon: Ticket },
        { id: 'betting' as TabType, label: '베팅', icon: TrendingUp },
        { id: 'products' as TabType, label: '상품', icon: Package },
        { id: 'members' as TabType, label: '멤버', icon: Users },
    ]

    const renderContent = () => {
        switch (activeTab) {
            case 'dashboard':
                return <DashboardView />
            case 'matches':
                return <MatchesView />
            case 'betting':
                return <BettingView />
            case 'products':
                return <ProductsView />
            case 'members':
                return <MembersView />
            default:
                return <DashboardView />
        }
    }

    return (
        <div className="min-h-screen bg-white text-black flex flex-col">
            {/* 헤더 - 모바일: 햄버거 메뉴, 데스크톱: 제목 + 파일 업로드 */}
            <header className="sticky top-0 z-40 bg-white border-b border-gray-200 px-4 sm:px-6 lg:px-8 py-3">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                        <Link
                            href="/"
                            className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                            aria-label="홈으로 돌아가기"
                        >
                            <ArrowLeft className="w-5 h-5" />
                        </Link>
                        {/* 모바일: 작게, 데스크톱: 보통 크기 */}
                        <h1 className="text-lg font-bold sm:text-xl lg:text-2xl">어드민</h1>
                    </div>

                    {/* 오른쪽 액션 버튼들 */}
                    <div className="flex items-center gap-2 sm:gap-3">
                        {/* 파일 업로드 버튼 - 반응형: 모바일은 아이콘만, 데스크톱은 아이콘+텍스트 */}
                        <Link
                            href="/v10/admin/upload/player"
                            className={cn(
                                'cursor-pointer transition-colors rounded-lg',
                                'flex items-center gap-2',
                                // 모바일: 아이콘 버튼만
                                'p-2 sm:px-3 sm:py-2',
                                // 데스크톱: 아이콘 + 텍스트
                                'hover:bg-gray-100',
                                'border border-gray-300 hover:border-gray-400'
                            )}
                            aria-label="파일 업로드"
                        >
                            <Upload className="w-4 h-4 sm:w-5 sm:h-5" />
                            {/* 데스크톱에서만 텍스트 표시 */}
                            <span className="hidden sm:inline text-sm font-medium">
                                파일 업로드
                            </span>
                        </Link>

                        {/* 모바일 햄버거 메뉴 버튼 - lg 미만에서만 표시 */}
                        <button
                            onClick={() => setIsMenuOpen(!isMenuOpen)}
                            className="lg:hidden p-2 hover:bg-gray-100 rounded-lg transition-colors"
                            aria-label={isMenuOpen ? '메뉴 닫기' : '메뉴 열기'}
                            aria-expanded={isMenuOpen}
                        >
                            {isMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
                        </button>
                    </div>
                </div>
            </header>

            {/* 모바일 사이드 메뉴 - Sheet 스타일, lg 미만에서만 표시 */}
            {isMenuOpen && (
                <>
                    {/* 오버레이 - 모바일에서만 표시 */}
                    <div
                        className="fixed inset-0 bg-black bg-opacity-50 z-40 lg:hidden"
                        onClick={() => setIsMenuOpen(false)}
                        aria-hidden="true"
                    />
                    {/* 사이드 메뉴 패널 - 모바일: 오른쪽에서 슬라이드, 데스크톱: 숨김 */}
                    <div
                        className={cn(
                            'fixed top-0 right-0 h-full w-64 bg-white shadow-lg z-50',
                            'transform transition-transform duration-300 ease-in-out',
                            'lg:hidden'
                        )}
                        role="dialog"
                        aria-modal="true"
                        aria-label="메뉴"
                    >
                        <div className="flex h-16 items-center justify-between border-b border-gray-200 px-4">
                            <h2 className="text-xl font-bold">메뉴</h2>
                            <button
                                onClick={() => setIsMenuOpen(false)}
                                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                                aria-label="메뉴 닫기"
                            >
                                <X className="w-5 h-5" />
                            </button>
                        </div>
                        <nav className="p-4">
                            <ul className="space-y-2">
                                {tabs.map((tab) => {
                                    const Icon = tab.icon
                                    return (
                                        <li key={tab.id}>
                                            <button
                                                onClick={() => {
                                                    setActiveTab(tab.id)
                                                    setIsMenuOpen(false)
                                                }}
                                                className={cn(
                                                    'w-full flex items-center gap-3 px-4 py-3 text-left rounded-lg transition-colors',
                                                    activeTab === tab.id
                                                        ? 'bg-gray-100 text-black font-medium'
                                                        : 'text-gray-700 hover:bg-gray-50'
                                                )}
                                            >
                                                <Icon className="w-5 h-5" />
                                                <span>{tab.label}</span>
                                            </button>
                                        </li>
                                    )
                                })}
                            </ul>
                        </nav>
                    </div>
                </>
            )}

            {/* 메인 컨텐츠 - 반응형 패딩 */}
            <main className="flex-1 overflow-y-auto pb-20 lg:pb-4">
                <div className="p-4 sm:p-6 lg:p-8">
                    {renderContent()}
                </div>
            </main>

            {/* 하단 탭 네비게이션 - 모바일 전용, 데스크톱에서 숨김 */}
            <nav className="lg:hidden fixed bottom-0 left-0 right-0 bg-white border-t border-gray-200 z-30">
                <div className="flex justify-around">
                    {tabs.map((tab) => {
                        const Icon = tab.icon
                        return (
                            <button
                                key={tab.id}
                                onClick={() => setActiveTab(tab.id)}
                                className={cn(
                                    'flex-1 flex flex-col items-center justify-center py-2 transition-colors',
                                    activeTab === tab.id
                                        ? 'text-black'
                                        : 'text-gray-500'
                                )}
                                aria-label={tab.label}
                            >
                                <Icon className="w-5 h-5 mb-1" />
                                <span className="text-xs">{tab.label}</span>
                            </button>
                        )
                    })}
                </div>
            </nav>
        </div>
    )
}

/**
 * 대시보드 뷰 컴포넌트
 * 모바일: 2열, 태블릿: 2열, 데스크톱: 4열 그리드
 */
function DashboardView() {
    return (
        <div className="space-y-4 sm:space-y-6">
            {/* 모바일: 작게, 데스크톱: 크게 */}
            <h2 className="text-xl font-bold mb-4 sm:text-2xl lg:text-3xl">대시보드</h2>

            {/* 반응형 그리드 - 모바일: 2열, 데스크톱: 4열 */}
            <div className="grid grid-cols-2 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4 lg:gap-6">
                <div className="bg-gray-50 p-4 sm:p-6 rounded-lg border border-gray-200">
                    <div className="text-sm text-gray-600 mb-2">총 매출</div>
                    <div className="text-xl font-bold sm:text-2xl lg:text-3xl">₩12,450,000</div>
                </div>
                <div className="bg-gray-50 p-4 sm:p-6 rounded-lg border border-gray-200">
                    <div className="text-sm text-gray-600 mb-2">활성 멤버</div>
                    <div className="text-xl font-bold sm:text-2xl lg:text-3xl">1,234</div>
                </div>
                <div className="bg-gray-50 p-4 sm:p-6 rounded-lg border border-gray-200">
                    <div className="text-sm text-gray-600 mb-2">예매 티켓</div>
                    <div className="text-xl font-bold sm:text-2xl lg:text-3xl">5,678</div>
                </div>
                <div className="bg-gray-50 p-4 sm:p-6 rounded-lg border border-gray-200">
                    <div className="text-sm text-gray-600 mb-2">활성 베팅</div>
                    <div className="text-xl font-bold sm:text-2xl lg:text-3xl">89</div>
                </div>
            </div>

            <div className="bg-gray-50 p-4 sm:p-6 rounded-lg border border-gray-200 mt-4 sm:mt-6">
                <h3 className="font-semibold mb-3 sm:mb-4 text-base sm:text-lg">최근 활동</h3>
                <div className="space-y-3 sm:space-y-4">
                    <div className="text-sm pb-3 sm:pb-4 border-b border-gray-200 last:border-0">
                        <div className="font-medium">홍길동님이 경기 티켓을 예매했습니다</div>
                        <div className="text-gray-500 text-xs mt-1">5분 전</div>
                    </div>
                    <div className="text-sm pb-3 sm:pb-4 border-b border-gray-200 last:border-0">
                        <div className="font-medium">김철수님이 베팅을 완료했습니다</div>
                        <div className="text-gray-500 text-xs mt-1">12분 전</div>
                    </div>
                </div>
            </div>
        </div>
    )
}

/**
 * 경기 예매 관리 뷰
 * 모바일: 카드 형식, 데스크톱: 테이블 형식 (선택적)
 */
function MatchesView() {
    return (
        <div className="space-y-4 sm:space-y-6">
            {/* 모바일: 세로, 데스크톱: 가로 */}
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-4 sm:mb-6">
                <h2 className="text-xl font-bold sm:text-2xl lg:text-3xl">경기 예매</h2>
                <button className="w-full sm:w-auto px-4 sm:px-6 py-2 sm:py-3 bg-black text-white rounded-lg text-sm sm:text-base hover:bg-gray-800 transition-colors font-medium">
                    추가
                </button>
            </div>

            {/* 반응형 카드 리스트 */}
            <div className="space-y-3 sm:space-y-4">
                <div className="border border-gray-200 rounded-lg p-4 sm:p-6 hover:shadow-md transition-shadow">
                    <div className="font-semibold text-base sm:text-lg mb-2">맨체스터 유나이티드 vs 리버풀</div>
                    <div className="text-sm text-gray-600 space-y-1">
                        <div>2024-03-15 20:00</div>
                        <div>예매 가능: 5,000매</div>
                    </div>
                </div>
                <div className="border border-gray-200 rounded-lg p-4 sm:p-6 hover:shadow-md transition-shadow">
                    <div className="font-semibold text-base sm:text-lg mb-2">바르셀로나 vs 레알 마드리드</div>
                    <div className="text-sm text-gray-600 space-y-1">
                        <div>2024-03-20 22:00</div>
                        <div>예매 가능: 3,000매</div>
                    </div>
                </div>
            </div>
        </div>
    )
}

/**
 * 베팅 시스템 뷰
 * 모바일: 1열, 데스크톱: 2열 그리드
 */
function BettingView() {
    return (
        <div className="space-y-4 sm:space-y-6">
            <h2 className="text-xl font-bold mb-4 sm:text-2xl lg:text-3xl sm:mb-6">베팅 시스템</h2>

            {/* 모바일: 1열, 데스크톱: 2열 */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 sm:gap-6">
                <div className="border border-gray-200 rounded-lg p-4 sm:p-6">
                    <div className="font-semibold text-base sm:text-lg mb-3 sm:mb-4">맨체스터 유나이티드 vs 리버풀</div>
                    <div className="grid grid-cols-3 gap-2 sm:gap-4 mb-3 sm:mb-4">
                        <div className="text-center p-3 sm:p-4 bg-gray-50 rounded-lg">
                            <div className="text-xs text-gray-600 mb-1 sm:mb-2">홈 승</div>
                            <div className="text-lg sm:text-xl lg:text-2xl font-bold mb-1">35%</div>
                            <div className="text-xs sm:text-sm text-blue-600 font-medium">2.86x</div>
                        </div>
                        <div className="text-center p-3 sm:p-4 bg-gray-50 rounded-lg">
                            <div className="text-xs text-gray-600 mb-1 sm:mb-2">무승부</div>
                            <div className="text-lg sm:text-xl lg:text-2xl font-bold mb-1">25%</div>
                            <div className="text-xs sm:text-sm text-blue-600 font-medium">4.0x</div>
                        </div>
                        <div className="text-center p-3 sm:p-4 bg-gray-50 rounded-lg">
                            <div className="text-xs text-gray-600 mb-1 sm:mb-2">원정 승</div>
                            <div className="text-lg sm:text-xl lg:text-2xl font-bold mb-1">40%</div>
                            <div className="text-xs sm:text-sm text-blue-600 font-medium">2.5x</div>
                        </div>
                    </div>
                    <div className="flex justify-between items-center text-sm">
                        <span className="text-gray-500">신뢰도: 85%</span>
                        <button className="text-blue-600 hover:text-blue-800 text-sm">재계산</button>
                    </div>
                </div>
            </div>
        </div>
    )
}

/**
 * 상품 관리 뷰
 */
function ProductsView() {
    return (
        <div className="space-y-4 sm:space-y-6">
            {/* 모바일: 세로, 데스크톱: 가로 */}
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-4 sm:mb-6">
                <h2 className="text-xl font-bold sm:text-2xl lg:text-3xl">상품 관리</h2>
                <button className="w-full sm:w-auto px-4 sm:px-6 py-2 sm:py-3 bg-black text-white rounded-lg text-sm sm:text-base hover:bg-gray-800 transition-colors font-medium">
                    추가
                </button>
            </div>

            <div className="space-y-3 sm:space-y-4">
                <div className="border border-gray-200 rounded-lg p-4 sm:p-6 hover:shadow-md transition-shadow">
                    <div className="font-semibold text-base sm:text-lg mb-2">프리미엄 시즌권</div>
                    <div className="text-sm sm:text-base text-gray-600 space-y-1">
                        <div className="font-medium">₩500,000</div>
                        <div>재고: 50개</div>
                    </div>
                </div>
                <div className="border border-gray-200 rounded-lg p-4 sm:p-6 hover:shadow-md transition-shadow">
                    <div className="font-semibold text-base sm:text-lg mb-2">VIP 박스석 패키지</div>
                    <div className="text-sm sm:text-base text-gray-600 space-y-1">
                        <div className="font-medium">₩2,000,000</div>
                        <div>재고: 10개</div>
                    </div>
                </div>
            </div>
        </div>
    )
}

/**
 * 멤버 관리 뷰
 */
function MembersView() {
    return (
        <div className="space-y-4 sm:space-y-6">
            {/* 모바일: 세로, 데스크톱: 가로 */}
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-4 sm:mb-6">
                <h2 className="text-xl font-bold sm:text-2xl lg:text-3xl">멤버 관리</h2>
                <button className="w-full sm:w-auto px-4 sm:px-6 py-2 sm:py-3 bg-black text-white rounded-lg text-sm sm:text-base hover:bg-gray-800 transition-colors font-medium">
                    추가
                </button>
            </div>

            <div className="space-y-3 sm:space-y-4">
                <div className="border border-gray-200 rounded-lg p-4 sm:p-6 hover:shadow-md transition-shadow">
                    <div className="font-semibold text-base sm:text-lg mb-2">홍길동</div>
                    <div className="text-sm sm:text-base text-gray-600 space-y-1">
                        <div>hong@example.com</div>
                        <div>VIP · 총 구매액: ₩2,500,000</div>
                    </div>
                </div>
                <div className="border border-gray-200 rounded-lg p-4 sm:p-6 hover:shadow-md transition-shadow">
                    <div className="font-semibold text-base sm:text-lg mb-2">김철수</div>
                    <div className="text-sm sm:text-base text-gray-600 space-y-1">
                        <div>kim@example.com</div>
                        <div>일반 · 총 구매액: ₩800,000</div>
                    </div>
                </div>
            </div>
        </div>
    )
}


