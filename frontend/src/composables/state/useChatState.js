import { ref } from 'vue'

// URL helpers
const getConversationFromUrl = () => {
    const match = window.location.pathname.match(/^\/c\/([a-f0-9-]+)$/i)
    return match ? match[1] : null
}

// Singleton state (shared across all components)
const messages = ref([])
const inputText = ref('')
const isLoading = ref(false)
const conversationId = ref(getConversationFromUrl() || null)
const conversations = ref([])
const archivedConversations = ref([])
const pendingQuestion = ref(null)
const pendingOAuth = ref(null) // { jobId, provider, authUrl, reason }
const attachedFiles = ref([]) // Array of {name, type, file, previewUrl}
const showConversationLoader = ref(false) // Delayed loader for conversation switching
const readAt = ref(null) // Timestamp when conversation was last read (for unread separator)

// Message ID generator
let msgCounter = 0
const genMsgId = () => `msg-${Date.now()}-${++msgCounter}`

// LocalStorage helpers for job state
const getStoredJobId = (convId) => localStorage.getItem(`activeJob_${convId}`)
const setStoredJobId = (convId, jobId) => localStorage.setItem(`activeJob_${convId}`, jobId)
const clearStoredJobId = (convId) => localStorage.removeItem(`activeJob_${convId}`)

// In-memory storage for input text per conversation (keeps input during session)
const inputTextByConversation = new Map()

// Save input for current conversation
const saveInputForConversation = (convId) => {
    if (convId && inputText.value.trim()) {
        inputTextByConversation.set(convId, inputText.value)
    } else if (convId) {
        // Clear stored input if empty
        inputTextByConversation.delete(convId)
    }
}

// Load input for a conversation (and restore to inputText ref)
const loadInputForConversation = (convId) => {
    if (convId && inputTextByConversation.has(convId)) {
        inputText.value = inputTextByConversation.get(convId)
    } else {
        inputText.value = ''
    }
}

export function useChatState() {
    // Clear all chat state for new chat
    const clearChatState = () => {
        messages.value = []
        pendingQuestion.value = null
        pendingOAuth.value = null
        isLoading.value = false
        readAt.value = null
    }

    // Update conversation ID
    const setConversationId = (convId) => {
        conversationId.value = convId
    }

    // Add message to current chat
    const addMessage = (message) => {
        messages.value.push({
            id: genMsgId(),
            ...message
        })
    }

    // Add file attachment with preview
    const addAttachment = (file) => {
        const fileObj = {
            name: file.name,
            type: file.type,
            file: file,
            previewUrl: file.type.startsWith('image/') ? URL.createObjectURL(file) : null
        }
        attachedFiles.value.push(fileObj)
    }

    // Remove file attachment
    const removeAttachment = (index) => {
        const file = attachedFiles.value[index]
        if (file.previewUrl) {
            URL.revokeObjectURL(file.previewUrl)
        }
        attachedFiles.value.splice(index, 1)
    }

    // Clear all attachments
    const clearAttachments = () => {
        attachedFiles.value.forEach(f => {
            if (f.previewUrl) URL.revokeObjectURL(f.previewUrl)
        })
        attachedFiles.value = []
    }

    // Reload messages from API (shared logic to avoid duplication)
    // api parameter should have getConversationMessages and markConversationRead methods
    // targetConversationId: if provided, only updates state if it matches current conversationId
    const reloadMessages = async (api, options = {}) => {
        const { updateReadAt = false, markAsRead = true, targetConversationId = null } = options

        // Use targetConversationId if provided, otherwise use current conversationId
        const convIdToLoad = targetConversationId || conversationId.value
        if (!convIdToLoad) return

        try {
            const data = await api.getConversationMessages(convIdToLoad)

            // IMPORTANT: Check if user switched conversations during the fetch
            // Only update state if we're still on the same conversation
            if (convIdToLoad !== conversationId.value) {
                console.log('Skipping message update - conversation changed during fetch')
                return
            }

            // API returns {messages: [...], read_at: "..."}
            const messageList = data.messages || data
            // Only update readAt if explicitly requested (e.g., on initial load)
            if (updateReadAt) {
                readAt.value = data.read_at || null
            }
            messages.value = messageList.map((m, idx) => ({
                id: `loaded-${convIdToLoad}-${idx}`,
                dbId: m.id,
                role: m.role,
                text: m.content,
                created_at: m.created_at,
                metadata: m.metadata || null
            }))
            // Mark as read since user is viewing the chat
            if (markAsRead) {
                api.markConversationRead(convIdToLoad).catch(e => console.warn('Failed to mark as read:', e))
            }
        } catch (e) {
            console.error('Failed to reload messages', e)
        }
    }

    return {
        // State
        messages,
        inputText,
        isLoading,
        conversationId,
        conversations,
        archivedConversations,
        pendingQuestion,
        pendingOAuth,
        attachedFiles,
        showConversationLoader,
        readAt,

        // Helpers
        genMsgId,
        getConversationFromUrl,
        getStoredJobId,
        setStoredJobId,
        clearStoredJobId,
        saveInputForConversation,
        loadInputForConversation,

        // Actions
        clearChatState,
        setConversationId,
        addMessage,
        addAttachment,
        removeAttachment,
        clearAttachments,
        reloadMessages
    }
}
