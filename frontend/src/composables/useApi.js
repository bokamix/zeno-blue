const API_BASE = ''

// Handle 401 - unregister SW and reload to show login form
const handleUnauthorized = async () => {
    // Unregister service worker so login form can be shown
    if ('serviceWorker' in navigator) {
        const registrations = await navigator.serviceWorker.getRegistrations()
        for (const registration of registrations) {
            await registration.unregister()
        }
    }
    // Clear caches
    if ('caches' in window) {
        const cacheNames = await caches.keys()
        await Promise.all(cacheNames.map(name => caches.delete(name)))
    }
    // Reload to get login form from server
    window.location.reload()
}

// Fetch with timeout wrapper (default 10s)
const fetchWithTimeout = async (url, options = {}, timeout = 10000) => {
    // Check offline before attempting fetch
    if (!navigator.onLine) {
        const err = new Error('No internet connection')
        err.name = 'OfflineError'
        throw err
    }

    const controller = new AbortController()
    const timeoutId = setTimeout(() => controller.abort(), timeout)

    const existingSignal = options.signal
    const abortHandler = () => controller.abort()

    try {
        if (existingSignal) {
            existingSignal.addEventListener('abort', abortHandler)
        }
        const res = await fetch(url, { ...options, signal: controller.signal })
        // Handle 401 globally - user needs to log in
        if (res.status === 401) {
            await handleUnauthorized()
        }
        return res
    } catch (e) {
        // Distinguish timeout from user cancel
        if (e.name === 'AbortError' && !existingSignal?.aborted) {
            const err = new Error('Request timeout')
            err.name = 'TimeoutError'
            throw err
        }
        throw e
    } finally {
        clearTimeout(timeoutId)
        if (existingSignal) {
            existingSignal.removeEventListener('abort', abortHandler)
        }
    }
}

export function useApi() {
    const sendMessage = async (message, conversationId = null) => {
        const payload = { message }
        if (conversationId) payload.conversation_id = conversationId

        const res = await fetch(`${API_BASE}/chat`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        })

        if (res.status === 402) {
            throw new Error('INSUFFICIENT_BALANCE')
        }
        if (!res.ok) throw new Error('Failed to send message')
        return res.json()
    }

    const pollJob = async (jobId, lastActivityId = null) => {
        let url = `${API_BASE}/jobs/${jobId}`
        if (lastActivityId) url += `?since_activity_id=${lastActivityId}`

        const res = await fetch(url)
        if (!res.ok) throw new Error('Failed to poll job')
        return res.json()
    }

    const submitAnswer = async (jobId, response) => {
        const res = await fetch(`${API_BASE}/jobs/${jobId}/respond`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ response })
        })

        if (!res.ok) throw new Error('Failed to submit response')
        return res.json()
    }

    const cancelJob = async (jobId) => {
        const res = await fetch(`${API_BASE}/jobs/${jobId}/cancel`, {
            method: 'POST'
        })

        if (!res.ok) throw new Error('Failed to cancel job')
        return res.json()
    }

    const getConversations = async () => {
        const res = await fetchWithTimeout(`${API_BASE}/conversations`)
        if (res.status === 401) {
            await handleUnauthorized()
            throw new Error('Unauthorized')
        }
        if (!res.ok) throw new Error('Failed to get conversations')
        return res.json()
    }

    const getConversationMessages = async (conversationId, signal = null) => {
        const res = await fetchWithTimeout(`${API_BASE}/conversations/${conversationId}/messages`, { signal })
        if (!res.ok) throw new Error('Failed to get conversation messages')
        return res.json()
    }

    const deleteMessagesFrom = async (conversationId, messageId) => {
        const res = await fetchWithTimeout(`${API_BASE}/conversations/${conversationId}/messages/from/${messageId}`, {
            method: 'DELETE'
        })
        if (!res.ok) throw new Error('Failed to delete messages')
        return res.json()
    }

    const getArtifacts = async (path = null) => {
        let url = `${API_BASE}/artifacts`
        if (path) url += `?path=${encodeURIComponent(path)}`

        const res = await fetchWithTimeout(url)
        if (!res.ok) throw new Error('Failed to get artifacts')
        return res.json()
    }

    const searchArtifacts = async (query) => {
        if (!query) return []
        const res = await fetchWithTimeout(`${API_BASE}/artifacts/search?q=${encodeURIComponent(query)}`)
        if (!res.ok) return []
        return res.json()
    }

    const searchSchedulers = async (query) => {
        if (!query) return []
        try {
            const res = await fetchWithTimeout(`${API_BASE}/scheduled-jobs`)
            if (!res.ok) return []
            const jobs = await res.json()
            const lowerQuery = query.toLowerCase()
            // If query is "scheduler" or starts with "scheduler", return all schedulers
            if ('scheduler'.startsWith(lowerQuery) || lowerQuery.startsWith('scheduler')) {
                return jobs
            }
            // Otherwise filter by name matching query (case-insensitive)
            return jobs.filter(job => job.name.toLowerCase().includes(lowerQuery))
        } catch (e) {
            return []
        }
    }

    const uploadArtifact = async (file, targetPath = '', signal = null) => {
        if (file.size > 50 * 1024 * 1024) {
            throw new Error('File too large (max 50MB)')
        }

        const formData = new FormData()
        formData.append('file', file)
        if (targetPath) formData.append('path', targetPath)

        const res = await fetch(`${API_BASE}/artifacts`, {
            method: 'POST',
            body: formData,
            signal
        })

        if (!res.ok) {
            let msg = 'Failed to upload file'
            try {
                const data = await res.json()
                if (data.detail) msg = data.detail
            } catch (e) {}
            throw new Error(msg)
        }
        return res.json()
    }

    const uploadArtifacts = async (files, targetPath = '') => {
        const results = []
        for (const file of files) {
            const result = await uploadArtifact(file, targetPath)
            results.push(result)
        }
        return results
    }

    const deleteArtifact = async (path) => {
        const res = await fetch(`${API_BASE}/artifacts/${encodeURIComponent(path)}`, {
            method: 'DELETE'
        })

        if (!res.ok) throw new Error('Failed to delete artifact')
        return res.json()
    }

    const moveArtifact = async (sourcePath, destPath) => {
        const res = await fetch(`${API_BASE}/artifacts/${encodeURIComponent(sourcePath)}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ new_path: destPath })
        })
        if (res.status === 409) throw new Error('Destination already exists')
        if (res.status === 404) throw new Error('Source not found')
        if (!res.ok) throw new Error('Failed to move file')
        return res.json()
    }

    const getFileContent = async (path) => {
        const res = await fetch(`${API_BASE}/artifacts/content?path=${encodeURIComponent(path)}`)
        if (!res.ok) throw new Error('Failed to get file content')
        return res.text()
    }

    const getZipDownloadUrl = (path) => {
        return `${API_BASE}/artifacts/${encodeURIComponent(path)}/download-zip`
    }

    const createDirectory = async (path) => {
        const res = await fetch(`${API_BASE}/artifacts/directory`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path })
        })
        if (res.status === 409) {
            throw new Error('Directory already exists')
        }
        if (!res.ok) {
            const err = await res.json().catch(() => ({}))
            throw new Error(err.detail || 'Failed to create directory')
        }
        return res.json()
    }

    const createFile = async (path, content = '') => {
        const res = await fetch(`${API_BASE}/artifacts/content`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ path, content })
        })
        if (!res.ok) {
            const err = await res.json().catch(() => ({}))
            throw new Error(err.detail || 'Failed to create file')
        }
        return res.json()
    }

    const renameConversation = async (conversationId, preview) => {
        const res = await fetch(`${API_BASE}/conversations/${conversationId}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ preview })
        })
        if (!res.ok) {
            const err = await res.json().catch(() => ({}))
            throw new Error(err.detail || 'Failed to rename conversation')
        }
        return res.json()
    }

    const forkConversation = async (conversationId, messageId) => {
        const res = await fetch(`${API_BASE}/conversations/${conversationId}/fork`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message_id: messageId })
        })
        if (!res.ok) {
            const err = await res.json().catch(() => ({}))
            throw new Error(err.detail || 'Failed to fork conversation')
        }
        return res.json()
    }

    const deleteConversation = async (conversationId) => {
        const res = await fetch(`${API_BASE}/conversations/${conversationId}`, {
            method: 'DELETE'
        })
        if (!res.ok) {
            const err = await res.json().catch(() => ({}))
            throw new Error(err.detail || 'Failed to delete conversation')
        }
        return res.json()
    }

    const getConversationCost = async (conversationId) => {
        const res = await fetch(`${API_BASE}/conversations/${conversationId}/cost`)
        if (!res.ok) {
            return { total_cost_usd: 0 }
        }
        return res.json()
    }

    const archiveConversation = async (conversationId) => {
        const res = await fetch(`${API_BASE}/conversations/${conversationId}/archive`, {
            method: 'POST'
        })
        if (!res.ok) {
            const err = await res.json().catch(() => ({}))
            throw new Error(err.detail || 'Failed to archive conversation')
        }
        return res.json()
    }

    const restoreConversation = async (conversationId) => {
        const res = await fetch(`${API_BASE}/conversations/${conversationId}/restore`, {
            method: 'POST'
        })
        if (!res.ok) {
            const err = await res.json().catch(() => ({}))
            throw new Error(err.detail || 'Failed to restore conversation')
        }
        return res.json()
    }

    const getArchivedConversations = async () => {
        const res = await fetch(`${API_BASE}/conversations/archived`)
        if (!res.ok) return []
        return res.json()
    }

    const markConversationRead = async (conversationId) => {
        const res = await fetch(`${API_BASE}/conversations/${conversationId}/read`, {
            method: 'POST'
        })
        if (!res.ok) {
            const err = await res.json().catch(() => ({}))
            throw new Error(err.detail || 'Failed to mark conversation as read')
        }
        return res.json()
    }

    const markConversationUnread = async (conversationId, beforeTimestamp) => {
        const res = await fetch(`${API_BASE}/conversations/${conversationId}/unread`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ before_timestamp: beforeTimestamp })
        })
        if (!res.ok) {
            const err = await res.json().catch(() => ({}))
            throw new Error(err.detail || 'Failed to mark conversation as unread')
        }
        return res.json()
    }

    // Custom Skills CRUD
    const getCustomSkills = async () => {
        const res = await fetchWithTimeout(`${API_BASE}/custom-skills`)
        if (!res.ok) throw new Error('Failed to get custom skills')
        return res.json()
    }

    const createCustomSkill = async (data) => {
        const res = await fetchWithTimeout(`${API_BASE}/custom-skills`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        })
        if (res.status === 409) throw new Error('Skill already exists')
        if (!res.ok) {
            const err = await res.json().catch(() => ({}))
            throw new Error(err.detail || 'Failed to create skill')
        }
        return res.json()
    }

    const updateCustomSkill = async (skillId, data) => {
        const res = await fetchWithTimeout(`${API_BASE}/custom-skills/${encodeURIComponent(skillId)}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        })
        if (!res.ok) {
            const err = await res.json().catch(() => ({}))
            throw new Error(err.detail || 'Failed to update skill')
        }
        return res.json()
    }

    const deleteCustomSkill = async (skillId) => {
        const res = await fetchWithTimeout(`${API_BASE}/custom-skills/${encodeURIComponent(skillId)}`, {
            method: 'DELETE'
        })
        if (!res.ok) throw new Error('Failed to delete skill')
        return res.json()
    }

    // Check if server is available (with short timeout for fast offline detection)
    const checkHealth = async (timeout = 2000) => {
        try {
            const res = await fetchWithTimeout(`${API_BASE}/health`, {}, timeout)
            return res.ok
        } catch (e) {
            return false
        }
    }

    // Get disk usage
    const getDiskUsage = async () => {
        try {
            const res = await fetchWithTimeout(`${API_BASE}/disk-usage`)
            if (!res.ok) {
                return null
            }
            return res.json()
        } catch (e) {
            return null
        }
    }

    return {
        sendMessage,
        pollJob,
        submitAnswer,
        cancelJob,
        getConversations,
        getConversationMessages,
        deleteMessagesFrom,
        renameConversation,
        forkConversation,
        deleteConversation,
        getConversationCost,
        archiveConversation,
        restoreConversation,
        getArchivedConversations,
        markConversationRead,
        markConversationUnread,
        getArtifacts,
        searchArtifacts,
        searchSchedulers,
        uploadArtifact,
        uploadArtifacts,
        deleteArtifact,
        moveArtifact,
        getFileContent,
        getZipDownloadUrl,
        createDirectory,
        createFile,
        checkHealth,
        getDiskUsage,
        getCustomSkills,
        createCustomSkill,
        updateCustomSkill,
        deleteCustomSkill
    }
}
