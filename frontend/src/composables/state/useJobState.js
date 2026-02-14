import { ref } from 'vue'

// Singleton state (shared across all components)

// Current job state
const currentJobId = ref(null)
const isCancelling = ref(false)

// Activity tracking
const activities = ref([])
const lastActivityId = ref(null)
const currentActivity = ref(null)

// Related question suggestions (Perplexity-style)
const suggestions = ref([])

// Post-response suggestions (shown after bot finishes response)
const postResponseSuggestions = ref([])
const postResponseSuggestionsConversationId = ref(null)

// Thinking messages (temporary messages shown during agent work)
const thinkingMessages = ref([])

// Container restart state
const restartCooldown = ref(0)
const isRestarting = ref(false)
const restartError = ref(null)

// Cooldown interval reference
let cooldownInterval = null

export function useJobState() {
    // Clear all activities (and thinking messages and suggestions)
    const clearActivities = () => {
        activities.value = []
        lastActivityId.value = null
        currentActivity.value = null
        thinkingMessages.value = []
        suggestions.value = []
    }

    // Add new activities
    const addActivities = (newActivities, newLastActivityId) => {
        if (newActivities?.length > 0) {
            activities.value = [...activities.value, ...newActivities]
            lastActivityId.value = newLastActivityId
        }
    }

    // Clear thinking messages
    const clearThinkingMessages = () => {
        thinkingMessages.value = []
    }

    // Set thinking message (replaces previous - only show latest)
    const setThinkingMessage = (activity) => {
        thinkingMessages.value = [{
            id: `thinking-${activity.id}`,
            content: activity.detail || activity.message,
            timestamp: activity.timestamp
        }]
    }

    // Set suggestions (related questions)
    const setSuggestions = (newSuggestions) => {
        if (newSuggestions?.length > 0 && suggestions.value.length === 0) {
            // Only set once (don't overwrite)
            suggestions.value = newSuggestions
        }
    }

    // Clear suggestions
    const clearSuggestions = () => {
        suggestions.value = []
    }

    // Preserve suggestions for post-response display
    const preserveSuggestionsForPostResponse = (conversationId) => {
        if (suggestions.value.length > 0 && conversationId) {
            postResponseSuggestions.value = [...suggestions.value]
            postResponseSuggestionsConversationId.value = conversationId
        }
    }

    // Clear post-response suggestions (when user sends a message)
    const clearPostResponseSuggestions = () => {
        postResponseSuggestions.value = []
        postResponseSuggestionsConversationId.value = null
    }

    // Reset job state
    const resetJobState = () => {
        currentJobId.value = null
        isCancelling.value = false
        clearActivities()
        clearThinkingMessages()
    }

    // Start cooldown timer for restart
    const startCooldownTimer = () => {
        if (cooldownInterval) clearInterval(cooldownInterval)

        cooldownInterval = setInterval(() => {
            if (restartCooldown.value > 0) {
                restartCooldown.value--
            } else {
                clearInterval(cooldownInterval)
                cooldownInterval = null
            }
        }, 1000)
    }

    // Set restart cooldown
    const setRestartCooldown = (seconds) => {
        restartCooldown.value = seconds
        if (seconds > 0) {
            startCooldownTimer()
        }
    }

    // Cleanup cooldown interval
    const cleanupCooldown = () => {
        if (cooldownInterval) {
            clearInterval(cooldownInterval)
            cooldownInterval = null
        }
    }

    return {
        // State
        currentJobId,
        isCancelling,
        activities,
        lastActivityId,
        currentActivity,
        thinkingMessages,
        suggestions,
        postResponseSuggestions,
        postResponseSuggestionsConversationId,
        restartCooldown,
        isRestarting,
        restartError,

        // Actions
        clearActivities,
        addActivities,
        clearThinkingMessages,
        setThinkingMessage,
        setSuggestions,
        clearSuggestions,
        preserveSuggestionsForPostResponse,
        clearPostResponseSuggestions,
        resetJobState,
        setRestartCooldown,
        startCooldownTimer,
        cleanupCooldown
    }
}
