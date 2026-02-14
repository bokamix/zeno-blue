<template>
    <!-- Setup screen (first run) -->
    <SetupScreen v-if="needsSetup && setupChecked" @complete="onSetupComplete" />

    <!-- Main app -->
    <PullToRefresh v-else-if="setupChecked">
    <div
        class="flex h-screen-safe overflow-hidden bg-[var(--bg-base)]"
        :class="{ 'md:flex-row-reverse': sidebarPosition === 'right' }"
    >
        <!-- Sidebar -->
        <Sidebar
            ref="sidebarRef"
            :position="sidebarPosition"
            :artifacts="artifacts"
            :refresh-key="artifactsRefreshKey"
            :conversations="conversations"
            :archived-conversations="archivedConversations"
            :current-conversation-id="conversationId"
            :is-open="isSidebarOpen"
            :is-collapsed="isSidebarCollapsed"
            @refresh="refreshArtifacts"
            @upload="uploadFile"
            @upload-multiple="uploadFiles"
            @select-file="selectFile"
            @open-file="openFile"
            @delete-file="deleteItem"
            @select-conversation="handleSelectConversation"
            @archive-conversation="handleArchiveConversation"
            @restore-conversation="handleRestoreConversation"
            @delete-archived="handleDeleteArchivedConversation"
            @toggle-collapsed="toggleSidebarCollapsed"
            @navigate-home="navigateHome"
            @show-scheduler="showSchedulerDetail"
            @create-folder="handleCreateFolder"
            @create-file="handleCreateFile"
            @rename-file="handleRenameFile"
            @move-to-folder="handleMoveToFolder"
            @close="closeSidebar"
        />

        <!-- Main Content -->
        <div class="flex-1 flex flex-col min-w-0 bg-[var(--bg-base)] relative overflow-hidden">
            <!-- Update Banner (above header) -->
            <UpdateBanner />

            <!-- Header -->
            <HeaderBar
                @toggle-sidebar="toggleSidebar"
                @open-mobile-nav="showMobileNav = true"
                @open-apps="showAppsModal = true"
                @open-integrations="showIntegrationsModal = true"
                @open-scheduler="showScheduledJobsModal = true"
                @open-settings="openSettingsModal"
                @new-chat="newChat"
            />

            <!-- Tab Bar (desktop only) -->
            <TabBar
                :tabs="workspaceTabs"
                :active-tab-id="activeTabId"
                @select="activeTabId = $event; saveWorkspace(conversationId)"
                @close="closeTab"
                @reveal="revealFileInTree"
            />

            <!-- Chat View -->
            <ChatView
                ref="chatViewRef"
                @fork="handleForkConversation"
                @open-file="handleFileClick"
                @refresh-artifacts="refreshArtifacts"
                @refresh-conversations="refreshConversations"
                @force-refresh-conversations="forceRefreshConversations"
                @new-chat="newChat"
            />
        </div>

        <!-- File Viewer Modal -->
        <FileViewer
            v-if="fileToView"
            :file-path="fileToView.path"
            @close="fileToView = null"
        />

        <!-- Scheduled Jobs Modal -->
        <ScheduledJobsModal
            v-if="showScheduledJobsModal"
            @close="showScheduledJobsModal = false"
            @show-details="showSchedulerDetail"
            @select-conversation="handleSchedulerConversationSelect"
            @refresh-conversations="refreshConversations"
            @new-conversation="handleNewConversation"
        />

        <!-- Scheduler Detail Modal -->
        <SchedulerDetailModal
            v-if="showSchedulerDetailModal && selectedSchedulerId"
            :scheduler-id="selectedSchedulerId"
            @close="showSchedulerDetailModal = false"
            @select-conversation="handleSchedulerConversationSelect"
            @deleted="refreshConversations"
        />

        <!-- Integrations Modal -->
        <IntegrationsModal
            v-if="showIntegrationsModal"
            @close="showIntegrationsModal = false"
        />

        <!-- Apps Modal -->
        <AppsModal
            v-if="showAppsModal"
            @close="showAppsModal = false"
        />

        <!-- Settings Modal (also show when dragging from right edge on mobile) -->
        <SettingsModal
            v-if="showSettingsModal || isDraggingSettings"
            :restart-cooldown="restartCooldown"
            :is-restarting="isRestarting"
            :restart-error="restartError"
            @close="showSettingsModal = false"
            @request-restart="requestRestart"
        />

        <!-- Cancel Confirmation Dialog -->
        <CancelConfirmModal
            v-if="showCancelConfirm"
            @cancel="cancelCancel"
            @confirm="confirmCancel"
        />

        <!-- Restart Confirmation Dialog -->
        <RestartConfirmModal
            v-if="showRestartConfirm"
            @cancel="cancelRestart"
            @confirm="confirmRestart"
        />

        <!-- Create Folder/File Modal -->
        <CreateItemModal
            v-if="showCreateModal"
            :mode="createMode"
            :initial-value="renameItem?.name || ''"
            @cancel="showCreateModal = false; renameItem = null"
            @create="handleCreateItem"
            @rename="handleRenameItem"
        />

        <!-- Restarting Overlay -->
        <div v-if="isRestarting" class="fixed inset-0 bg-black/80 backdrop-blur-md z-[100] flex items-center justify-center">
            <div class="text-center">
                <RefreshCw class="w-12 h-12 text-orange-400 animate-spin mx-auto mb-4" />
                <h2 class="text-xl font-semibold text-white mb-2">Restarting Container</h2>
                <p class="text-zinc-400">Please wait, reconnecting...</p>
            </div>
        </div>

        <!-- Mobile Bottom Sheet Menu -->
        <MobileNavSheet
            v-if="showMobileNav"
            @close="showMobileNav = false"
            @open-apps="showAppsModal = true; showMobileNav = false"
            @open-integrations="showIntegrationsModal = true; showMobileNav = false"
            @open-scheduler="showScheduledJobsModal = true; showMobileNav = false"
            @open-settings="openSettingsModal(); showMobileNav = false"
        />

        <!-- Server Unavailable Overlay -->
        <div v-if="serverUnavailable" class="fixed inset-0 bg-black/80 backdrop-blur-md z-[100] flex items-center justify-center">
            <div class="text-center px-6">
                <WifiOff class="w-16 h-16 text-red-400 mx-auto mb-4" />
                <h2 class="text-xl font-semibold text-white mb-2">{{ t('errors.serverUnavailable.title') }}</h2>
                <p class="text-zinc-400 mb-6">{{ t('errors.serverUnavailable.message') }}</p>
                <button
                    @click="retryConnection"
                    :disabled="isCheckingServer"
                    class="px-6 py-2.5 bg-orange-500 hover:bg-orange-600 disabled:bg-orange-500/50 text-white rounded-lg font-medium transition-colors flex items-center gap-2 mx-auto"
                >
                    <RefreshCw v-if="isCheckingServer" class="w-4 h-4 animate-spin" />
                    <span>{{ isCheckingServer ? t('common.loading') : t('errors.serverUnavailable.retry') }}</span>
                </button>
            </div>
        </div>

        <!-- PWA Install Prompt -->
        <InstallPrompt />

        <!-- Toast notifications -->
        <Toast />
    </div>
    </PullToRefresh>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick, defineAsyncComponent, provide } from 'vue'
import { RefreshCw, WifiOff } from 'lucide-vue-next'
import { useApi } from './composables/useApi'
import { useSwipeGesture } from './composables/useSwipeGesture'
import { useI18n } from 'vue-i18n'

// State Composables
import { useChatState, useUIState, useJobState, useSettingsState, useWorkspaceState } from './composables/state'
import { useToast } from './composables/useToast'

// Components
import SetupScreen from './components/SetupScreen.vue'
import Sidebar from './components/Sidebar.vue'
import Toast from './components/Toast.vue'
import FileViewer from './components/FileViewer.vue'
import TabBar from './components/TabBar.vue'
import InstallPrompt from './components/InstallPrompt.vue'
import HeaderBar from './components/HeaderBar.vue'
import ChatView from './components/ChatView.vue'
import UpdateBanner from './components/UpdateBanner.vue'
import PullToRefresh from './components/PullToRefresh.vue'

// Lazy load modals for better initial bundle size
// With retry on failure (handles offline/network errors)
const lazyModal = (loader) => defineAsyncComponent({
    loader,
    onError(error, retry, fail) {
        // Retry once on network error
        if (error.message?.includes('fetch') || error.message?.includes('network')) {
            retry()
        } else {
            fail()
        }
    }
})
const ScheduledJobsModal = lazyModal(() => import('./components/modals/ScheduledJobsModal.vue'))
const SchedulerDetailModal = lazyModal(() => import('./components/modals/SchedulerDetailModal.vue'))
const IntegrationsModal = lazyModal(() => import('./components/modals/IntegrationsModal.vue'))
const AppsModal = lazyModal(() => import('./components/modals/AppsModal.vue'))
const SettingsModal = lazyModal(() => import('./components/modals/SettingsModal.vue'))
const CancelConfirmModal = lazyModal(() => import('./components/modals/CancelConfirmModal.vue'))
const RestartConfirmModal = lazyModal(() => import('./components/modals/RestartConfirmModal.vue'))
const MobileNavSheet = lazyModal(() => import('./components/modals/MobileNavSheet.vue'))
const CreateItemModal = lazyModal(() => import('./components/modals/CreateItemModal.vue'))

const api = useApi()
const { t } = useI18n()
const toast = useToast()

// Initialize composables
const {
    messages,
    inputText,
    isLoading,
    conversationId,
    conversations,
    archivedConversations,
    pendingQuestion,
    pendingOAuth,
    showConversationLoader,
    readAt,
    genMsgId,
    getConversationFromUrl,
    getStoredJobId,
    setStoredJobId,
    clearStoredJobId,
    saveInputForConversation,
    loadInputForConversation,
    clearChatState,
    reloadMessages: reloadMessagesFromState
} = useChatState()

const {
    isSidebarOpen,
    isSidebarCollapsed,
    showMobileNav,
    showSettingsModal,
    showAppsModal,
    showIntegrationsModal,
    showScheduledJobsModal,
    showRestartConfirm,
    showCancelConfirm,
    toggleSidebar,
    closeSidebar,
    toggleSidebarCollapsed,
    loadSidebarCollapsed
} = useUIState()

const {
    currentJobId,
    isCancelling,
    activities,
    lastActivityId,
    currentActivity,
    restartCooldown,
    isRestarting,
    restartError,
    clearActivities,
    setRestartCooldown,
    cleanupCooldown
} = useJobState()

const {
    sidebarPosition,
    loadSettings
} = useSettingsState()

// Initialize swipe gestures for mobile
const { isDragging, dragTarget, sidebarTransform, settingsDragOffset } = useSwipeGesture({
    sidebarWidth: 288,
    onOpenSidebar: () => { isSidebarOpen.value = true },
    onCloseSidebar: closeSidebar,
    onOpenSettings: () => { showSettingsModal.value = true },
    onCloseSettings: () => { showSettingsModal.value = false },
    isSidebarOpen,
    isSettingsOpen: showSettingsModal
})

provide('swipeState', { isDragging, dragTarget, sidebarTransform, settingsDragOffset })

// Setup state (first-run check)
const needsSetup = ref(false)
const setupChecked = ref(false)

const checkSetup = async () => {
    try {
        const res = await fetch('/setup/status')
        if (res.ok) {
            const data = await res.json()
            needsSetup.value = !data.configured
        }
    } catch {
        // Server not available - don't show setup
    }
    setupChecked.value = true
}

const onSetupComplete = () => {
    needsSetup.value = false
    // Reload the page to reinitialize with new config
    window.location.reload()
}

// Computed for showing settings during drag
const isDraggingSettings = computed(() => isDragging.value && dragTarget.value === 'settings')

const {
    artifacts,
    fileToView,
    workspaceTabs,
    activeTabId,
    saveWorkspace,
    loadWorkspace,
    resetWorkspace,
    closeTab: closeTabFromState,
    openFile: openFileFromState,
    findFileInArtifacts,
    revealFileInTree
} = useWorkspaceState()

// Template refs
const sidebarRef = ref(null)
const chatViewRef = ref(null)

// Scheduler detail modal state
const showSchedulerDetailModal = ref(false)
const selectedSchedulerId = ref(null)

// Create item modal state
const showCreateModal = ref(false)
const createMode = ref('folder') // 'folder', 'file', or 'rename'
const renameItem = ref(null) // item being renamed

const showSchedulerDetail = (schedulerId) => {
    selectedSchedulerId.value = schedulerId
    showSchedulerDetailModal.value = true
    showScheduledJobsModal.value = false
}

const handleSchedulerConversationSelect = (convId) => {
    showSchedulerDetailModal.value = false
    showScheduledJobsModal.value = false
    handleSelectConversation(convId)
}

// Handle optimistic new conversation from scheduler
const handleNewConversation = (conv) => {
    // Add to beginning of list if not already present
    if (!conversations.value.find(c => c.id === conv.id)) {
        conversations.value.unshift(conv)
    }
}

// Create folder/file handlers
const handleCreateFolder = () => {
    createMode.value = 'folder'
    showCreateModal.value = true
}

const handleCreateFile = () => {
    createMode.value = 'file'
    showCreateModal.value = true
}

const handleRenameFile = (item) => {
    renameItem.value = item
    createMode.value = 'rename'
    showCreateModal.value = true
}

const handleRenameItem = async (newName) => {
    showCreateModal.value = false
    const item = renameItem.value
    renameItem.value = null

    if (!item) return

    // Build new path (keep the directory, change the name)
    const pathParts = item.path.split('/')
    pathParts.pop()
    const newPath = pathParts.length > 0 ? `${pathParts.join('/')}/${newName}` : newName

    try {
        await api.moveArtifact(item.path, newPath)
        toast.success(t('toast.fileRenamed'))
        refreshArtifacts()
    } catch (e) {
        toast.error(e.message)
    }
}

const handleCreateItem = async (name) => {
    showCreateModal.value = false
    try {
        if (createMode.value === 'folder') {
            await api.createDirectory(name)
            toast.success(t('toast.folderCreated'))
        } else {
            // Add .txt extension if no extension provided
            let fileName = name
            if (!fileName.includes('.')) {
                fileName = fileName + '.txt'
            }
            await api.createFile(fileName, '')
            toast.success(t('toast.fileCreated'))
            // Open the newly created file
            openFile({ path: fileName, name: fileName })
        }
        refreshArtifacts()
    } catch (e) {
        toast.error(e.message)
    }
}

const handleMoveToFolder = async (sourcePath, destFolderPath) => {
    const fileName = sourcePath.split('/').pop()
    const newPath = destFolderPath ? `${destFolderPath}/${fileName}` : fileName

    try {
        await api.moveArtifact(sourcePath, newPath)
        toast.success(t('toast.fileMoved'))
        refreshArtifacts()
    } catch (e) {
        toast.error(e.message)
    }
}

// Server availability state
const serverUnavailable = ref(false)
const isCheckingServer = ref(false)

// Conversation loading control
let conversationAbortController = null
let conversationLoaderTimeout = null
let pollingAbortController = null // Abort controller for job polling

// Job Cancellation
const confirmCancel = async () => {
    showCancelConfirm.value = false
    if (!currentJobId.value) return

    isCancelling.value = true
    try {
        await api.cancelJob(currentJobId.value)
    } catch (e) {
        console.error('Cancel failed:', e)
        isCancelling.value = false
    }
}

const cancelCancel = () => {
    showCancelConfirm.value = false
}

// New chat
const newChat = () => {
    saveWorkspace(conversationId.value)
    saveInputForConversation(conversationId.value)

    messages.value = []
    conversationId.value = null
    localStorage.removeItem('conversationId')
    pendingQuestion.value = null
    pendingOAuth.value = null
    isLoading.value = false
    clearActivities()
    window.history.pushState({}, '', '/')
    refreshConversations()
    resetWorkspace()

    // Clear input for new chat
    inputText.value = ''

    nextTick(() => chatViewRef.value?.inputBox?.focus())
}

// Navigate to home (same as newChat)
const navigateHome = () => newChat()

// Load conversation
const loadConversation = async (convId) => {
    if (convId === conversationId.value && messages.value.length > 0) return

    // Cancel any in-flight conversation load request
    if (conversationAbortController) {
        conversationAbortController.abort()
    }
    conversationAbortController = new AbortController()
    const signal = conversationAbortController.signal

    // Cancel any ongoing polling from previous conversation
    if (pollingAbortController) {
        pollingAbortController.abort()
        pollingAbortController = null
    }

    // Save workspace and input only when switching to a DIFFERENT conversation
    if (convId !== conversationId.value) {
        saveWorkspace(conversationId.value)
        saveInputForConversation(conversationId.value)
    }

    // Immediately update selection for instant visual feedback
    conversationId.value = convId

    // Load saved input for this conversation (if any)
    loadInputForConversation(convId)
    localStorage.setItem('conversationId', convId)
    window.history.pushState({}, '', `/c/${convId}`)
    messages.value = [] // Clear messages while loading
    isLoading.value = true // Prevent EmptyState from showing

    // Delayed visual loader - only show if loading takes > 200ms
    clearTimeout(conversationLoaderTimeout)
    showConversationLoader.value = false
    conversationLoaderTimeout = setTimeout(() => {
        showConversationLoader.value = true
    }, 200)

    // Optimistic update - immediately mark as read in local state (sidebar)
    const conv = conversations.value.find(c => c.id === convId)
    if (conv) {
        conv.is_unread = false
        conv.unread_count = 0
    }
    pendingQuestion.value = null
    pendingOAuth.value = null
    clearActivities()

    try {
        // IMPORTANT: Fetch messages FIRST to get old read_at (for unread separator)
        // THEN mark as read in backend
        const data = await api.getConversationMessages(convId, signal)

        // Check if request was aborted (user clicked another conversation)
        if (signal.aborted) return

        // Now mark as read in backend (fire and forget - don't block UI)
        api.markConversationRead(convId).catch(e => console.warn('Failed to mark as read:', e))

        loadWorkspace(convId)
        activeTabId.value = 'chat'

        // API now returns {messages: [...], read_at: "..."}
        const messageList = data.messages || data
        readAt.value = data.read_at || null

        messages.value = messageList.map((m, idx) => ({
            id: `loaded-${convId}-${idx}`,
            dbId: m.id,
            role: m.role,
            text: m.content,
            created_at: m.created_at
        }))

        // Clear loader now that messages are loaded
        clearTimeout(conversationLoaderTimeout)
        showConversationLoader.value = false
        isLoading.value = false

        nextTick(() => chatViewRef.value?.forceScrollToBottom())

        // Check for active job (will set isLoading=true if agent is working)
        const activeJobRes = await fetch(`/conversations/${convId}/active-job`, { signal })
        if (signal.aborted) return

        if (activeJobRes.ok) {
            const activeJob = await activeJobRes.json()

            if (activeJob.job_id) {
                setStoredJobId(convId, activeJob.job_id)

                if (activeJob.status === 'waiting_for_input') {
                    const jobData = await api.pollJob(activeJob.job_id)
                    pendingQuestion.value = {
                        jobId: activeJob.job_id,
                        question: jobData.question,
                        options: jobData.question_options
                    }
                    isLoading.value = true
                    return // Active job manages its own loading state
                } else if (activeJob.status === 'oauth_pending') {
                    const jobData = await api.pollJob(activeJob.job_id)
                    pendingOAuth.value = {
                        jobId: activeJob.job_id,
                        provider: jobData.oauth_provider,
                        authUrl: jobData.oauth_url,
                        reason: jobData.oauth_reason
                    }
                    isLoading.value = true
                    return // Active job manages its own loading state
                } else if (activeJob.status === 'pending' || activeJob.status === 'running') {
                    isLoading.value = true
                    resumePolling(activeJob.job_id, convId)
                    return // Polling manages its own loading state
                }
            }
        }
    } catch (e) {
        // Ignore AbortError - it means user clicked another conversation
        if (e.name === 'AbortError') return

        // Offline or timeout → show overlay instead of error in chat
        if (e.name === 'OfflineError' || e.name === 'TimeoutError') {
            serverUnavailable.value = true
            clearTimeout(conversationLoaderTimeout)
            showConversationLoader.value = false
            isLoading.value = false
            return
        }

        console.error('Failed to load conversation', e)
        // Show error message in chat
        messages.value = [{
            id: genMsgId(),
            role: 'system',
            text: `**${t('errors.loadConversationError', 'Failed to load conversation')}**\n\n${e.message}`
        }]
    }
    // Clear delayed loader
    clearTimeout(conversationLoaderTimeout)
    showConversationLoader.value = false
    isLoading.value = false
}

// Resume polling (for active jobs when loading conversation)
const resumePolling = async (jobId, convId) => {
    currentJobId.value = jobId
    const POLL_INTERVAL = 1000  // Poll every 1s instead of 250ms

    // Create abort controller for this polling session
    pollingAbortController = new AbortController()
    const abortSignal = pollingAbortController

    try {
        while (true) {
            // Check if polling was aborted (user switched conversations)
            if (abortSignal.signal.aborted) {
                console.log('Polling aborted - user switched conversations')
                break
            }

            const job = await api.pollJob(jobId, lastActivityId.value)

            // Check again after async operation
            if (abortSignal.signal.aborted) {
                console.log('Polling aborted after poll - user switched conversations')
                break
            }

            // Only update UI if still on the same conversation
            const isCurrentConversation = convId === conversationId.value
            if (isCurrentConversation) {
                if (job.activities?.length > 0) {
                    activities.value = [...activities.value, ...job.activities]
                    lastActivityId.value = job.last_activity_id
                }
                currentActivity.value = job.current
            }

            if (job.status === 'completed' || job.status === 'failed' || job.status === 'cancelled') {
                clearStoredJobId(convId)
                if (isCurrentConversation) {
                    isLoading.value = false
                    clearActivities()
                    await refreshArtifacts()  // Refresh artifacts BEFORE messages so file links work
                    await reloadMessages({ targetConversationId: convId })
                } else {
                    // Optimistic update: show unread badge immediately for non-active conversation
                    const conv = conversations.value.find(c => c.id === convId)
                    if (conv) {
                        conv.has_active_job = false
                        conv.has_pending_question = false
                        conv.unread_count = (conv.unread_count || 0) + 1
                        conv.is_unread = true
                    }
                }
                // Force refresh to get authoritative state from backend
                setTimeout(() => forceRefreshConversations(), 1000)
                break
            }
            if (job.status === 'waiting_for_input') {
                if (isCurrentConversation) {
                    pendingQuestion.value = {
                        jobId: jobId,
                        question: job.question,
                        options: job.question_options
                    }
                }
                break
            }
            if (job.status === 'oauth_pending') {
                if (isCurrentConversation) {
                    pendingOAuth.value = {
                        jobId: jobId,
                        provider: job.oauth_provider,
                        authUrl: job.oauth_url,
                        reason: job.oauth_reason
                    }
                }
                break
            }

            await new Promise(r => setTimeout(r, POLL_INTERVAL))
        }
    } catch (e) {
        if (e.name !== 'AbortError') {
            console.error('Resume polling failed:', e)
        }
        // Only update UI if still on the same conversation
        if (convId === conversationId.value) {
            isLoading.value = false
        }
        clearStoredJobId(convId)
    } finally {
        currentJobId.value = null
        isCancelling.value = false
        if (pollingAbortController === abortSignal) {
            pollingAbortController = null
        }
    }
}

// Reload messages from DB (uses shared function from composable)
const reloadMessages = (options = {}) => reloadMessagesFromState(api, options)

// Handle conversation selection
const handleSelectConversation = (convId) => {
    closeSidebar()
    loadConversation(convId)
}

// Handle conversation archiving (soft delete)
const handleArchiveConversation = async (convId) => {
    try {
        await api.archiveConversation(convId)
        await refreshConversations()
        await refreshArchivedConversations()

        if (convId === conversationId.value) {
            newChat()
        }
    } catch (e) {
        console.error('Archive failed:', e)
        alert(t('errors.archiveError'))
    }
}

// Handle conversation restore from archive
const handleRestoreConversation = async (convId) => {
    try {
        await api.restoreConversation(convId)
        await refreshConversations()
        await refreshArchivedConversations()
    } catch (e) {
        console.error('Restore failed:', e)
        alert(t('errors.restoreError'))
    }
}

// Handle permanent deletion of archived conversation
const handleDeleteArchivedConversation = async (convId) => {
    if (!confirm(t('sidebar.confirmDeletePermanent'))) return

    try {
        await api.deleteConversation(convId)
        await refreshArchivedConversations()
    } catch (e) {
        console.error('Delete failed:', e)
        alert(t('errors.deleteError'))
    }
}

// Fork conversation
const handleForkConversation = async (messageId) => {
    if (!conversationId.value) return

    try {
        const result = await api.forkConversation(conversationId.value, messageId)
        await refreshConversations()
        nextTick(() => sidebarRef.value?.scrollConversationsToTop())
        await loadConversation(result.conversation_id)
        nextTick(() => chatViewRef.value?.inputBox?.focus())
    } catch (e) {
        console.error('Fork failed:', e)
        alert('Nie udało się sforkować konwersacji: ' + e.message)
    }
}

// Refresh artifacts
const artifactsRefreshKey = ref(0)
provide('artifactsRefreshKey', artifactsRefreshKey)

const refreshArtifacts = async () => {
    try {
        artifacts.value = await api.getArtifacts()
        artifactsRefreshKey.value++ // trigger refresh of open folder contents
    } catch (e) {
        console.error('Failed to load artifacts', e)
    }
}

// Throttle utility (inline, without external library)
// Returns void - callers should not await the result
const REFRESH_THROTTLE_MS = 3000
const createThrottle = (fn, delay) => {
    let lastCall = 0
    let pending = false
    return (...args) => {
        const now = Date.now()
        if (now - lastCall >= delay) {
            lastCall = now
            fn(...args)
        } else if (!pending) {
            pending = true
            setTimeout(() => {
                pending = false
                lastCall = Date.now()
                fn(...args)
            }, delay - (now - lastCall))
        }
    }
}

// Refresh conversations (throttled to max 1 refresh per 3 seconds)
const refreshConversations = createThrottle(async () => {
    try {
        const apiConversations = await api.getConversations()

        // Preserve optimistic updates that aren't in API response yet
        const optimisticUpdates = conversations.value.filter(conv =>
            conv.has_active_job && !apiConversations.find(c => c.id === conv.id)
        )

        // Merge: optimistic updates first (they're newest), then API response
        conversations.value = [...optimisticUpdates, ...apiConversations]
    } catch (e) {
        console.error('Failed to load conversations', e)
    }
}, REFRESH_THROTTLE_MS)

// Force refresh conversations (bypasses throttle, used after job completion)
const forceRefreshConversations = async () => {
    try {
        const apiConversations = await api.getConversations()
        const optimisticUpdates = conversations.value.filter(conv =>
            conv.has_active_job && !apiConversations.find(c => c.id === conv.id)
        )
        conversations.value = [...optimisticUpdates, ...apiConversations]
    } catch (e) {
        console.error('Failed to load conversations', e)
    }
}

// Refresh archived conversations
const refreshArchivedConversations = async () => {
    try {
        archivedConversations.value = await api.getArchivedConversations()
    } catch (e) {
        console.error('Failed to load archived conversations', e)
    }
}

// File operations
const uploadFile = async (file) => {
    try {
        await api.uploadArtifact(file)
        refreshArtifacts()
    } catch (e) {
        alert(t('errors.uploadError') + ': ' + e.message)
    }
}

const uploadFiles = async (files, targetPath = '') => {
    try {
        const results = await api.uploadArtifacts(files, targetPath)
        refreshArtifacts()
        return results
    } catch (e) {
        alert(t('errors.uploadError') + ': ' + e.message)
        return []
    }
}

const deleteItem = async (item) => {
    try {
        await api.deleteArtifact(item.path)
        refreshArtifacts()
        toast.success(t('toast.fileDeleted'))
    } catch (e) {
        toast.error(t('errors.deleteError') + ': ' + e.message)
    }
}

const selectFile = (item) => {
    // Placeholder for file selection
}

const closeTab = (tabId) => closeTabFromState(tabId, conversationId.value)

const openFile = (item) => openFileFromState(item, conversationId.value, closeSidebar)

const handleFileClick = (fileNameOrPath) => {
    // For full /workspace paths, open directly without checking artifacts
    // (children are lazy-loaded, so nested files won't be in artifacts.value)
    if (fileNameOrPath.startsWith('/workspace/')) {
        const relativePath = fileNameOrPath.replace(/^\/workspace\/artifacts\/?/, '').replace(/^\/workspace\/?/, '')
        const name = relativePath.split('/').pop()
        const isDir = !name.includes('.')
        isSidebarOpen.value = true
        revealFileInTree(relativePath)
        if (!isDir) {
            openFile({ path: relativePath, name })
        }
        return
    }

    // For simple filenames, try to find in artifacts
    const file = findFileInArtifacts(fileNameOrPath)
    if (file) {
        isSidebarOpen.value = true
        revealFileInTree(file.path)
        openFile(file)
        return
    }

    // Then try to find as directory (includeDirs = true)
    const dir = findFileInArtifacts(fileNameOrPath, true)
    if (dir && dir.is_dir) {
        // For directories, open sidebar to show files
        isSidebarOpen.value = true
        return
    }

    console.warn('File not found in workspace:', fileNameOrPath)
}

// Listen for file open events from AI message badges
if (typeof window !== 'undefined') {
    window.addEventListener('open-file', (event) => {
        handleFileClick(event.detail)
    })

    // Event delegation for file-link clicks (data-file-path attribute)
    document.addEventListener('click', (event) => {
        const fileLink = event.target.closest('.file-link[data-file-path]')
        if (fileLink) {
            const filePath = fileLink.getAttribute('data-file-path')
            if (filePath) {
                handleFileClick(filePath)
            }
        }
    })
}

// Settings modal
const openSettingsModal = () => {
    showSettingsModal.value = true
    fetchRestartStatus()
}

// Container Restart Functions
const fetchRestartStatus = async () => {
    try {
        const res = await fetch('/container/restart-status')
        if (res.ok) {
            const data = await res.json()
            setRestartCooldown(data.cooldown_remaining)
        }
    } catch (e) {
        console.error('Failed to fetch restart status', e)
    }
}

const requestRestart = () => {
    showRestartConfirm.value = true
    restartError.value = null
}

const confirmRestart = async () => {
    showRestartConfirm.value = false
    isRestarting.value = true
    restartError.value = null

    try {
        const res = await fetch('/container/restart', { method: 'POST' })

        if (res.status === 429) {
            const data = await res.json()
            restartError.value = data.detail
            isRestarting.value = false
            fetchRestartStatus()
            return
        }

        if (!res.ok) {
            throw new Error('Restart failed')
        }

        startReconnection()

    } catch (e) {
        restartError.value = e.message
        isRestarting.value = false
    }
}

const cancelRestart = () => {
    showRestartConfirm.value = false
}

const startReconnection = () => {
    const maxAttempts = 60
    let attempts = 0

    const checkHealth = async () => {
        attempts++
        try {
            const res = await fetch('/health')
            if (res.ok) {
                isRestarting.value = false
                fetchRestartStatus()
                refreshArtifacts()
                refreshConversations()
                return
            }
        } catch (e) {
            // Expected during restart
        }

        if (attempts < maxAttempts) {
            setTimeout(checkHealth, 1000)
        } else {
            restartError.value = 'Container did not restart. Please refresh the page.'
            isRestarting.value = false
        }
    }

    setTimeout(checkHealth, 2000)
}

// Global keyboard handler
const handleGlobalKeydown = (e) => {
    if (e.key === 'Escape') {
        if (showCreateModal.value) {
            showCreateModal.value = false
        } else if (showRestartConfirm.value) {
            showRestartConfirm.value = false
        } else if (showMobileNav.value) {
            showMobileNav.value = false
        } else if (showSchedulerDetailModal.value) {
            showSchedulerDetailModal.value = false
        } else if (showScheduledJobsModal.value) {
            showScheduledJobsModal.value = false
        } else if (showIntegrationsModal.value) {
            showIntegrationsModal.value = false
        } else if (showAppsModal.value) {
            showAppsModal.value = false
        } else if (showSettingsModal.value) {
            showSettingsModal.value = false
        } else if (fileToView.value) {
            fileToView.value = null
        }
    }
}

// Handle browser back/forward navigation
const handlePopstate = async () => {
    const urlConvId = getConversationFromUrl()
    if (urlConvId && urlConvId !== conversationId.value) {
        await loadConversation(urlConvId)
    } else if (!urlConvId) {
        newChat()
    }
}

// Server health check
const checkServerHealth = async () => {
    const isAvailable = await api.checkHealth()
    serverUnavailable.value = !isAvailable
    return isAvailable
}

// Retry connection when server is unavailable (with exponential backoff)
const retryConnection = async () => {
    if (isCheckingServer.value) return
    isCheckingServer.value = true

    const maxAttempts = 3
    for (let i = 0; i < maxAttempts; i++) {
        const isAvailable = await checkServerHealth()
        if (isAvailable) {
            // Server is back - reload data
            refreshArtifacts()
            refreshConversations()
            refreshArchivedConversations()
            if (conversationId.value) {
                loadConversation(conversationId.value).catch(() => {})
            }
            break
        }
        if (i < maxAttempts - 1) {
            await new Promise(r => setTimeout(r, 1000 * Math.pow(2, i)))
        }
    }
    isCheckingServer.value = false
}

// Handle browser offline/online events (more reliable than navigator.onLine)
const handleOffline = () => {
    serverUnavailable.value = true
}

const handleOnline = () => {
    // Browser detected connection restored - try to reconnect
    retryConnection()
}

// Initialize LogRocket user identification
const initLogRocket = async () => {
    try {
        const res = await fetch('/user-info')
        if (res.ok) {
            const data = await res.json()
            if (window.LogRocket && data.user_id) {
                window.LogRocket.identify(data.user_id, {
                    domain: data.domain
                })
            }
        }
    } catch (e) {
        console.warn('Failed to init LogRocket:', e)
    }
}

// Mount
onMounted(async () => {
    loadSettings()
    loadSidebarCollapsed()

    window.addEventListener('keydown', handleGlobalKeydown)
    window.addEventListener('popstate', handlePopstate)
    window.addEventListener('offline', handleOffline)
    window.addEventListener('online', handleOnline)

    // Check if first-run setup is needed
    await checkSetup()
    if (needsSetup.value) return

    // Initialize LogRocket (fire and forget)
    initLogRocket()

    // Check server health first (with short timeout for faster offline detection)
    const isAvailable = await checkServerHealth()

    if (isAvailable) {
        // Server is available - load data (don't await, run in parallel)
        refreshArtifacts()
        refreshConversations()
        refreshArchivedConversations()

        if (conversationId.value) {
            // Don't block on loadConversation - let it run async
            loadConversation(conversationId.value).catch(() => {})
            // Focus input only when viewing existing conversation
            nextTick(() => chatViewRef.value?.inputBox?.focus())
        }
    }
})

// Unmount
onUnmounted(() => {
    window.removeEventListener('keydown', handleGlobalKeydown)
    window.removeEventListener('popstate', handlePopstate)
    window.removeEventListener('offline', handleOffline)
    window.removeEventListener('online', handleOnline)
    cleanupCooldown()
    cleanupBalancePolling()
    clearTimeout(conversationLoaderTimeout)
    conversationAbortController?.abort()
})
</script>
