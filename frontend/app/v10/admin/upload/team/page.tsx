'use client'

import { useState, useCallback } from 'react'
import { ArrowLeft, Upload, X, CheckCircle2, AlertCircle, Loader2, Users, Building2, MapPin, Calendar } from 'lucide-react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { cn } from '@/lib/utils'

type ItemType = 'player' | 'team' | 'stadium' | 'schedule'

interface FileItem {
    id: string
    file: File
    status: 'pending' | 'uploading' | 'success' | 'error'
    progress?: number
    error?: string
    itemType: ItemType
}

interface MenuItem {
    id: ItemType
    label: string
    icon: React.ComponentType<{ className?: string }>
}

const menuItems: MenuItem[] = [
    { id: 'player', label: '선수', icon: Users },
    { id: 'team', label: '팀', icon: Building2 },
    { id: 'stadium', label: '스타디움', icon: MapPin },
    { id: 'schedule', label: '스케줄', icon: Calendar },
]

/**
 * 파일 업로드 페이지 컴포넌트
 * JSONL 파일을 드래그 앤 드롭으로 multipart/form-data로 전송
 */
export default function FileUploadPage() {
    const router = useRouter()
    const currentType: ItemType = 'team'
    const [files, setFiles] = useState<FileItem[]>([])
    const [isDragging, setIsDragging] = useState(false)

    /**
     * 메뉴 아이템 클릭 핸들러
     */
    const handleMenuClick = useCallback((itemType: ItemType) => {
        if (itemType === currentType) return
        router.push(`/v10/admin/upload/${itemType}`)
    }, [router, currentType])

    /**
     * 파일 추가
     */
    const addFiles = useCallback((newFiles: FileList | null) => {
        if (!newFiles) return

        const fileArray = Array.from(newFiles)
            .filter(file => file.name.endsWith('.jsonl'))
            .map(file => ({
                id: `${Date.now()}-${Math.random()}`,
                file,
                status: 'pending' as const,
                itemType: currentType,
            }))

        setFiles(prev => [...prev, ...fileArray])
    }, [currentType])

    /**
     * 파일 제거
     */
    const removeFile = useCallback((id: string) => {
        setFiles(prev => prev.filter(f => f.id !== id))
    }, [])

    /**
     * 파일 업로드
     */
    const uploadFile = useCallback(async (fileItem: FileItem) => {
        // 업로드 중 상태로 변경
        setFiles(prev =>
            prev.map(f =>
                f.id === fileItem.id
                    ? { ...f, status: 'uploading', progress: 0 }
                    : f
            )
        )

        try {
            const formData = new FormData()
            formData.append('file', fileItem.file)
            formData.append('item_type', fileItem.itemType) // 아이템 타입 지정

            const xhr = new XMLHttpRequest()

            // 업로드 진행률 추적
            xhr.upload.addEventListener('progress', (e) => {
                if (e.lengthComputable) {
                    const progress = Math.round((e.loaded / e.total) * 100)
                    setFiles(prev =>
                        prev.map(f =>
                            f.id === fileItem.id
                                ? { ...f, progress }
                                : f
                        )
                    )
                }
            })

            // 업로드 완료 처리
            const uploadPromise = new Promise<void>((resolve, reject) => {
                xhr.addEventListener('load', () => {
                    if (xhr.status >= 200 && xhr.status < 300) {
                        resolve()
                    } else {
                        reject(new Error(xhr.responseText || `HTTP ${xhr.status}`))
                    }
                })

                xhr.addEventListener('error', () => {
                    reject(new Error('네트워크 오류가 발생했습니다.'))
                })

                xhr.addEventListener('abort', () => {
                    reject(new Error('업로드가 취소되었습니다.'))
                })
            })

            xhr.open('POST', '/api/v10/admin/upload')
            xhr.send(formData)

            await uploadPromise

            // 성공 상태로 변경
            setFiles(prev =>
                prev.map(f =>
                    f.id === fileItem.id
                        ? { ...f, status: 'success', progress: 100 }
                        : f
                )
            )
        } catch (error) {
            // 실패 상태로 변경
            setFiles(prev =>
                prev.map(f =>
                    f.id === fileItem.id
                        ? {
                            ...f,
                            status: 'error',
                            error: error instanceof Error ? error.message : '알 수 없는 오류',
                        }
                        : f
                )
            )
        }
    }, [])

    /**
     * 모든 파일 업로드
     */
    const uploadAllFiles = useCallback(async () => {
        const pendingFiles = files.filter(f => f.status === 'pending')
        for (const fileItem of pendingFiles) {
            await uploadFile(fileItem)
        }
    }, [files, uploadFile])

    /**
     * 드래그 이벤트 핸들러
     */
    const handleDragEnter = useCallback((e: React.DragEvent) => {
        e.preventDefault()
        e.stopPropagation()
        setIsDragging(true)
    }, [])

    const handleDragLeave = useCallback((e: React.DragEvent) => {
        e.preventDefault()
        e.stopPropagation()
        setIsDragging(false)
    }, [])

    const handleDragOver = useCallback((e: React.DragEvent) => {
        e.preventDefault()
        e.stopPropagation()
    }, [])

    const handleDrop = useCallback((e: React.DragEvent) => {
        e.preventDefault()
        e.stopPropagation()
        setIsDragging(false)

        const droppedFiles = e.dataTransfer.files
        addFiles(droppedFiles)
    }, [addFiles])

    /**
     * 파일 선택 핸들러
     */
    const handleFileSelect = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
        addFiles(e.target.files)
        // 같은 파일 재선택 가능하도록 초기화
        e.target.value = ''
    }, [addFiles])

    const pendingCount = files.filter(f => f.status === 'pending').length
    const uploadingCount = files.filter(f => f.status === 'uploading').length
    const successCount = files.filter(f => f.status === 'success').length
    const errorCount = files.filter(f => f.status === 'error').length

    const selectedMenuItem = menuItems.find(item => item.id === currentType)

    return (
        <div className="min-h-screen bg-white text-black flex">
            {/* 사이드 메뉴 */}
            <aside className="w-64 border-r border-gray-200 bg-gray-50 flex-shrink-0">
                <div className="p-4 border-b border-gray-200">
                    <Link
                        href="/v10/admin"
                        className="flex items-center gap-2 text-gray-600 hover:text-black transition-colors mb-4"
                    >
                        <ArrowLeft className="w-4 h-4" />
                        <span className="text-sm font-medium">어드민으로</span>
                    </Link>
                    <h2 className="text-lg font-bold">파일 업로드</h2>
                </div>
                <nav className="p-2">
                    <ul className="space-y-1">
                        {menuItems.map((item) => {
                            const Icon = item.icon
                            const isActive = currentType === item.id
                            const itemCount = isActive ? files.length : 0
                            const itemSuccessCount = isActive ? files.filter(f => f.status === 'success').length : 0

                            return (
                                <li key={item.id}>
                                    <button
                                        onClick={() => handleMenuClick(item.id)}
                                        className={cn(
                                            'w-full flex items-center justify-between px-4 py-3 rounded-lg transition-colors text-left',
                                            isActive
                                                ? 'bg-black text-white'
                                                : 'text-gray-700 hover:bg-gray-100'
                                        )}
                                    >
                                        <div className="flex items-center gap-3">
                                            <Icon className="w-5 h-5" />
                                            <span className="font-medium">{item.label}</span>
                                        </div>
                                        {isActive && itemCount > 0 && (
                                            <span
                                                className={cn(
                                                    'text-xs px-2 py-1 rounded-full',
                                                    'bg-white/20 text-white'
                                                )}
                                            >
                                                {itemSuccessCount > 0 ? `${itemSuccessCount}/${itemCount}` : itemCount}
                                            </span>
                                        )}
                                    </button>
                                </li>
                            )
                        })}
                    </ul>
                </nav>
            </aside>

            {/* 메인 컨텐츠 */}
            <main className="flex-1 overflow-y-auto">
                <div className="p-4 sm:p-6 lg:p-8 max-w-4xl">
                    {/* 선택된 타입 헤더 */}
                    {selectedMenuItem && (
                        <div className="mb-6">
                            <div className="flex items-center gap-3 mb-2">
                                {(() => {
                                    const Icon = selectedMenuItem.icon
                                    return <Icon className="w-6 h-6" />
                                })()}
                                <h1 className="text-2xl font-bold">{selectedMenuItem.label} 파일 업로드</h1>
                            </div>
                            <p className="text-gray-600 text-sm">
                                {selectedMenuItem.label} 데이터를 JSONL 형식으로 업로드하세요.
                            </p>
                        </div>
                    )}

                    {/* 드래그 앤 드롭 영역 */}
                    <div
                        onDragEnter={handleDragEnter}
                        onDragLeave={handleDragLeave}
                        onDragOver={handleDragOver}
                        onDrop={handleDrop}
                        className={cn(
                            'border-2 border-dashed rounded-lg p-8 sm:p-12 text-center transition-colors',
                            isDragging
                                ? 'border-blue-500 bg-blue-50'
                                : 'border-gray-300 hover:border-gray-400 bg-gray-50'
                        )}
                    >
                        <Upload className="w-12 h-12 sm:w-16 sm:h-16 mx-auto mb-4 text-gray-400" />
                        <h2 className="text-lg sm:text-xl font-semibold mb-2">
                            JSONL 파일을 드래그 앤 드롭하세요
                        </h2>
                        <p className="text-sm sm:text-base text-gray-600 mb-4">
                            또는 아래 버튼을 클릭하여 파일을 선택하세요
                        </p>
                        <label
                            htmlFor={`file-input-${currentType}`}
                            className="inline-block px-6 py-3 bg-black text-white rounded-lg cursor-pointer hover:bg-gray-800 transition-colors font-medium"
                        >
                            파일 선택
                        </label>
                        <input
                            id={`file-input-${currentType}`}
                            type="file"
                            accept=".jsonl"
                            multiple
                            onChange={handleFileSelect}
                            className="hidden"
                        />
                    </div>

                    {/* 파일 목록 */}
                    {files.length > 0 && (
                        <div className="mt-6 space-y-4">
                            {/* 통계 */}
                            <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                                <div className="flex items-center gap-4 text-sm">
                                    <span className="text-gray-600">
                                        총 <strong>{files.length}</strong>개 파일
                                    </span>
                                    {pendingCount > 0 && (
                                        <span className="text-blue-600">
                                            대기: <strong>{pendingCount}</strong>
                                        </span>
                                    )}
                                    {uploadingCount > 0 && (
                                        <span className="text-yellow-600">
                                            업로드 중: <strong>{uploadingCount}</strong>
                                        </span>
                                    )}
                                    {successCount > 0 && (
                                        <span className="text-green-600">
                                            완료: <strong>{successCount}</strong>
                                        </span>
                                    )}
                                    {errorCount > 0 && (
                                        <span className="text-red-600">
                                            실패: <strong>{errorCount}</strong>
                                        </span>
                                    )}
                                </div>
                                {pendingCount > 0 && (
                                    <button
                                        onClick={uploadAllFiles}
                                        disabled={uploadingCount > 0}
                                        className={cn(
                                            'px-4 py-2 bg-black text-white rounded-lg text-sm font-medium',
                                            'hover:bg-gray-800 transition-colors',
                                            'disabled:opacity-50 disabled:cursor-not-allowed'
                                        )}
                                    >
                                        모두 업로드
                                    </button>
                                )}
                            </div>

                            {/* 파일 아이템 목록 */}
                            <div className="space-y-3">
                                {files.map((fileItem) => (
                                    <div
                                        key={fileItem.id}
                                        className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow"
                                    >
                                        <div className="flex items-start justify-between gap-4">
                                            <div className="flex-1 min-w-0">
                                                <div className="flex items-center gap-2 mb-2">
                                                    <span className="font-medium text-sm sm:text-base truncate">
                                                        {fileItem.file.name}
                                                    </span>
                                                    {fileItem.status === 'success' && (
                                                        <CheckCircle2 className="w-5 h-5 text-green-500 flex-shrink-0" />
                                                    )}
                                                    {fileItem.status === 'error' && (
                                                        <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
                                                    )}
                                                    {fileItem.status === 'uploading' && (
                                                        <Loader2 className="w-5 h-5 text-blue-500 animate-spin flex-shrink-0" />
                                                    )}
                                                </div>
                                                <div className="text-xs text-gray-500">
                                                    {(fileItem.file.size / 1024).toFixed(2)} KB
                                                </div>
                                                {fileItem.status === 'uploading' && fileItem.progress !== undefined && (
                                                    <div className="mt-2">
                                                        <div className="w-full bg-gray-200 rounded-full h-2">
                                                            <div
                                                                className="bg-blue-500 h-2 rounded-full transition-all duration-300"
                                                                style={{ width: `${fileItem.progress}%` }}
                                                            />
                                                        </div>
                                                        <div className="text-xs text-gray-500 mt-1">
                                                            {fileItem.progress}%
                                                        </div>
                                                    </div>
                                                )}
                                                {fileItem.status === 'error' && fileItem.error && (
                                                    <div className="mt-2 text-sm text-red-600">
                                                        {fileItem.error}
                                                    </div>
                                                )}
                                                {fileItem.status === 'pending' && (
                                                    <button
                                                        onClick={() => uploadFile(fileItem)}
                                                        className="mt-2 px-3 py-1 text-sm bg-blue-500 text-white rounded hover:bg-blue-600 transition-colors"
                                                    >
                                                        업로드
                                                    </button>
                                                )}
                                            </div>
                                            <button
                                                onClick={() => removeFile(fileItem.id)}
                                                className="p-1 hover:bg-gray-100 rounded transition-colors flex-shrink-0"
                                                aria-label="파일 제거"
                                            >
                                                <X className="w-5 h-5 text-gray-500" />
                                            </button>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            </main>
        </div>
    )
}

