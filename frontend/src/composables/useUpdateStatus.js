import { ref, onMounted, onUnmounted } from 'vue'

const API_BASE = ''
const POLL_INTERVAL = 10000 // 10 seconds

// Shared state across components
const updatePending = ref(false)
const activeJobs = ref(0)
const updateVersion = ref(null)
const canUpdate = ref(false)
const currentVersion = ref('dev')

let pollInterval = null
let isPolling = false
let wasUpdatePending = false  // Track previous state for auto-refresh

async function fetchStatus() {
    try {
        const res = await fetch(`${API_BASE}/status`)
        if (!res.ok) return

        const data = await res.json()

        // Check if update just completed (was pending, now not)
        if (wasUpdatePending && !data.update_pending) {
            // Update completed - refresh the page to load new version
            console.log('[UpdateStatus] Update completed, refreshing page...')
            window.location.reload()
            return
        }

        wasUpdatePending = data.update_pending
        updatePending.value = data.update_pending
        activeJobs.value = data.active_jobs
        updateVersion.value = data.update_version
        canUpdate.value = data.can_update
        currentVersion.value = data.version
    } catch (e) {
        // Silently fail - status endpoint might not be available
    }
}

function startPolling() {
    if (isPolling) return
    isPolling = true

    // Initial fetch
    fetchStatus()

    // Poll periodically
    pollInterval = setInterval(fetchStatus, POLL_INTERVAL)
}

function stopPolling() {
    if (pollInterval) {
        clearInterval(pollInterval)
        pollInterval = null
    }
    isPolling = false
}

export function useUpdateStatus() {
    onMounted(() => {
        startPolling()
    })

    onUnmounted(() => {
        // Don't stop polling on unmount - other components might need it
        // stopPolling()
    })

    return {
        updatePending,
        activeJobs,
        updateVersion,
        canUpdate,
        currentVersion,
        refresh: fetchStatus
    }
}
