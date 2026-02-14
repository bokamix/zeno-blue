<template>
    <div v-if="hasContent || isLoading" class="mb-4">
        <!-- Thinking Section -->
        <div v-if="thinkingActivities.length > 0" class="mb-3">
            <p class="text-xs text-[var(--text-muted)] mb-1.5 font-medium">
                {{ $t('suggestions.thinking') }}
            </p>
            <TransitionGroup name="activity-fade" tag="div" class="space-y-1">
                <div
                    v-for="activity in thinkingActivities"
                    :key="activity.id"
                    class="flex items-start gap-2 text-sm"
                >
                    <span
                        class="mt-1.5 w-1.5 h-1.5 rounded-full shrink-0 transition-opacity duration-300"
                        :class="activity.isActive
                            ? 'bg-violet-400 animate-pulse'
                            : 'bg-[var(--text-muted)]'"
                    ></span>
                    <span
                        class="text-[var(--text-muted)] transition-opacity duration-300"
                        :class="{ 'opacity-50': !activity.isActive }"
                    >
                        {{ getActivityMessage(activity) }}
                    </span>
                </div>
            </TransitionGroup>
        </div>

        <!-- Searching Section (grouped search chips) -->
        <div v-if="searchQueries.length > 0" class="mb-3">
            <p class="text-xs text-[var(--text-muted)] mb-1.5 font-medium">
                {{ $t('suggestions.searching') }}
            </p>
            <div class="flex flex-wrap gap-1.5">
                <span
                    v-for="(query, idx) in searchQueries"
                    :key="idx"
                    class="inline-flex items-center gap-1.5 px-2.5 py-1
                           text-xs text-[var(--text-secondary)]
                           bg-[var(--bg-elevated)] rounded-md"
                >
                    <Search class="w-3 h-3 text-cyan-400/70" />
                    <span class="truncate max-w-[180px]">{{ query }}</span>
                </span>
            </div>
        </div>

        <!-- Delegates Section (cards with individual status) -->
        <div v-if="trackedDelegates.length > 0" class="mb-3">
            <!-- Header with agent count -->
            <div class="flex items-center gap-2 mb-2">
                <Users class="w-3.5 h-3.5 text-violet-400" />
                <span class="text-xs font-medium text-[var(--text-muted)]">
                    {{ $t('delegates.hired', { count: trackedDelegates.length }) }}
                </span>
                <span
                    v-if="runningDelegatesCount > 0"
                    class="text-xs text-violet-400"
                >
                    ({{ $t('delegates.working', { count: runningDelegatesCount }) }})
                </span>
            </div>

            <!-- Delegate cards -->
            <TransitionGroup name="delegate-card" tag="div" class="space-y-2">
                <div
                    v-for="delegate in trackedDelegates"
                    :key="delegate.id"
                    class="delegate-card"
                    :class="getDelegateCardClass(delegate)"
                >
                    <div class="flex items-start gap-2.5">
                        <!-- Status icon -->
                        <div class="mt-0.5 shrink-0">
                            <Loader2
                                v-if="delegate.status === 'running'"
                                class="w-4 h-4 text-violet-400 animate-spin"
                            />
                            <CheckCircle2
                                v-else-if="delegate.status === 'completed'"
                                class="w-4 h-4 text-emerald-400"
                            />
                            <XCircle
                                v-else
                                class="w-4 h-4 text-red-400"
                            />
                        </div>

                        <!-- Content -->
                        <div class="flex-1 min-w-0">
                            <p class="text-sm text-[var(--text-secondary)] leading-snug">
                                {{ delegate.task }}
                            </p>

                            <!-- Output preview (completed) -->
                            <p
                                v-if="delegate.status === 'completed' && delegate.output"
                                class="mt-1.5 text-xs text-[var(--text-muted)] line-clamp-2"
                            >
                                {{ delegate.output }}
                            </p>

                            <!-- Error message -->
                            <p
                                v-if="delegate.status === 'error' && delegate.error"
                                class="mt-1.5 text-xs text-red-400/80"
                            >
                                {{ delegate.error }}
                            </p>
                        </div>
                    </div>
                </div>
            </TransitionGroup>
        </div>

        <!-- Current status with bouncing dots -->
        <div v-if="isLoading" class="flex items-center gap-2 mt-3">
            <div class="flex items-center gap-0.5">
                <span class="w-1 h-1 rounded-full bg-indigo-400 animate-bounce" style="animation-delay: 0ms"></span>
                <span class="w-1 h-1 rounded-full bg-violet-400 animate-bounce" style="animation-delay: 150ms"></span>
                <span class="w-1 h-1 rounded-full bg-cyan-400 animate-bounce" style="animation-delay: 300ms"></span>
            </div>
            <span class="text-xs text-[var(--text-muted)]">{{ currentStatusText }}</span>
        </div>

        <!-- Related Questions - inline style -->
        <RelatedQuestions
            v-if="isLoading && suggestions.length > 0"
            :suggestions="suggestions"
            @select="$emit('suggestion-select', $event)"
        />
    </div>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Search, Zap, Users, Loader2, CheckCircle2, XCircle } from 'lucide-vue-next'
import RelatedQuestions from './RelatedQuestions.vue'

const { t } = useI18n()

const emit = defineEmits(['suggestion-select'])

const props = defineProps({
    activities: {
        type: Array,
        default: () => []
    },
    isLoading: {
        type: Boolean,
        default: false
    },
    currentActivity: {
        type: Object,
        default: null
    },
    maxVisible: {
        type: Number,
        default: 6
    },
    suggestions: {
        type: Array,
        default: () => []
    }
})

// Check if we have any content to show
const hasContent = computed(() => {
    return thinkingActivities.value.length > 0 ||
           searchQueries.value.length > 0 ||
           trackedDelegates.value.length > 0
})

// Extract thinking/progress activities (not search-related)
const thinkingActivities = computed(() => {
    const relevant = props.activities.filter(a => {
        const type = (a.type || '').toLowerCase()
        const toolName = (a.tool_name || '').toLowerCase()

        // Include thinking, planning, routing, progress steps
        if (type === 'thinking_stream' || type === 'planning' || type === 'routing' || type === 'progress_step') {
            return true
        }

        // Include explore subagent activities
        if (type.startsWith('explore_')) {
            return true
        }

        // Include tool calls that aren't web_search or delegate
        if (type === 'tool_call') {
            return !toolName.includes('web_search') && !toolName.includes('delegate')
        }

        // Exclude delegate_start (shown in delegateTasks section)
        if (type === 'delegate_start') {
            return false
        }

        return false
    })

    // Take last N activities
    const recent = relevant.slice(-props.maxVisible)

    // Mark last 2 as active for visual progression
    const activeCount = props.isLoading ? 2 : 0
    return recent.map((activity, idx) => ({
        ...activity,
        isActive: props.isLoading && idx >= recent.length - activeCount
    }))
})

// Extract search queries as simple strings
const searchQueries = computed(() => {
    const searches = props.activities.filter(a => {
        const type = (a.type || '').toLowerCase()
        const toolName = (a.tool_name || '').toLowerCase()
        return type === 'tool_call' && toolName.includes('web_search')
    })

    // Extract query text from each search activity
    return searches.map(a => {
        const message = a.message || ''
        // Try to extract query from message
        const queryMatch = message.match(/query['":\s]+["']?([^"'\n]+)["']?/i) ||
                          message.match(/searching[:\s]+["']?([^"'\n]+)["']?/i)
        if (queryMatch) return queryMatch[1].trim()

        // Fallback: use the message itself if it looks like a query
        if (message.length < 60 && !message.includes(':')) {
            return message.trim()
        }

        return t('activity.searchingWeb')
    }).filter((q, idx, arr) => arr.indexOf(q) === idx) // Remove duplicates
})

// Tracked delegates using tool_call/tool_result (delegate_start/end not saved by backend)
const trackedDelegates = computed(() => {
    const delegates = []
    const runningDelegates = []

    for (const activity of props.activities) {
        const type = (activity.type || '').toLowerCase()
        const toolName = (activity.tool_name || '').toLowerCase()

        // Start: tool_call with delegate_task
        if (type === 'tool_call' && toolName === 'delegate_task') {
            // Extract task from message like "delegate_task({'task': '...', 'context': '...'})"
            const message = activity.message || ''
            let task = 'Sub-agent task'

            // Try to parse task from the message
            const taskMatch = message.match(/['"]task['"]\s*:\s*['"]([^'"]+)['"]/)
            if (taskMatch) {
                task = taskMatch[1]
                // Truncate long tasks
                if (task.length > 80) {
                    task = task.substring(0, 77) + '...'
                }
            }

            const delegate = {
                id: activity.id,
                task,
                status: 'running',
                output: null,
                error: null
            }
            delegates.push(delegate)
            runningDelegates.push(delegate)
        }
        // End: tool_result with delegate_task
        else if (type === 'tool_result' && toolName === 'delegate_task' && runningDelegates.length > 0) {
            const delegate = runningDelegates.shift()
            const message = activity.message || ''

            // Check for error
            if (activity.is_error) {
                delegate.status = 'error'
                delegate.error = message.substring(0, 100)
            } else {
                delegate.status = 'completed'
                // Try to extract output preview from JSON result
                try {
                    const result = JSON.parse(message)
                    if (result.output) {
                        delegate.output = result.output.substring(0, 100)
                        if (result.output.length > 100) {
                            delegate.output += '...'
                        }
                    }
                } catch {
                    // Not JSON, use raw message
                    delegate.output = message.substring(0, 100)
                }
            }
        }
    }

    return delegates
})

const runningDelegatesCount = computed(() =>
    trackedDelegates.value.filter(d => d.status === 'running').length
)

const getDelegateCardClass = (delegate) => ({
    'delegate-card--running': delegate.status === 'running',
    'delegate-card--completed': delegate.status === 'completed',
    'delegate-card--error': delegate.status === 'error'
})

// Current status text based on last activity
const currentStatusText = computed(() => {
    const activity = props.currentActivity
    if (!activity) return t('loading.statusWorking')

    const toolName = (activity.tool_name || '').toLowerCase()
    const activityType = (activity.type || '').toLowerCase()

    if (toolName.includes('shell')) return t('loading.statusRunningCommand')
    if (toolName.includes('write') || toolName.includes('edit')) return t('loading.statusCreatingFile')
    if (toolName.includes('web') || toolName.includes('search')) return t('loading.statusSearchingWeb')
    if (activityType === 'llm_call' || activityType === 'thinking') return t('loading.statusThinking')

    return t('loading.statusWorking')
})

// Get user-friendly message for activity
const getActivityMessage = (activity) => {
    const toolName = (activity.tool_name || '').toLowerCase()
    const type = (activity.type || '').toLowerCase()
    const message = activity.message || ''

    const extractFilename = (msg) => {
        const match = msg.match(/["']?([\/\w\-\.]+\.\w+)["']?/) ||
                      msg.match(/path['":\s]+([\/\w\-\.]+)/) ||
                      msg.match(/\/workspace\/([\/\w\-\.]+)/)
        return match ? match[1].split('/').pop() : null
    }

    const extractCommand = (msg) => {
        const match = msg.match(/command['":\s]+["']?(\w+)/) ||
                      msg.match(/^(\w+)\s/)
        return match ? match[1] : null
    }

    if (toolName.includes('shell')) {
        const cmd = extractCommand(message)
        return cmd ? t('activity.runningCommand', { cmd }) : t('activity.executingCommand')
    }
    if (toolName.includes('write_file')) {
        const file = extractFilename(message)
        return file ? t('activity.creatingFile', { file }) : t('activity.writingFile')
    }
    if (toolName.includes('edit_file')) {
        const file = extractFilename(message)
        return file ? t('activity.editingFile', { file }) : t('activity.editingFile', { file: 'file' })
    }
    if (toolName.includes('read_file')) {
        const file = extractFilename(message)
        return file ? t('activity.readingFile', { file }) : t('activity.readingFile', { file: 'file' })
    }
    if (toolName.includes('list_dir')) return t('activity.listingDirectory')
    if (toolName.includes('search_in_files')) return t('activity.searchingFiles')
    if (toolName.includes('web_fetch')) return t('activity.fetchingWeb')
    if (toolName.includes('search_knowledge')) return t('activity.searchingKnowledge')
    if (toolName.includes('ask_user')) return t('activity.askingUser')
    if (toolName.includes('delegate')) return t('activity.delegatingTask')
    if (toolName.includes('explore')) return t('activity.exploringCode')

    if (type === 'thinking_stream') return activity.message || t('activity.thinking')
    if (type === 'planning') return t('activity.planning')
    if (type === 'routing') return t('activity.analyzing')
    if (type === 'progress_step') return activity.message || t('activity.working')
    if (type === 'explore_start') return activity.message || t('activity.exploringCode')
    if (type === 'explore_step') return activity.message || t('activity.exploringCode')
    if (type === 'explore_end') return activity.message || t('activity.exploringCode')

    return message || t('activity.working')
}
</script>

<style scoped>
.activity-fade-enter-active {
    transition: all 0.4s ease-out;
}

.activity-fade-leave-active {
    transition: all 0.2s ease-in;
}

.activity-fade-enter-from {
    opacity: 0;
    transform: translateY(-8px);
}

.activity-fade-leave-to {
    opacity: 0;
}

.activity-fade-move {
    transition: transform 0.3s ease;
}

/* Delegate Cards */
.delegate-card {
    @apply px-3 py-2.5 rounded-lg border transition-all duration-300;
    background: var(--bg-elevated);
    border-color: var(--border-subtle);
}

.delegate-card--running {
    @apply border-violet-500/30;
    animation: delegate-pulse 2s ease-in-out infinite;
}

.delegate-card--completed {
    @apply border-emerald-500/20 opacity-75;
}

.delegate-card--error {
    @apply border-red-500/20 opacity-75;
}

@keyframes delegate-pulse {
    0%, 100% { box-shadow: 0 0 0 0 rgba(139, 92, 246, 0); }
    50% { box-shadow: 0 0 8px 2px rgba(139, 92, 246, 0.15); }
}

/* Line clamp */
.line-clamp-2 {
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
}

/* Card transitions */
.delegate-card-enter-active {
    transition: all 0.3s ease-out;
}
.delegate-card-leave-active {
    transition: all 0.2s ease-in;
}
.delegate-card-enter-from {
    opacity: 0;
    transform: translateY(-10px) scale(0.95);
}
.delegate-card-leave-to {
    opacity: 0;
    transform: scale(0.95);
}
.delegate-card-move {
    transition: transform 0.3s ease;
}
</style>
