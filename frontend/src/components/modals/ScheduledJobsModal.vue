<template>
    <div
        class="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
        @click.self="$emit('close')"
    >
        <div class="glass-solid rounded-3xl w-full max-w-lg max-h-[80vh] flex flex-col animate-modal-enter relative overflow-hidden">
            <!-- Gradient top accent -->
            <div class="absolute top-0 left-8 right-8 h-px bg-gradient-to-r from-transparent via-cyan-500/50 to-transparent"></div>

            <!-- Modal Header -->
            <div class="flex items-center justify-between p-6 border-b border-white/5">
                <div class="flex items-center gap-3">
                    <div class="p-2 rounded-xl bg-gradient-to-br from-cyan-500/20 to-blue-500/20">
                        <Clock class="w-5 h-5 text-cyan-400" />
                    </div>
                    <h2 class="text-lg font-semibold text-[var(--text-primary)]">{{ $t('modals.scheduledJobs.title') }}</h2>
                </div>
                <button @click="$emit('close')" class="p-2 rounded-xl text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-surface)] transition-all">
                    <X class="w-5 h-5" />
                </button>
            </div>

            <!-- Modal Body -->
            <div class="flex-1 overflow-y-auto p-6 custom-scroll">
                <div v-if="jobs.length === 0" class="text-center py-12">
                    <div class="w-16 h-16 rounded-2xl bg-gradient-to-br from-cyan-500/10 to-blue-500/10 flex items-center justify-center mx-auto mb-4">
                        <Clock class="w-8 h-8 text-cyan-400/50" />
                    </div>
                    <p class="text-[var(--text-secondary)]">{{ $t('modals.scheduledJobs.noJobs') }}</p>
                    <p class="text-sm text-[var(--text-muted)] mt-1">{{ $t('modals.scheduledJobs.askAssistant') }}</p>
                </div>

                <div v-else class="space-y-3">
                    <div
                        v-for="job in jobs"
                        :key="job.id"
                        class="bg-white/5 border border-white/5 rounded-xl overflow-hidden hover:bg-white/[0.07] transition-colors"
                    >
                        <!-- Job Header (clickable to expand) -->
                        <div
                            class="p-4 cursor-pointer"
                            @click="toggleExpand(job.id)"
                        >
                            <div class="flex items-start justify-between gap-3">
                                <div class="flex-1 min-w-0">
                                    <div class="flex items-center gap-2">
                                        <ChevronDown
                                            class="w-4 h-4 text-[var(--text-muted)] transition-transform"
                                            :class="{ 'rotate-180': expandedJob === job.id }"
                                        />
                                        <h3 class="font-medium text-[var(--text-primary)] truncate">{{ job.name }}</h3>
                                    </div>
                                    <p class="text-sm text-[var(--text-secondary)] mt-0.5 ml-6">{{ job.schedule_description }}</p>
                                    <p class="text-xs text-[var(--text-muted)] mt-1 ml-6 truncate" :title="job.prompt">{{ job.prompt }}</p>
                                    <div class="flex items-center gap-3 mt-2 ml-6 text-xs text-[var(--text-muted)]">
                                        <span v-if="job.next_run_at">{{ $t('modals.scheduledJobs.next') }}: {{ formatDate(job.next_run_at) }}</span>
                                        <span v-if="job.run_count > 0">{{ $t('modals.scheduledJobs.runs') }}: {{ job.run_count }}</span>
                                    </div>
                                </div>
                                <div class="flex items-center gap-2 flex-shrink-0">
                                    <button
                                        @click.stop="toggleJob(job.id, !job.is_enabled)"
                                        :class="job.is_enabled ? 'text-emerald-400 hover:text-emerald-300' : 'text-[var(--text-muted)] hover:text-[var(--text-secondary)]'"
                                        :title="job.is_enabled ? $t('common.disable') : $t('common.enable')"
                                        class="transition-colors"
                                    >
                                        <ToggleRight v-if="job.is_enabled" class="w-6 h-6" />
                                        <ToggleLeft v-else class="w-6 h-6" />
                                    </button>
                                    <button
                                        @click.stop="deleteJob(job.id)"
                                        class="p-1.5 text-[var(--text-muted)] hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-all"
                                        :title="$t('common.delete')"
                                    >
                                        <Trash2 class="w-4 h-4" />
                                    </button>
                                </div>
                            </div>
                        </div>

                        <!-- Expanded Details -->
                        <div
                            v-if="expandedJob === job.id"
                            class="border-t border-[var(--border-subtle)] p-4 bg-[var(--bg-elevated)]"
                        >
                            <!-- Recent Runs / Conversations -->
                            <div v-if="jobDetails && jobDetails.conversations && jobDetails.conversations.length > 0">
                                <h4 class="text-sm font-medium text-[var(--text-primary)] mb-2">{{ $t('modals.scheduledJobs.recentRuns') }}</h4>
                                <div class="space-y-2">
                                    <div
                                        v-for="conv in jobDetails.conversations.slice(0, 5)"
                                        :key="conv.id"
                                        class="flex items-center gap-2 p-2 rounded-lg bg-[var(--bg-surface)] border border-[var(--border-subtle)] hover:bg-[var(--bg-overlay)] cursor-pointer transition-colors"
                                        @click="$emit('select-conversation', conv.id)"
                                    >
                                        <Clock class="w-4 h-4 text-cyan-500 flex-shrink-0" />
                                        <span class="text-sm text-[var(--text-secondary)] truncate flex-1">{{ conv.preview || $t('modals.scheduledJobs.noPreview') }}</span>
                                        <span class="text-xs text-[var(--text-muted)] flex-shrink-0">{{ formatDate(conv.created_at) }}</span>
                                    </div>
                                </div>
                            </div>
                            <div v-else class="text-sm text-[var(--text-muted)]">
                                {{ $t('modals.scheduledJobs.noRunsYet') }}
                            </div>

                            <!-- Actions -->
                            <div class="flex items-center gap-2 mt-4">
                                <button
                                    @click.stop="$emit('show-details', job.id)"
                                    class="px-3 py-1.5 text-sm bg-cyan-500 hover:bg-cyan-600 text-white rounded-lg transition-colors"
                                >
                                    {{ $t('modals.scheduledJobs.viewDetails') }}
                                </button>
                                <button
                                    @click.stop="triggerJob(job.id)"
                                    class="px-3 py-1.5 text-sm bg-emerald-500 hover:bg-emerald-600 text-white rounded-lg transition-colors"
                                    :disabled="triggering"
                                >
                                    {{ $t('modals.scheduledJobs.runNow') }}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { Clock, X, Trash2, ToggleLeft, ToggleRight, ChevronDown } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'

const emit = defineEmits(['close', 'show-details', 'select-conversation', 'refresh-conversations', 'new-conversation'])
const { t } = useI18n()

const jobs = ref([])
const expandedJob = ref(null)
const jobDetails = ref(null)
const triggering = ref(false)
let pollInterval = null

const fetchJobs = async () => {
    try {
        const res = await fetch('/scheduled-jobs')
        if (res.ok) {
            jobs.value = await res.json()
        }
    } catch (e) {
        console.error('Failed to fetch scheduled jobs', e)
    }
}

const fetchJobDetails = async (jobId) => {
    try {
        const res = await fetch(`/scheduled-jobs/${jobId}/details`)
        if (res.ok) {
            jobDetails.value = await res.json()
        }
    } catch (e) {
        console.error('Failed to fetch job details', e)
    }
}

const toggleExpand = async (jobId) => {
    if (expandedJob.value === jobId) {
        expandedJob.value = null
        jobDetails.value = null
    } else {
        expandedJob.value = jobId
        await fetchJobDetails(jobId)
    }
}

const toggleJob = async (id, enabled) => {
    try {
        await fetch(`/scheduled-jobs/${id}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ is_enabled: enabled })
        })
        await fetchJobs()
    } catch (e) {
        console.error('Failed to toggle scheduled job', e)
    }
}

const deleteJob = async (id) => {
    if (!confirm(t('confirmations.deleteJob'))) return
    try {
        await fetch(`/scheduled-jobs/${id}`, { method: 'DELETE' })
        if (expandedJob.value === id) {
            expandedJob.value = null
            jobDetails.value = null
        }
        await fetchJobs()
    } catch (e) {
        console.error('Failed to delete scheduled job', e)
    }
}

const triggerJob = async (id) => {
    triggering.value = true
    try {
        const res = await fetch(`/scheduled-jobs/${id}/trigger`, { method: 'POST' })
        if (res.ok) {
            const data = await res.json()
            if (data.conversation_id) {
                // Optimistic: emit new conversation to add it to sidebar immediately
                const job = jobs.value.find(j => j.id === id)
                emit('new-conversation', {
                    id: data.conversation_id,
                    preview: job?.name || t('modals.scheduledJobs.scheduledTask'),
                    created_at: new Date().toISOString(),
                    last_message_at: new Date().toISOString(),
                    has_active_job: true,
                    has_pending_question: false,
                    is_unread: false,
                    unread_count: 0,
                    is_scheduler_run: true
                })
                emit('select-conversation', data.conversation_id)
                emit('close')
                return
            }
        }
    } catch (e) {
        console.error('Failed to trigger scheduled job', e)
    } finally {
        triggering.value = false
    }
}

const formatDate = (isoString) => {
    if (!isoString) return ''
    const date = new Date(isoString)
    return date.toLocaleString(undefined, {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    })
}

onMounted(() => {
    fetchJobs()
    // Poll for conversation list updates while modal is open
    pollInterval = setInterval(() => {
        emit('refresh-conversations')
    }, 3000)
})

onUnmounted(() => {
    if (pollInterval) {
        clearInterval(pollInterval)
        pollInterval = null
    }
})
</script>
