/**
 * usePermissions – hook for component-level source permission checks.
 *
 * Fetches the current user's permissions from GET /users/me/permissions
 * and exposes helpers like canAccessSource(), canDownloadSource(), etc.
 *
 * Permissions are cached via React Query and refetched every 60 seconds.
 */

import { useQuery } from '@tanstack/react-query'
import api from '@/shared/lib/api'
import { useAuth } from '@/shared/context/auth-context'

// Types matching backend response
export interface SourceActions {
    can_view: boolean
    can_download: boolean
    can_filter: boolean
    can_sync: boolean
    can_preview: boolean
}

export interface UserPermissions {
    uid: string
    role: string
    is_admin: boolean
    clearance_level: number
    allowed_category_ids: string[]
    allowed_sources: string[]
    source_permissions: Record<string, SourceActions>
}

const SOURCES = ['s3', 'sharepoint', 'gdrive', 'direct_upload'] as const
export type SourceType = (typeof SOURCES)[number]

async function fetchMyPermissions(): Promise<UserPermissions> {
    const { data } = await api.get<UserPermissions>('users/me/permissions')
    return data
}

export function usePermissions() {
    const { user, role } = useAuth()

    const {
        data: permissions,
        isLoading,
        error,
    } = useQuery<UserPermissions>({
        queryKey: ['user-permissions', user?.uid],
        queryFn: fetchMyPermissions,
        enabled: !!user,
        staleTime: 60_000,
        refetchInterval: 60_000,
    })

    const isAdmin = permissions?.is_admin ?? role === 'org_admin'

    /** Can user see this source at all? */
    const canAccessSource = (source: string): boolean => {
        if (isAdmin) return true
        return permissions?.allowed_sources?.includes(source) ?? false
    }

    const canViewSource = (source: string): boolean => {
        if (isAdmin) return true
        return permissions?.source_permissions?.[source]?.can_view ?? false
    }

    const canDownloadSource = (source: string): boolean => {
        if (isAdmin) return true
        return permissions?.source_permissions?.[source]?.can_download ?? false
    }

    const canSyncSource = (source: string): boolean => {
        if (isAdmin) return true
        return permissions?.source_permissions?.[source]?.can_sync ?? false
    }

    const canPreviewSource = (source: string): boolean => {
        if (isAdmin) return true
        return permissions?.source_permissions?.[source]?.can_preview ?? false
    }

    const canFilterSource = (source: string): boolean => {
        if (isAdmin) return true
        return permissions?.source_permissions?.[source]?.can_filter ?? false
    }

    return {
        permissions,
        isLoading,
        error,
        isAdmin,
        allowedSources: permissions?.allowed_sources ?? (isAdmin ? [...SOURCES] : []),
        canAccessSource,
        canViewSource,
        canDownloadSource,
        canSyncSource,
        canPreviewSource,
        canFilterSource,
    }
}
