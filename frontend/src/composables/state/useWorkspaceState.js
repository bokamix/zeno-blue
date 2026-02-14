import { ref, computed, shallowRef } from 'vue'

// Singleton state (shared across all components)
const artifacts = ref([])
const fileToView = ref(null) // { path, name } - for mobile file viewer modal

// Workspace tabs state
const workspaceTabs = ref([
    { type: 'chat', id: 'chat', title: 'Chat', closable: false }
])
const activeTabId = ref('chat')

// Default chat tab
const DEFAULT_TABS = [{ type: 'chat', id: 'chat', title: 'Chat', closable: false }]

// Computed set of open file paths for quick lookup
const openFilePaths = computed(() => {
    return new Set(
        workspaceTabs.value
            .filter(t => t.type === 'file')
            .map(t => t.path)
    )
})

// Reveal file in tree state
const revealFilePath = shallowRef(null) // { path: string, timestamp: number }

const revealFileInTree = (path) => {
    if (!path) return
    revealFilePath.value = { path, timestamp: Date.now() }
}

const clearRevealFile = () => {
    revealFilePath.value = null
}

export function useWorkspaceState() {
    // Save workspace to localStorage for a conversation
    const saveWorkspace = (conversationId) => {
        if (!conversationId) return
        const workspace = {
            tabs: workspaceTabs.value,
            activeTab: activeTabId.value
        }
        localStorage.setItem(`workspace_${conversationId}`, JSON.stringify(workspace))
    }

    // Load workspace from localStorage for a conversation
    const loadWorkspace = (conversationId) => {
        if (!conversationId) {
            workspaceTabs.value = [...DEFAULT_TABS]
            activeTabId.value = 'chat'
            return
        }
        const saved = localStorage.getItem(`workspace_${conversationId}`)
        if (saved) {
            try {
                const workspace = JSON.parse(saved)
                workspaceTabs.value = workspace.tabs || [...DEFAULT_TABS]
                activeTabId.value = workspace.activeTab || 'chat'
            } catch (e) {
                console.error('Failed to load workspace:', e)
                workspaceTabs.value = [...DEFAULT_TABS]
                activeTabId.value = 'chat'
            }
        } else {
            workspaceTabs.value = [...DEFAULT_TABS]
            activeTabId.value = 'chat'
        }
    }

    // Reset workspace to default
    const resetWorkspace = () => {
        workspaceTabs.value = [...DEFAULT_TABS]
        activeTabId.value = 'chat'
    }

    // Open file in tab (or activate if already open)
    const openFileInTab = (path, name, conversationId) => {
        const existing = workspaceTabs.value.find(t => t.id === path)
        if (existing) {
            activeTabId.value = path
            return
        }
        workspaceTabs.value.push({
            type: 'file',
            id: path,
            title: name || path.split('/').pop(),
            path: path,
            closable: true
        })
        activeTabId.value = path
        saveWorkspace(conversationId)
    }

    // Close tab
    const closeTab = (tabId, conversationId) => {
        if (tabId === 'chat') return
        const idx = workspaceTabs.value.findIndex(t => t.id === tabId)
        if (idx === -1) return
        workspaceTabs.value.splice(idx, 1)
        if (activeTabId.value === tabId) {
            activeTabId.value = 'chat'
        }
        saveWorkspace(conversationId)
    }

    // Open file (uses tabs on desktop, modal on mobile)
    const openFile = (item, conversationId, closeSidebar) => {
        if (item && item.path) {
            // On mobile, use modal
            if (window.innerWidth < 768) {
                fileToView.value = { path: item.path, name: item.name }
            } else {
                // On desktop, use tabs
                openFileInTab(item.path, item.name, conversationId)
            }
            if (closeSidebar) closeSidebar()
        }
    }

    // Find file or folder in artifacts tree
    const findFileInArtifacts = (nameOrPath, includeDirs = false) => {
        // Strip /workspace/ or /workspace/artifacts/ prefix if present
        let target = nameOrPath
            .replace(/^\/workspace\/artifacts\/?/, '')
            .replace(/^\/workspace\/?/, '')
            .replace(/\/$/, '') // Remove trailing slash

        // If target is empty after stripping, we're looking for root (artifacts folder itself)
        if (!target) {
            return includeDirs ? { is_dir: true, name: 'artifacts', path: '', children: artifacts.value } : null
        }

        // If target contains slashes, navigate the path
        if (target.includes('/')) {
            const parts = target.split('/')
            let current = artifacts.value
            for (let i = 0; i < parts.length; i++) {
                const part = parts[i]
                const isLast = i === parts.length - 1
                const found = current.find(item => item.name === part)
                if (!found) return null
                if (isLast) {
                    // Last part - return if it matches type criteria
                    if (found.is_dir && !includeDirs) return null
                    return found
                } else {
                    // Not last - must be a directory to continue
                    if (!found.is_dir || !found.children) return null
                    current = found.children
                }
            }
            return null
        }

        // Simple name search (no slashes) - search entire tree
        const findItem = (items, searchTarget) => {
            for (const item of items) {
                // For files - match by name (filename only) anywhere in tree
                if (!item.is_dir && item.name === searchTarget) {
                    return item
                }
                // For directories (when includeDirs is true)
                if (item.is_dir) {
                    if (includeDirs && item.name === searchTarget) {
                        return item
                    }
                    if (item.children) {
                        const found = findItem(item.children, searchTarget)
                        if (found) return found
                    }
                }
            }
            return null
        }
        return findItem(artifacts.value, target)
    }

    // Flatten file tree to flat list (for @-mentions search)
    // Memoized version - only recalculates when artifacts change
    let cachedArtifacts = null
    let cachedFlatList = []

    const flattenFilesInternal = (items, prefix = '') => {
        let result = []
        for (const item of items) {
            const path = prefix ? `${prefix}/${item.name}` : item.name
            result.push({ ...item, path })
            if (item.is_dir && item.children) {
                result = result.concat(flattenFilesInternal(item.children, path))
            }
        }
        return result
    }

    const flattenFiles = (items = artifacts.value) => {
        // Return cached result if artifacts haven't changed
        if (items === cachedArtifacts) {
            return cachedFlatList
        }
        // Recalculate and cache
        cachedArtifacts = items
        cachedFlatList = flattenFilesInternal(items)
        return cachedFlatList
    }

    // Get file tabs only
    const getFileTabs = () => workspaceTabs.value.filter(t => t.type === 'file')

    return {
        // State
        artifacts,
        fileToView,
        workspaceTabs,
        activeTabId,
        openFilePaths,
        revealFilePath,

        // Actions
        saveWorkspace,
        loadWorkspace,
        resetWorkspace,
        openFileInTab,
        closeTab,
        openFile,
        findFileInArtifacts,
        flattenFiles,
        getFileTabs,
        revealFileInTree,
        clearRevealFile
    }
}
