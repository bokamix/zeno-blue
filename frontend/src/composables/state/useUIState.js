import { ref } from 'vue'

// Singleton state (shared across all components)

// Sidebar state
const isSidebarOpen = ref(false)
const isSidebarCollapsed = ref(false)

// Sidebar width (resizable on desktop)
const DEFAULT_SIDEBAR_WIDTH = 288 // w-72
const MIN_SIDEBAR_WIDTH = 200
const MAX_SIDEBAR_WIDTH = 480
const sidebarWidth = ref(DEFAULT_SIDEBAR_WIDTH)

// Mobile navigation
const showMobileNav = ref(false)

// Modal states
const showSettingsModal = ref(false)
const showAppsModal = ref(false)
const showIntegrationsModal = ref(false)
const showScheduledJobsModal = ref(false)
const showCustomSkillsModal = ref(false)

// Confirmation dialogs
const showRestartConfirm = ref(false)
const showCancelConfirm = ref(false)

// Input states
const inputFocused = ref(false)
const isDraggingOnInput = ref(false)
const promptPending = ref(false) // For pulse animation on demo prompts

// Scroll state
const isAtBottom = ref(true)

export function useUIState() {
    // Sidebar actions
    const toggleSidebar = () => {
        isSidebarOpen.value = !isSidebarOpen.value
    }

    const closeSidebar = () => {
        isSidebarOpen.value = false
    }

    const toggleSidebarCollapsed = () => {
        isSidebarCollapsed.value = !isSidebarCollapsed.value
        localStorage.setItem('sidebar-collapsed', isSidebarCollapsed.value ? 'true' : 'false')
    }

    // Load sidebar collapsed state from localStorage
    const loadSidebarCollapsed = () => {
        const saved = localStorage.getItem('sidebar-collapsed')
        if (saved === 'true') {
            isSidebarCollapsed.value = true
        }
    }

    // Sidebar width management
    const setSidebarWidth = (width) => {
        const clampedWidth = Math.max(MIN_SIDEBAR_WIDTH, Math.min(MAX_SIDEBAR_WIDTH, width))
        sidebarWidth.value = clampedWidth
        localStorage.setItem('sidebar-width', String(clampedWidth))
    }

    const loadSidebarWidth = () => {
        const saved = localStorage.getItem('sidebar-width')
        if (saved) {
            const width = parseInt(saved, 10)
            if (!isNaN(width)) {
                sidebarWidth.value = Math.max(MIN_SIDEBAR_WIDTH, Math.min(MAX_SIDEBAR_WIDTH, width))
            }
        }
    }

    // Modal actions
    const openSettingsModal = () => {
        showSettingsModal.value = true
    }

    const openAppsModal = () => {
        showAppsModal.value = true
    }

    const openIntegrationsModal = () => {
        showIntegrationsModal.value = true
    }

    const openScheduledJobsModal = () => {
        showScheduledJobsModal.value = true
    }

    const openCustomSkillsModal = () => {
        showCustomSkillsModal.value = true
    }

    // Close all modals
    const closeAllModals = () => {
        showSettingsModal.value = false
        showAppsModal.value = false
        showIntegrationsModal.value = false
        showScheduledJobsModal.value = false
        showCustomSkillsModal.value = false
        showRestartConfirm.value = false
        showCancelConfirm.value = false
        showMobileNav.value = false
    }

    // Handle escape key for modals
    const handleEscapeKey = (fileToView) => {
        if (showRestartConfirm.value) {
            showRestartConfirm.value = false
            return true
        }
        if (showMobileNav.value) {
            showMobileNav.value = false
            return true
        }
        if (showCustomSkillsModal.value) {
            showCustomSkillsModal.value = false
            return true
        }
        if (showScheduledJobsModal.value) {
            showScheduledJobsModal.value = false
            return true
        }
        if (showIntegrationsModal.value) {
            showIntegrationsModal.value = false
            return true
        }
        if (showAppsModal.value) {
            showAppsModal.value = false
            return true
        }
        if (showSettingsModal.value) {
            showSettingsModal.value = false
            return true
        }
        if (fileToView?.value) {
            fileToView.value = null
            return true
        }
        return false
    }

    return {
        // State
        isSidebarOpen,
        isSidebarCollapsed,
        sidebarWidth,
        showMobileNav,
        showSettingsModal,
        showAppsModal,
        showIntegrationsModal,
        showScheduledJobsModal,
        showCustomSkillsModal,
        showRestartConfirm,
        showCancelConfirm,
        inputFocused,
        isDraggingOnInput,
        promptPending,
        isAtBottom,

        // Actions
        toggleSidebar,
        closeSidebar,
        toggleSidebarCollapsed,
        loadSidebarCollapsed,
        setSidebarWidth,
        loadSidebarWidth,
        openSettingsModal,
        openAppsModal,
        openIntegrationsModal,
        openScheduledJobsModal,
        openCustomSkillsModal,
        closeAllModals,
        handleEscapeKey
    }
}
