<template>
    <div class="flex-1 flex flex-col overflow-hidden">
        <!-- Scrollable content wrapper -->
        <div class="flex-1 overflow-hidden relative">
            <!-- Chat Tab Content -->
            <div
                v-show="activeTabId === 'chat'"
                class="h-full"
            >
                <!-- Empty State -->
                <EmptyState
                    v-if="messages.length === 0 && !isLoading"
                    @fill-prompt="fillPromptFromDemo"
                />

                <!-- Conversation Loading State (delayed to avoid flash on fast loads) -->
                <div
                    v-if="messages.length === 0 && showConversationLoader && !pendingQuestion && !pendingOAuth"
                    class="h-full flex items-center justify-center"
                >
                    <div class="flex items-center gap-2">
                        <span class="loading-dot loading-dot-1"></span>
                        <span class="loading-dot loading-dot-2"></span>
                        <span class="loading-dot loading-dot-3"></span>
                    </div>
                </div>

                <!-- Virtualized Messages List -->
                <VirtualMessageList
                    v-if="messages.length > 0"
                    ref="virtualMessageList"
                    :messages="messages"
                    :read-at="readAt"
                    v-model:isAtBottom="isAtBottom"
                    @fork="$emit('fork', $event)"
                    @open-file="$emit('open-file', $event)"
                    @scroll="handleChatScroll"
                    @mark-unread="handleMarkUnread"
                    @edit="handleEditMessage"
                >
                    <template #footer>
                        <!-- Activity Stream (shows what agent is doing) -->
                        <ActivityStream
                            v-if="isLoading && !pendingQuestion && !pendingOAuth"
                            :activities="activities"
                            :is-loading="isLoading"
                            :current-activity="currentActivity"
                            :max-visible="5"
                            :suggestions="suggestions"
                            @suggestion-select="handleRelatedQuestionSelect"
                        />

                        <!-- Long thinking hint -->
                        <LoadingIndicator
                            :visible="isLoading && !pendingQuestion && !pendingOAuth && activities.length === 0"
                            :current-activity="currentActivity"
                            :activities="activities"
                            @new-chat="$emit('new-chat')"
                        />
                        <QuestionPrompt
                            :question="pendingQuestion"
                            @submit="submitQuestionResponse"
                        />
                        <OAuthPrompt
                            :oauth="pendingOAuth"
                            @start-oauth="startOAuth"
                        />
                    </template>
                </VirtualMessageList>
            </div>

            <!-- File Tab Contents -->
            <div
                v-for="tab in workspaceTabs.filter(t => t.type === 'file')"
                :key="tab.id"
                v-show="activeTabId === tab.id"
                class="h-full overflow-auto"
            >
                <FileTabContent :file-path="tab.path" @saved="$emit('refresh-artifacts')" />
            </div>

            <!-- Scroll to bottom button -->
            <Transition name="fade">
                <button
                    v-if="!isAtBottom && activeTabId === 'chat' && messages.length > 0"
                    @click="scrollToBottomSmooth"
                    class="absolute bottom-4 right-4 md:right-8 p-3 rounded-full
                           bg-[var(--bg-elevated)] border border-[var(--border-subtle)]
                           shadow-lg hover:bg-[var(--bg-surface)] hover:scale-110
                           transition-all duration-200 z-20"
                    :title="$t('chat.scrollToBottom')"
                >
                    <ChevronDown class="w-5 h-5 text-[var(--text-secondary)]" />
                </button>
            </Transition>
        </div>

        <!-- Input Area - Only visible when chat tab is active -->
        <div v-show="activeTabId === 'chat'" class="px-4 md:px-6 pt-4 pb-6 shrink-0 bg-[var(--bg-base)]">
            <div class="max-w-3xl mx-auto">
                <!-- Post-response suggestions (after bot finishes) -->
                <PostResponseSuggestions
                    v-if="showPostResponseSuggestions"
                    :suggestions="postResponseSuggestions"
                    @select="handlePostResponseSelect"
                    class="mb-3"
                />

                <!-- File Attachments Preview Gallery -->
                <div v-if="attachedFiles.length > 0" class="mb-3 flex flex-wrap gap-2">
                    <div
                        v-for="(file, index) in attachedFiles"
                        :key="file.id"
                        class="relative group bg-[var(--bg-surface)] border border-[var(--border-subtle)] rounded-lg overflow-hidden hover:border-blue-500/40 transition-all"
                        style="width: 80px; height: 80px;"
                    >
                        <!-- Image preview -->
                        <img
                            v-if="file.previewUrl"
                            :src="file.previewUrl"
                            :alt="file.name"
                            class="w-full h-full object-cover"
                        />
                        <!-- Non-image file -->
                        <div v-else class="w-full h-full flex flex-col items-center justify-center p-2 text-center">
                            <span class="text-2xl mb-1">📄</span>
                            <span class="text-[10px] text-[var(--text-muted)] truncate w-full px-1">{{ file.name }}</span>
                        </div>
                        <!-- Uploading overlay -->
                        <div
                            v-if="file.uploading"
                            class="absolute inset-0 bg-black/60 flex items-center justify-center"
                        >
                            <div class="flex items-center gap-1">
                                <span class="w-1.5 h-1.5 rounded-full bg-blue-400 animate-bounce" style="animation-delay: 0ms"></span>
                                <span class="w-1.5 h-1.5 rounded-full bg-sky-400 animate-bounce" style="animation-delay: 150ms"></span>
                                <span class="w-1.5 h-1.5 rounded-full bg-cyan-400 animate-bounce" style="animation-delay: 300ms"></span>
                            </div>
                        </div>
                        <!-- Remove/Cancel button -->
                        <button
                            @click="removeAttachment(index)"
                            :title="file.uploading ? $t('common.cancel') : $t('chat.removeAttachment')"
                            class="absolute top-1 right-1 w-5 h-5 rounded-full text-white flex items-center justify-center transition-opacity hover:scale-110"
                            :class="file.uploading
                                ? 'bg-red-500/80 hover:bg-red-500 opacity-100'
                                : 'bg-red-500 hover:bg-red-600 opacity-100 md:opacity-0 md:group-hover:opacity-100'"
                        >
                            <span class="text-xs font-bold leading-none">×</span>
                        </button>
                    </div>
                </div>

                <!-- Input container with glow -->
                <div
                    class="relative"
                    @dragenter.prevent="isDraggingOnInput = true"
                    @dragover.prevent
                    @dragleave="handleInputDragLeave"
                    @drop.prevent="handleInputDrop"
                >
                    <!-- Drag & drop overlay -->
                    <div
                        v-if="isDraggingOnInput"
                        class="absolute inset-0 z-20 rounded-2xl bg-blue-500/20 border-2 border-dashed border-blue-500 flex items-center justify-center backdrop-blur-sm overflow-hidden"
                    >
                        <div class="text-center pointer-events-none">
                            <Upload class="w-6 h-6 text-blue-400 mx-auto mb-1" />
                            <span class="text-xs text-blue-300 font-medium">{{ $t('chat.dropFilesOrImages') }}</span>
                        </div>
                    </div>

                    <!-- Outer glow on focus -->
                    <div class="absolute -inset-[2px] rounded-2xl opacity-0 transition-all duration-500 blur-md"
                         :class="inputFocused ? 'opacity-100' : ''"
                         style="background: linear-gradient(135deg, rgba(37, 99, 235, 0.4), rgba(14, 165, 233, 0.3), rgba(6, 182, 212, 0.4));"></div>

                    <!-- Border glow layer -->
                    <div class="absolute -inset-[1px] rounded-2xl opacity-0 transition-all duration-300"
                         :class="inputFocused ? 'opacity-100' : ''"
                         style="background: linear-gradient(135deg, rgba(37, 99, 235, 0.6), rgba(14, 165, 233, 0.4), rgba(6, 182, 212, 0.6));"></div>

                    <!-- Glass input container -->
                    <div class="relative bg-[var(--bg-surface)] rounded-2xl transition-all duration-300 border border-transparent"
                         :class="inputFocused ? 'border-blue-500/30' : 'border-[var(--border-subtle)]'">
                        <textarea
                            ref="inputBox"
                            v-model="inputText"
                            @keydown="handleKeydown"
                            @input="onMentionInput"
                            @focus="inputFocused = true"
                            @blur="inputFocused = false"
                            @paste="handlePaste"
                            rows="1"
                            :placeholder="$t('chat.messagePlaceholder')"
                            :disabled="isLoading"
                            class="w-full bg-transparent text-[15px] text-[var(--text-primary)] rounded-2xl pl-14 pt-[21px] pb-[15px] pr-14
                                   focus:outline-none resize-none custom-scroll leading-normal overflow-hidden
                                   placeholder:text-[var(--text-muted)] transition-colors"
                            style="min-height: 56px; max-height: 200px;"
                        ></textarea>

                        <!-- Attach files button -->
                        <label
                            class="absolute left-4 top-[17px] p-1.5 cursor-pointer
                                   text-[var(--text-muted)] hover:text-blue-400
                                   transition-colors duration-200"
                            :title="$t('chat.attachFiles')"
                        >
                            <Plus class="w-5 h-5" />
                            <input
                                type="file"
                                class="hidden"
                                @change="handleFileInputChange"
                                multiple
                                :disabled="isLoading"
                            >
                        </label>

                        <!-- Send / Stop button -->
                        <button
                            v-if="isLoading && currentJobId"
                            @click="stopExecution"
                            :disabled="isCancelling"
                            class="absolute right-3 bottom-3 p-2.5 rounded-xl
                                   bg-gradient-to-r from-red-500 to-orange-500 text-white
                                   shadow-lg shadow-red-500/25
                                   hover:scale-110 hover:shadow-red-500/40
                                   disabled:opacity-50 disabled:scale-100
                                   transition-all duration-200"
                            :title="$t('chat.stopExecution')"
                        >
                            <div v-if="isCancelling" class="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                            <Square v-else class="w-4 h-4 fill-current" />
                        </button>
                        <button
                            v-else
                            @click="sendMessage"
                            :disabled="!inputText.trim() || isLoading || hasUploadingFiles"
                            class="absolute right-3 bottom-3 p-2.5 rounded-xl
                                   bg-gradient-to-r from-blue-600 to-sky-500 text-white
                                   shadow-lg shadow-blue-500/25
                                   hover:scale-110 hover:shadow-blue-500/40
                                   disabled:opacity-40 disabled:scale-100 disabled:shadow-none
                                   transition-all duration-200"
                            :class="{ 'send-pulse': promptPending && inputText.trim() }"
                        >
                            <Send class="w-4 h-4" />
                        </button>
                    </div>

                    <!-- @-Mentions Autocomplete Dropdown - Glass -->
                    <div
                        v-if="showMentions"
                        ref="mentionDropdown"
                        class="absolute bottom-full left-0 mb-2 w-80 max-h-64 overflow-y-auto glass rounded-xl z-50 animate-modal-enter"
                    >
                        <!-- Schedulers Section -->
                        <template v-if="mentionResults.some(r => r.type === 'scheduler')">
                            <div class="px-4 py-2 text-xs text-zinc-500 border-b border-white/5 font-medium uppercase tracking-wider">
                                {{ $t('nav.scheduler') }}
                            </div>
                            <div
                                v-for="(item, idx) in mentionResults.filter(r => r.type === 'scheduler')"
                                :key="'scheduler-' + item.id"
                                :ref="el => setMentionItemRef(mentionResults.indexOf(item), el)"
                                @click="insertMention(item)"
                                @mouseenter="mentionIndex = mentionResults.indexOf(item)"
                                class="px-4 py-2.5 cursor-pointer flex items-center gap-3 text-sm transition-colors"
                                :class="mentionResults.indexOf(item) === mentionIndex ? 'bg-cyan-500/20 text-white' : 'text-zinc-300 hover:bg-white/5'"
                            >
                                <Clock class="w-4 h-4 text-cyan-400 flex-shrink-0" />
                                <span class="truncate">{{ item.name }}</span>
                            </div>
                        </template>
                        <!-- Files Section -->
                        <template v-if="mentionResults.some(r => r.type === 'file')">
                            <div class="px-4 py-2 text-xs text-zinc-500 border-b border-white/5 font-medium uppercase tracking-wider">
                                {{ $t('chat.files') }}
                            </div>
                            <div
                                v-for="(item, idx) in mentionResults.filter(r => r.type === 'file')"
                                :key="'file-' + item.path"
                                :ref="el => setMentionItemRef(mentionResults.indexOf(item), el)"
                                @click="insertMention(item)"
                                @mouseenter="mentionIndex = mentionResults.indexOf(item)"
                                class="px-4 py-2.5 cursor-pointer flex items-center gap-3 text-sm transition-colors"
                                :class="mentionResults.indexOf(item) === mentionIndex ? 'bg-blue-500/20 text-white' : 'text-zinc-300 hover:bg-white/5'"
                            >
                                <FileIcon class="w-4 h-4 text-blue-400 flex-shrink-0" />
                                <span class="truncate">{{ item.path }}</span>
                            </div>
                        </template>
                    </div>
                </div>

                <!-- Hint text with kbd styling -->
                <div class="flex items-center justify-center mt-4">
                    <p class="text-center text-xs text-zinc-600">
                        <kbd class="px-1.5 py-0.5 bg-white/5 rounded text-zinc-500 font-mono text-[10px]">{{ $t('chat.inputHint.shiftEnter') }}</kbd>
                        <span class="mx-2 text-zinc-700">{{ $t('chat.inputHint.forNewLine') }}</span>
                        <span class="mx-2 text-zinc-700">·</span>
                        <kbd class="px-1.5 py-0.5 bg-white/5 rounded text-zinc-500 font-mono text-[10px]">{{ $t('chat.inputHint.atSymbol') }}</kbd>
                        <span class="mx-2 text-zinc-700">{{ $t('chat.inputHint.toMentionFiles') }}</span>
                        <span class="mx-2 text-zinc-700">·</span>
                        <span class="text-zinc-700">{{ $t('chat.inputHint.dragAndDrop') }}</span>
                    </p>
                </div>
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted, onUnmounted, watch } from 'vue'
import { Plus, Send, FileIcon, ChevronDown, Upload, Square, Clock } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { useApi } from '../composables/useApi'

// State Composables (singletons)
import { useChatState, useUIState, useJobState, useWorkspaceState, useSettingsState } from '../composables/state'
import { useMentions } from '../composables/useMentions'
import { useToast } from '../composables/useToast'

// Components
import LoadingIndicator from './LoadingIndicator.vue'
import ActivityStream from './ActivityStream.vue'
import PostResponseSuggestions from './PostResponseSuggestions.vue'
import QuestionPrompt from './QuestionPrompt.vue'
import OAuthPrompt from './OAuthPrompt.vue'
import EmptyState from './EmptyState.vue'
import FileTabContent from './FileTabContent.vue'
import VirtualMessageList from './VirtualMessageList.vue'

const emit = defineEmits([
    'fork',
    'open-file',
    'refresh-artifacts',
    'refresh-conversations',
    'force-refresh-conversations',
    'new-chat'
])

const api = useApi()
const { t } = useI18n()
const toast = useToast()

// Initialize state composables
const {
    messages,
    inputText,
    isLoading,
    conversationId,
    conversations,
    pendingQuestion,
    pendingOAuth,
    attachedFiles,
    showConversationLoader,
    readAt,
    genMsgId,
    getStoredJobId,
    setStoredJobId,
    clearStoredJobId,
    clearChatState,
    addMessage,
    removeAttachment: removeAttachmentFromState,
    clearAttachments,
    reloadMessages: reloadMessagesFromState
} = useChatState()

const {
    inputFocused,
    isDraggingOnInput,
    promptPending,
    isAtBottom,
    showCancelConfirm
} = useUIState()

const {
    currentJobId,
    isCancelling,
    activities,
    lastActivityId,
    currentActivity,
    suggestions,
    postResponseSuggestions,
    postResponseSuggestionsConversationId,
    clearActivities,
    setSuggestions,
    preserveSuggestionsForPostResponse,
    clearPostResponseSuggestions
} = useJobState()

const {
    artifacts,
    workspaceTabs,
    activeTabId
} = useWorkspaceState()

const { playNotificationSound } = useSettingsState()

// Template refs
const virtualMessageList = ref(null)
const inputBox = ref(null)
const mentionDropdown = ref(null)
const mentionItemRefs = ref([])

// Set mention item ref (for scroll into view)
const setMentionItemRef = (idx, el) => {
    if (el) {
        mentionItemRefs.value[idx] = el
    }
}


// Expose inputBox for parent focus calls
defineExpose({ inputBox, scrollToBottom, forceScrollToBottom })

// @-Mentions (includes files and schedulers)
const {
    showMentions,
    mentionResults,
    mentionIndex,
    onMentionInput: mentionInputHandler,
    insertMention,
    handleMentionKeydown
} = useMentions(inputText, inputBox, api.searchArtifacts, api.searchSchedulers)

// Scroll selected mention item into view when navigating with arrow keys
watch(mentionIndex, (newIdx) => {
    nextTick(() => {
        const item = mentionItemRefs.value[newIdx]
        if (item && mentionDropdown.value) {
            item.scrollIntoView({ block: 'nearest', behavior: 'smooth' })
        }
    })
})

// Scroll handling - isAtBottom is now synced via v-model with VirtualMessageList
const handleChatScroll = () => {
    // isAtBottom is updated via v-model binding from VirtualMessageList
}

// Mark conversation as unread from a specific message
const handleMarkUnread = async (beforeTimestamp) => {
    if (!conversationId.value || !beforeTimestamp) return
    try {
        const result = await api.markConversationUnread(conversationId.value, beforeTimestamp)
        // Update local readAt to show unread separator
        readAt.value = result.read_at
        // Update sidebar to show unread count
        const conv = conversations.value.find(c => c.id === conversationId.value)
        if (conv) {
            conv.is_unread = true
            // Count messages after the new read_at
            const unreadCount = messages.value.filter(m =>
                m.role === 'assistant' && m.created_at && m.created_at > result.read_at
            ).length
            conv.unread_count = unreadCount
        }
        emit('refresh-conversations')
    } catch (e) {
        console.error('Failed to mark as unread:', e)
    }
}

// Edit mode state
const editingMessageId = ref(null)

// Handle edit message - populate input with message text and store message ID
const handleEditMessage = (data) => {
    if (!data?.text) return
    editingMessageId.value = data.id || null
    inputText.value = data.text
    // Focus the input box
    nextTick(() => {
        inputBox.value?.focus()
    })
}

const scrollToBottomSmooth = () => {
    virtualMessageList.value?.scrollToBottomSmooth()
}

// Conditional scroll - only scrolls if user is already at bottom
function scrollToBottom() {
    if (!isAtBottom.value) return
    nextTick(() => {
        virtualMessageList.value?.scrollToBottom()
    })
}

// Force scroll - always scrolls regardless of position (for user-initiated actions)
function forceScrollToBottom() {
    nextTick(() => {
        virtualMessageList.value?.scrollToBottom()
    })
}

// Auto-resize textarea
const autoResize = () => {
    const el = inputBox.value
    if (!el) return

    // If input is empty, reset to minimum height (mobile fix)
    if (!el.value.trim()) {
        el.style.height = '56px'
        el.style.overflowY = 'hidden'
        return
    }

    el.style.height = 'auto'
    const newHeight = Math.min(el.scrollHeight, 200)
    el.style.height = newHeight + 'px'
    el.style.overflowY = el.scrollHeight > 200 ? 'auto' : 'hidden'
}

const onMentionInput = (e) => {
    mentionInputHandler(e, autoResize)
}

const isMobile = () => window.innerWidth < 768

const handleKeydown = (e) => {
    if (handleMentionKeydown(e)) return
    if (e.key === 'Enter' && !e.shiftKey && !isMobile()) {
        e.preventDefault()
        sendMessage()
    }
}

// Job cancellation - immediate stop without confirmation
const stopExecution = async () => {
    if (!currentJobId.value || isCancelling.value) return

    isCancelling.value = true
    try {
        await api.cancelJob(currentJobId.value)
    } catch (e) {
        console.error('Stop failed:', e)
        isCancelling.value = false
    }
}

// Keep for backward compatibility with LoadingIndicator
const requestCancel = () => {
    stopExecution()
}

// Poll job until done
// targetConversationId: the conversation this job belongs to (captured at job start)
const pollJobUntilDone = async (jobId, targetConversationId = null) => {
    const POLL_INTERVAL = 1000  // Poll every 1s instead of 250ms
    const SIDEBAR_REFRESH_EVERY = 10  // Refresh sidebar every 10s
    let pollCount = 0
    // Use the target conversation ID passed in, or fall back to what the API returns
    let jobConversationId = targetConversationId

    while (true) {
        const job = await api.pollJob(jobId, lastActivityId.value)

        // Update from API response if we didn't have it initially
        if (!jobConversationId && job.conversation_id) {
            jobConversationId = job.conversation_id
        }

        // Only update UI if user is still viewing the conversation this job belongs to
        const isCurrentConversation = jobConversationId && jobConversationId === conversationId.value

        if (isCurrentConversation) {
            if (job.activities?.length > 0) {
                activities.value = [...activities.value, ...job.activities]
                lastActivityId.value = job.last_activity_id
                nextTick(() => scrollToBottom())
            }
            currentActivity.value = job.current

            // Capture suggestions (related questions)
            if (job.suggestions?.length > 0) {
                setSuggestions(job.suggestions)
            }
        }

        pollCount++
        if (pollCount % SIDEBAR_REFRESH_EVERY === 0) {
            emit('refresh-conversations')
        }

        if (job.status === 'completed') {
            emit('refresh-conversations')
            return { ...job, _isCurrentConversation: isCurrentConversation }
        }
        if (job.status === 'failed') {
            emit('refresh-conversations')
            throw new Error(job.error || 'Job failed')
        }
        if (job.status === 'cancelled') {
            emit('refresh-conversations')
            return {
                status: 'cancelled',
                result: job.result || t('errors.executionStopped'),
                _isCurrentConversation: isCurrentConversation
            }
        }
        if (job.status === 'waiting_for_input') {
            emit('refresh-conversations')
            return {
                status: 'waiting_for_input',
                jobId: jobId,
                question: job.question,
                options: job.question_options,
                _isCurrentConversation: isCurrentConversation
            }
        }
        if (job.status === 'oauth_pending') {
            emit('refresh-conversations')
            return {
                status: 'oauth_pending',
                jobId: jobId,
                provider: job.oauth_provider,
                authUrl: job.oauth_url,
                reason: job.oauth_reason,
                _isCurrentConversation: isCurrentConversation
            }
        }
        await new Promise(r => setTimeout(r, POLL_INTERVAL))
    }
}

// Reload messages from DB (uses shared function from composable)
// Pass targetConversationId to ensure we only update if still on the same conversation
const reloadMessages = async (options = {}) => {
    await reloadMessagesFromState(api, options)
}

// Send message
const sendMessage = async () => {
    const text = inputText.value.trim()
    if (!text) return

    // Clear post-response suggestions when user sends a new message
    clearPostResponseSuggestions()

    // If in edit mode, remove old message from UI instantly, delete from backend in background
    const wasEditing = editingMessageId.value && conversationId.value
    if (wasEditing) {
        // Instantly remove from UI (before adding new message)
        // Note: dbId is the database ID, id is the local generated ID
        const editIdx = messages.value.findIndex(m => m.dbId === editingMessageId.value)
        if (editIdx !== -1) {
            messages.value = messages.value.slice(0, editIdx)
        }
        // Delete from backend in background (don't await)
        const convId = conversationId.value
        const msgId = editingMessageId.value
        api.deleteMessagesFrom(convId, msgId).catch(e => {
            console.error('Failed to delete messages for edit:', e)
        })
        editingMessageId.value = null
    }

    clearActivities()
    await nextTick()

    // Use already uploaded files
    let uploadedMentions = ''
    let uploadedAttachments = []
    if (attachedFiles.value.length > 0) {
        uploadedAttachments = attachedFiles.value.map(f => f.uploadedPath).filter(Boolean)
        uploadedMentions = uploadedAttachments.length > 0
            ? ' ' + uploadedAttachments.map(p => `@${p}`).join(' ')
            : ''

        attachedFiles.value.forEach(f => {
            if (f.previewUrl) URL.revokeObjectURL(f.previewUrl)
        })
        attachedFiles.value = []
    }

    const localMsgId = genMsgId()
    messages.value.push({
        id: localMsgId,
        role: 'user',
        text: text,
        attachments: uploadedAttachments.length > 0 ? uploadedAttachments : undefined
    })
    inputText.value = ''
    promptPending.value = false
    nextTick(() => autoResize())

    await nextTick()
    forceScrollToBottom()
    isLoading.value = true

    try {
        const { job_id, conversation_id: convId, message_id } = await api.sendMessage(text + uploadedMentions, conversationId.value)

        // Update local message with database ID (needed for fork functionality)
        if (message_id) {
            const localMsg = messages.value.find(m => m.id === localMsgId)
            if (localMsg) {
                localMsg.dbId = message_id
            }
        }

        if (!conversationId.value) {
            // Optimistic update: add placeholder to conversations list immediately
            conversations.value.unshift({
                id: convId,
                preview: text.slice(0, 50) + (text.length > 50 ? '...' : ''),
                created_at: new Date().toISOString(),
                last_message_at: new Date().toISOString(),
                has_active_job: true,
                has_pending_question: false,
                is_unread: false,
                unread_count: 0
            })

            conversationId.value = convId
            localStorage.setItem('conversationId', convId)
            window.history.pushState({}, '', `/c/${convId}`)
        } else {
            // Optimistic update for existing conversation: update timestamp to move to top
            const existingConv = conversations.value.find(c => c.id === convId)
            if (existingConv) {
                existingConv.last_message_at = new Date().toISOString()
                existingConv.has_active_job = true
                existingConv.preview = text.slice(0, 50) + (text.length > 50 ? '...' : '')
            }
        }

        setStoredJobId(convId, job_id)
        currentJobId.value = job_id
        emit('refresh-conversations')

        // Pass convId to pollJobUntilDone to prevent mixing chats when user switches conversations
        const job = await pollJobUntilDone(job_id, convId)

        if (job.status === 'waiting_for_input') {
            if (job._isCurrentConversation) {
                pendingQuestion.value = {
                    jobId: job.jobId,
                    question: job.question,
                    options: job.options
                }
                scrollToBottom()
            }
            return
        }

        if (job.status === 'oauth_pending') {
            if (job._isCurrentConversation) {
                pendingOAuth.value = {
                    jobId: job.jobId,
                    provider: job.provider,
                    authUrl: job.authUrl,
                    reason: job.reason
                }
                scrollToBottom()
            }
            return
        }

        if (job.status === 'cancelled') {
            clearStoredJobId(convId)
            if (job._isCurrentConversation) {
                clearActivities()
                await reloadMessages({ targetConversationId: convId })
            }
            emit('refresh-artifacts')
            emit('refresh-conversations')
            return
        }

        clearStoredJobId(convId)

        if (job._isCurrentConversation) {
            // Preserve suggestions for post-response display before clearing
            preserveSuggestionsForPostResponse(convId)
            clearActivities()
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

        // Play notification sound when job completes successfully
        playNotificationSound()

        emit('refresh-artifacts')
        emit('refresh-conversations')

        // Delayed force refresh to get authoritative state from backend
        if (!job._isCurrentConversation) {
            setTimeout(() => emit('force-refresh-conversations'), 1000)
        }

    } catch (e) {
        console.error('Send message error:', e)
        // Only update UI if we're still on the same conversation
        // Note: convId may not be set if the error occurred before API response
        const currentConvId = conversationId.value

        if (currentConvId) {
            clearActivities()
            await reloadMessages({ targetConversationId: currentConvId })
            // Only show error message if still on the same conversation after async reload
            if (currentConvId === conversationId.value) {
                messages.value.push({
                    id: genMsgId(),
                    role: 'assistant',
                    text: `**${t('errors.error')}:** ${e.message}`
                })
            }
        }
    } finally {
        currentJobId.value = null
        isCancelling.value = false
        if (!pendingQuestion.value && !pendingOAuth.value) {
            isLoading.value = false
        }
        scrollToBottom()
        nextTick(() => inputBox.value?.focus())
    }
}

// Submit question response
const submitQuestionResponse = async (response) => {
    if (!response?.trim() || !pendingQuestion.value) return

    const jobId = pendingQuestion.value.jobId
    // Capture conversation ID BEFORE any async operations to prevent mixing chats
    const targetConvId = conversationId.value
    pendingQuestion.value = null
    currentJobId.value = jobId

    scrollToBottom()

    try {
        const trimmedResponse = response.trim()
        await api.submitAnswer(jobId, trimmedResponse)

        // Reload messages to get the question from database
        await reloadMessages()

        // Add user's response AFTER reloadMessages so it doesn't get overwritten
        messages.value.push({
            id: genMsgId(),
            role: 'user',
            text: trimmedResponse
        })
        scrollToBottom()

        const job = await pollJobUntilDone(jobId, targetConvId)

        if (job.status === 'waiting_for_input') {
            if (job._isCurrentConversation) {
                pendingQuestion.value = {
                    jobId: job.jobId,
                    question: job.question,
                    options: job.options
                }
                scrollToBottom()
            }
        } else if (job.status === 'oauth_pending') {
            // Show OAuth prompt when agent needs authorization
            if (job._isCurrentConversation) {
                pendingOAuth.value = {
                    jobId: job.jobId,
                    provider: job.provider,
                    authUrl: job.authUrl,
                    reason: job.reason
                }
                scrollToBottom()
            }
        } else if (job.status === 'cancelled') {
            clearStoredJobId(targetConvId)
            if (job._isCurrentConversation) {
                clearActivities()
                await reloadMessages({ targetConversationId: targetConvId })
            }
            if (targetConvId === conversationId.value) {
                isLoading.value = false
                scrollToBottom()
                nextTick(() => inputBox.value?.focus())
            }
            emit('refresh-artifacts')
            emit('refresh-conversations')
        } else {
            clearStoredJobId(targetConvId)
            if (job._isCurrentConversation) {
                // Preserve suggestions for post-response display before clearing
                preserveSuggestionsForPostResponse(targetConvId)
                clearActivities()
                await reloadMessages({ targetConversationId: targetConvId })
            }
            if (targetConvId === conversationId.value) {
                isLoading.value = false
                scrollToBottom()
                nextTick(() => inputBox.value?.focus())
            }
            emit('refresh-artifacts')
            emit('refresh-conversations')
        }
    } catch (e) {
        console.error('Submit question error:', e)
        // Only update UI if we're still on the same conversation
        const currentConvId = conversationId.value
        if (currentConvId) {
            clearActivities()
            // Only show error if still on the same conversation
            if (currentConvId === conversationId.value) {
                messages.value.push({
                    id: genMsgId(),
                    role: 'assistant',
                    text: `**${t('errors.error')}:** ${e.message}`
                })
                isLoading.value = false
                scrollToBottom()
                nextTick(() => inputBox.value?.focus())
            }
        }
    } finally {
        currentJobId.value = null
        isCancelling.value = false
    }
}

// OAuth
const startOAuth = () => {
    if (!pendingOAuth.value?.authUrl) return
    window.open(pendingOAuth.value.authUrl, 'oauth', 'width=500,height=600,popup=1')
}

const handleOAuthComplete = async (event) => {
    if (event.data?.type !== 'oauth_complete') return

    const jobId = pendingOAuth.value?.jobId
    // Capture conversation ID BEFORE any async operations to prevent mixing chats
    const targetConvId = conversationId.value
    pendingOAuth.value = null

    if (!jobId) return

    currentJobId.value = jobId

    try {
        const job = await pollJobUntilDone(jobId, targetConvId)

        if (job.status === 'waiting_for_input') {
            if (job._isCurrentConversation) {
                pendingQuestion.value = {
                    jobId: job.jobId,
                    question: job.question,
                    options: job.options
                }
                scrollToBottom()
            }
        } else if (job.status === 'oauth_pending') {
            if (job._isCurrentConversation) {
                pendingOAuth.value = {
                    jobId: job.jobId,
                    provider: job.provider,
                    authUrl: job.authUrl,
                    reason: job.reason
                }
                scrollToBottom()
            }
        } else if (job.status === 'cancelled') {
            clearStoredJobId(targetConvId)
            if (job._isCurrentConversation) {
                clearActivities()
                messages.value.push({
                    id: genMsgId(),
                    role: 'system',
                    text: job.result
                })
                isLoading.value = false
                scrollToBottom()
                nextTick(() => inputBox.value?.focus())
            }
            emit('refresh-artifacts')
            emit('refresh-conversations')
        } else {
            clearStoredJobId(targetConvId)
            if (job._isCurrentConversation) {
                // Preserve suggestions for post-response display before clearing
                preserveSuggestionsForPostResponse(targetConvId)
                clearActivities()
                await reloadMessages({ targetConversationId: targetConvId })
                isLoading.value = false
                scrollToBottom()
                nextTick(() => inputBox.value?.focus())
            }
            emit('refresh-artifacts')
            emit('refresh-conversations')
        }
    } catch (e) {
        console.error('OAuth complete error:', e)
        // Only update UI if we're still on the same conversation
        if (targetConvId === conversationId.value) {
            clearActivities()
            messages.value.push({
                id: genMsgId(),
                role: 'assistant',
                text: `**${t('errors.error')}:** ${e.message}`
            })
            isLoading.value = false
            scrollToBottom()
            nextTick(() => inputBox.value?.focus())
        }
    } finally {
        currentJobId.value = null
        isCancelling.value = false
    }
}

// File upload helpers
let fileIdCounter = 0
const hasUploadingFiles = computed(() => attachedFiles.value.some(f => f.uploading))


// Input suggestions visibility - only on empty chat
const showInputSuggestions = computed(() => {
    return messages.value.length === 0 && !isLoading.value
})

// Post-response suggestions visibility - only for current conversation
const showPostResponseSuggestions = computed(() => {
    return !isLoading.value &&
           postResponseSuggestions.value.length > 0 &&
           postResponseSuggestionsConversationId.value === conversationId.value
})

// Start a background chat (doesn't navigate user away)
const startBackgroundChat = async (prompt) => {
    try {
        // Send message without conversationId = creates new conversation
        const { job_id, conversation_id: newConvId } = await api.sendMessage(prompt, null)

        // Show toast confirmation
        toast.info(t('chat.automationStarted'))

        // Refresh sidebar to show new conversation
        emit('refresh-conversations')

        // Poll job in background (fire and forget)
        pollBackgroundJob(job_id, newConvId)
    } catch (e) {
        console.error('Failed to start background chat:', e)
        toast.error(t('errors.error'))
    }
}

// Poll a background job without blocking UI
const pollBackgroundJob = async (jobId, bgConversationId) => {
    const POLL_INTERVAL = 500
    const MAX_POLL_DURATION = 30 * 60 * 1000 // 30 minutes max
    const startTime = Date.now()

    while (true) {
        // Check timeout to prevent infinite polling
        if (Date.now() - startTime > MAX_POLL_DURATION) {
            console.warn('Background poll timed out after 30 minutes')
            break
        }

        try {
            const job = await api.pollJob(jobId)

            if (job.status === 'completed' || job.status === 'cancelled' || job.status === 'failed') {
                // Mark as unread so user knows it's done
                if (!unreadConversations.value.includes(bgConversationId)) {
                    unreadConversations.value.push(bgConversationId)
                }
                emit('refresh-conversations')
                playNotificationSound()
                break
            }

            // For waiting_for_input or oauth_pending, mark as unread too
            if (job.status === 'waiting_for_input' || job.status === 'oauth_pending') {
                if (!unreadConversations.value.includes(bgConversationId)) {
                    unreadConversations.value.push(bgConversationId)
                }
                emit('refresh-conversations')
                break
            }

            await new Promise(r => setTimeout(r, POLL_INTERVAL))
        } catch (e) {
            console.error('Background poll error:', e)
            break
        }
    }
}

// Handle suggestion selection (from empty state)
const handleSuggestionSelect = (suggestion) => {
    const prompt = suggestion.prompt || ''

    // If currently loading (user is waiting), start a new chat in background
    if (isLoading.value) {
        startBackgroundChat(prompt)
        return
    }

    // Otherwise, fill the input as usual
    inputText.value = prompt
    nextTick(() => {
        autoResize()
        inputBox.value?.focus()
    })
}

// Handle related question selection (Perplexity-style, during loading)
const handleRelatedQuestionSelect = async (question) => {
    try {
        // Find the last user message to fork from
        const lastUserMsg = messages.value.findLast(m => m.role === 'user')
        const lastUserMsgId = lastUserMsg?.dbId

        if (!conversationId.value || !lastUserMsgId) {
            // No conversation to fork from - start fresh
            startBackgroundChat(question)
            return
        }

        // 1. Fork conversation from last user message
        const { conversation_id: newConvId } = await api.forkConversation(
            conversationId.value,
            lastUserMsgId
        )

        // 2. Send the suggestion message to the forked conversation
        const { job_id } = await api.sendMessage(question, newConvId)

        // 3. Show toast notification
        toast.info(t('suggestions.startedInBackground'))

        // 4. Refresh sidebar to show new conversation
        emit('refresh-conversations')

        // 5. Poll forked job in background
        pollBackgroundJob(job_id, newConvId)

    } catch (e) {
        console.error('Failed to start related question:', e)
        toast.error(t('errors.error'))
    }
}

// Handle post-response suggestion selection (sends as user message in current chat)
const handlePostResponseSelect = (suggestion) => {
    clearPostResponseSuggestions()
    inputText.value = suggestion
    nextTick(() => {
        sendMessage()
    })
}

const addAndUploadFile = async (file) => {
    const fileId = ++fileIdCounter
    const abortController = new AbortController()
    const fileObj = {
        id: fileId,
        name: file.name,
        type: file.type,
        file: file,
        previewUrl: file.type.startsWith('image/') ? URL.createObjectURL(file) : null,
        uploading: true,
        uploadedPath: null,
        abortController
    }
    attachedFiles.value.push(fileObj)

    try {
        const result = await api.uploadArtifact(file, '', abortController.signal)
        // Find item in array to ensure reactivity
        const item = attachedFiles.value.find(f => f.id === fileId)
        if (item) {
            item.uploadedPath = result.path
            item.uploading = false
            item.abortController = null
        }
        emit('refresh-artifacts')
    } catch (e) {
        // Remove failed/aborted upload
        const idx = attachedFiles.value.findIndex(f => f.id === fileId)
        if (idx !== -1) {
            if (attachedFiles.value[idx].previewUrl) {
                URL.revokeObjectURL(attachedFiles.value[idx].previewUrl)
            }
            attachedFiles.value.splice(idx, 1)
        }
        // Don't show error for aborted uploads
        if (e.name !== 'AbortError') {
            alert(t('errors.uploadError') + ': ' + e.message)
        }
    }
}

// Drag & drop
const handleInputDrop = async (event) => {
    isDraggingOnInput.value = false
    const files = Array.from(event.dataTransfer?.files || [])
    if (!files.length) return

    for (const file of files) {
        addAndUploadFile(file)
    }

    nextTick(() => inputBox.value?.focus())
}

const handleFileInputChange = (event) => {
    const files = Array.from(event.target.files || [])
    if (!files.length) return

    for (const file of files) {
        addAndUploadFile(file)
    }

    event.target.value = ''
    nextTick(() => inputBox.value?.focus())
}

const handleInputDragLeave = (event) => {
    if (!event.currentTarget.contains(event.relatedTarget)) {
        isDraggingOnInput.value = false
    }
}

// Clipboard paste
const handlePaste = (event) => {
    const clipboardData = event.clipboardData
    if (!clipboardData) return

    const files = []

    // Method 1: Direct files (e.g., copied from file explorer)
    if (clipboardData.files && clipboardData.files.length > 0) {
        files.push(...clipboardData.files)
    }

    // Method 2: Items (e.g., screenshots, copied images)
    if (clipboardData.items) {
        for (const item of clipboardData.items) {
            if (item.kind === 'file') {
                const file = item.getAsFile()
                if (file && !files.some(f => f.name === file.name && f.size === file.size)) {
                    files.push(file)
                }
            }
        }
    }

    if (files.length === 0) return // No files, let default paste behavior continue

    event.preventDefault() // Prevent pasting file name as text

    for (const file of files) {
        addAndUploadFile(file)
    }
}

const removeAttachment = (index) => {
    const file = attachedFiles.value[index]
    if (file?.abortController) {
        file.abortController.abort()
    }
    removeAttachmentFromState(index)
}

// Fill prompt from demo
const fillPromptFromDemo = (prompt) => {
    // Don't replace if user has already typed something
    if (inputText.value.trim()) return

    inputText.value = prompt
    promptPending.value = true
    nextTick(() => {
        autoResize()
        inputBox.value?.focus()
        inputBox.value?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    })
}

// Handle OAuth completion from localStorage (for popup blocked scenarios)
const handleStorageEvent = (event) => {
    if (event.key !== 'oauth_complete') return

    try {
        const data = JSON.parse(event.newValue)
        if (data?.type === 'oauth_complete') {
            // Clear it immediately to prevent duplicate handling
            localStorage.removeItem('oauth_complete')
            // Trigger the same handler
            handleOAuthComplete({ data })
        }
    } catch (e) {
        console.error('Error parsing oauth_complete from localStorage:', e)
    }
}

// Check localStorage on mount for OAuth completion (user might have navigated here after OAuth)
const checkPendingOAuthInStorage = () => {
    try {
        const stored = localStorage.getItem('oauth_complete')
        if (stored) {
            const data = JSON.parse(stored)
            // Only process if it's recent (within last 30 seconds)
            if (data?.type === 'oauth_complete' && data.timestamp && (Date.now() - data.timestamp) < 30000) {
                localStorage.removeItem('oauth_complete')
                handleOAuthComplete({ data })
            } else {
                // Stale data, remove it
                localStorage.removeItem('oauth_complete')
            }
        }
    } catch (e) {
        console.error('Error checking pending OAuth in localStorage:', e)
        localStorage.removeItem('oauth_complete')
    }
}

// Lifecycle
onMounted(() => {
    window.addEventListener('message', handleOAuthComplete)
    window.addEventListener('storage', handleStorageEvent)
    // Check if OAuth completed while we were away
    checkPendingOAuthInStorage()
})

onUnmounted(() => {
    window.removeEventListener('message', handleOAuthComplete)
    window.removeEventListener('storage', handleStorageEvent)
})
</script>

<style scoped>
.send-pulse {
    animation: pulse-glow 1.5s ease-in-out infinite;
    box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.7);
}

@keyframes pulse-glow {
    0% {
        box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.7);
        transform: scale(1);
    }
    50% {
        box-shadow: 0 0 20px 8px rgba(59, 130, 246, 0.4);
        transform: scale(1.05);
    }
    100% {
        box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.7);
        transform: scale(1);
    }
}

/* Conversation loading dots */
.loading-dot {
    --loading-dot-1: var(--accent-glow, #3b82f6);
    --loading-dot-2: var(--accent-violet, #a78bfa);
    --loading-dot-3: var(--accent-pink, #f472b6);

    width: 12px;
    height: 12px;
    border-radius: 50%;
    animation: loading-bounce 1.4s ease-in-out infinite;
}

.loading-dot-1 {
    background: var(--loading-dot-1);
    animation-delay: 0s;
}

.loading-dot-2 {
    background: var(--loading-dot-2);
    animation-delay: 0.2s;
}

.loading-dot-3 {
    background: var(--loading-dot-3);
    animation-delay: 0.4s;
}

@keyframes loading-bounce {
    0%, 80%, 100% {
        transform: scale(0.6);
        opacity: 0.5;
    }
    40% {
        transform: scale(1);
        opacity: 1;
    }
}

</style>
