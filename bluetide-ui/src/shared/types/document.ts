// Document types for the IDP platform

export type DocumentType = 'pdf' | 'docx' | 'image' | 'other'
export type DocumentSource = 'onedrive' | 's3' | 'sharepoint' | 'gdrive' | 'local'
export type DocumentStage = 'parsed' | 'ocr_extraction' | 'generating_embeddings' | 'completed' | 'failed'
export type ConfidenceStatus = 'running' | 'chunking' | 'completed'
export type DocumentLanguage = 'english' | 'arabic'
export type DocumentCategory = 'invoice' | 'equipment_document' | 'user_manual' | 'finance' | 'other'

export interface Document {
    id: string
    name: string
    size: number // in bytes
    type: DocumentType
    source: DocumentSource
    currentStage: DocumentStage
    confidenceStatus: ConfidenceStatus
    confidencePercentage?: number // 0-100
    uploadedAt: Date
    lastModifiedAt: Date
    language: DocumentLanguage
    category: DocumentCategory
    fingerprint: string
    uid: string
    s3Url?: string
    fileSizeMb?: string
    // Admin fields
    classificationLevel: number // 0-3
    categoryIds: string[]
    deletedAt: Date | null
    createdByUid: string
}

// Mock data generator
export function generateMockDocuments(count: number): Document[] {
    const types: DocumentType[] = ['pdf', 'docx', 'image', 'other']
    const sources: DocumentSource[] = ['onedrive', 's3']
    const stages: DocumentStage[] = ['parsed', 'ocr_extraction', 'generating_embeddings', 'completed', 'failed']
    const confidenceStatuses: ConfidenceStatus[] = ['running', 'chunking', 'completed']
    const languages: DocumentLanguage[] = ['english', 'arabic']
    const categories: DocumentCategory[] = ['invoice', 'equipment_document', 'user_manual', 'finance', 'other']
    const names = [
        'Invoice_2024_Q1.pdf',
        'Equipment_Manual_v2.docx',
        'Receipt_Scan.png',
        'Financial_Report.pdf',
        'Contract_Agreement.docx',
        'Product_Catalog.pdf',
        'Maintenance_Guide.pdf',
        'Budget_Overview.xlsx',
        'User_Guidelines.docx',
        'Technical_Specs.pdf',
    ]

    return Array.from({ length: count }, (_, i) => ({
        id: `doc-${i + 1}`,
        name: names[i % names.length],
        size: Math.floor(Math.random() * 10000000) + 100000,
        type: types[Math.floor(Math.random() * types.length)],
        source: sources[Math.floor(Math.random() * sources.length)],
        currentStage: stages[Math.floor(Math.random() * stages.length)],
        confidenceStatus: confidenceStatuses[Math.floor(Math.random() * confidenceStatuses.length)],
        confidencePercentage: Math.floor(Math.random() * 40) + 60,
        uploadedAt: new Date(Date.now() - Math.random() * 30 * 24 * 60 * 60 * 1000),
        lastModifiedAt: new Date(Date.now() - Math.random() * 7 * 24 * 60 * 60 * 1000),
        language: languages[Math.floor(Math.random() * languages.length)],
        category: categories[Math.floor(Math.random() * categories.length)],
        fingerprint: `${Math.random().toString(36).substring(2, 8)}...${Math.random().toString(36).substring(2, 8)}`,
        uid: `UID-${Math.random().toString(36).substring(2, 10).toUpperCase()}`,
        classificationLevel: Math.floor(Math.random() * 4),
        categoryIds: [],
        deletedAt: null,
        createdByUid: 'mock-user',
    }))
}
