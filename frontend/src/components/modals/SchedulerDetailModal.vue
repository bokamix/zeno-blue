<template>
    <div
        class="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
        @click.self="$emit('close')"
    >
        <div class="glass-solid rounded-3xl w-full max-w-2xl max-h-[85vh] flex flex-col animate-modal-enter relative overflow-hidden">
            <!-- Gradient top accent -->
            <div class="absolute top-0 left-8 right-8 h-px bg-gradient-to-r from-transparent via-cyan-500/50 to-transparent"></div>

            <!-- Modal Header -->
            <div class="flex items-center justify-between p-6 border-b border-[var(--border-subtle)]">
                <div class="flex items-center gap-3">
                    <div class="p-2 rounded-xl bg-gradient-to-br from-cyan-500/20 to-blue-500/20">
                        <Clock class="w-5 h-5 text-cyan-400" />
                    </div>
                    <div>
                        <h2 class="text-lg font-semibold text-[var(--text-primary)]">{{ job?.name || $t('modals.schedulerDetail.title') }}</h2>
                        <p v-if="job" class="text-sm text-[var(--text-secondary)]">{{ job.schedule_description }}</p>
                    </div>
                </div>
                <button @click="$emit('close')" class="p-2 rounded-xl text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-surface)] transition-all">
                    <X class="w-5 h-5" />
                </button>
            </div>

            <!-- Loading State -->
            <div v-if="loading" class="flex-1 flex items-center justify-center">
                <div class="animate-spin w-8 h-8 border-2 border-cyan-500 border-t-transparent rounded-full"></div>
            </div>

            <!-- Modal Body -->
            <div v-else-if="job" class="flex-1 overflow-y-auto p-6 custom-scroll space-y-6">
                <!-- Task Prompt -->
                <div>
                    <h3 class="text-sm font-medium text-[var(--text-primary)] mb-2">{{ $t('modals.schedulerDetail.whatItDoes') }}</h3>
                    <p v-if="!showEditPrompt" class="text-sm text-[var(--text-secondary)] bg-[var(--bg-elevated)] border border-[var(--border-subtle)] rounded-lg p-3 whitespace-pre-wrap">{{ job.prompt }}</p>
                    <button
                        v-if="!showEditPrompt"
                        @click="showEditPrompt = true; editedPrompt = job.prompt"
                        class="mt-2 text-sm text-cyan-600 hover:text-cyan-700 font-medium transition-colors"
                    >
                        {{ $t('modals.schedulerDetail.editPrompt') }}
                    </button>

                    <!-- Edit Prompt Form -->
                    <div v-if="showEditPrompt" class="mt-2 space-y-3">
                        <textarea
                            v-model="editedPrompt"
                            rows="6"
                            class="w-full bg-[var(--bg-surface)] border border-[var(--border-subtle)] rounded-lg px-3 py-2 text-sm text-[var(--text-primary)] focus:outline-none focus:border-cyan-500/50 resize-y"
                            :placeholder="$t('modals.schedulerDetail.promptPlaceholder')"
                        ></textarea>
                        <div class="flex gap-2">
                            <button
                                @click="showEditPrompt = false"
                                class="px-4 py-2 text-sm text-[var(--text-primary)] hover:bg-[var(--bg-overlay)] rounded-lg transition-colors"
                            >
                                {{ $t('common.cancel') }}
                            </button>
                            <button
                                @click="updatePrompt"
                                :disabled="savingPrompt || !editedPrompt.trim()"
                                class="px-4 py-2 bg-cyan-500 hover:bg-cyan-600 text-white rounded-lg text-sm transition-colors disabled:opacity-50"
                            >
                                {{ savingPrompt ? $t('common.saving') : $t('common.save') }}
                            </button>
                        </div>
                    </div>
                </div>

                <!-- Schedule Info -->
                <div>
                    <h3 class="text-sm font-medium text-[var(--text-primary)] mb-2">{{ $t('modals.schedulerDetail.schedule') }}</h3>
                    <div class="flex items-center gap-4 text-sm">
                        <div class="bg-[var(--bg-elevated)] border border-[var(--border-subtle)] rounded-lg p-3 flex-1">
                            <div class="text-[var(--text-muted)] text-xs mb-1">{{ $t('modals.schedulerDetail.runsAt') }}</div>
                            <span class="text-[var(--text-primary)]">{{ cronToHumanReadable(job.cron_expression) }}</span>
                        </div>
                        <div class="bg-[var(--bg-elevated)] border border-[var(--border-subtle)] rounded-lg p-3 flex-1">
                            <div class="text-[var(--text-muted)] text-xs mb-1">{{ $t('modals.schedulerDetail.nextRun') }}</div>
                            <span class="text-[var(--text-primary)]">{{ formatDate(job.next_run_at) || '-' }}</span>
                        </div>
                    </div>
                    <button
                        @click="showEditSchedule = !showEditSchedule"
                        class="mt-2 text-sm text-cyan-600 hover:text-cyan-700 font-medium transition-colors"
                    >
                        {{ showEditSchedule ? $t('common.cancel') : $t('modals.schedulerDetail.editSchedule') }}
                    </button>

                    <!-- Edit Schedule Form -->
                    <div v-if="showEditSchedule" class="mt-3 p-3 bg-[var(--bg-elevated)] border border-[var(--border-subtle)] rounded-lg space-y-3">
                        <!-- Frequency -->
                        <div>
                            <label class="text-xs text-[var(--text-secondary)] font-medium block mb-1">{{ $t('modals.schedulerDetail.frequency') }}</label>
                            <select
                                v-model="scheduleFrequency"
                                class="w-full bg-[var(--bg-surface)] border border-[var(--border-subtle)] rounded-lg px-3 py-2 text-sm text-[var(--text-primary)] focus:outline-none focus:border-cyan-500/50"
                            >
                                <option value="everyMinutes">{{ $t('modals.schedulerDetail.everyMinutes') }}</option>
                                <option value="daily">{{ $t('modals.schedulerDetail.daily') }}</option>
                                <option value="weekly">{{ $t('modals.schedulerDetail.weekly') }}</option>
                                <option value="monthly">{{ $t('modals.schedulerDetail.monthly') }}</option>
                                <option value="customDays">{{ $t('modals.schedulerDetail.customDays') }}</option>
                            </select>
                        </div>

                        <!-- Interval (for everyMinutes) -->
                        <div v-if="scheduleFrequency === 'everyMinutes'">
                            <label class="text-xs text-[var(--text-secondary)] font-medium block mb-1">{{ $t('modals.schedulerDetail.interval') }}</label>
                            <select
                                v-model="scheduleInterval"
                                class="w-full bg-[var(--bg-surface)] border border-[var(--border-subtle)] rounded-lg px-3 py-2 text-sm text-[var(--text-primary)] focus:outline-none focus:border-cyan-500/50"
                            >
                                <option v-for="m in [1, 2, 3, 5, 10, 15, 30]" :key="m" :value="m">{{ $t('modals.schedulerDetail.everyXMinutes', { minutes: m }) }}</option>
                            </select>
                        </div>

                        <!-- Day of week (for weekly) -->
                        <div v-if="scheduleFrequency === 'weekly'">
                            <label class="text-xs text-[var(--text-secondary)] font-medium block mb-1">{{ $t('modals.schedulerDetail.dayOfWeek') }}</label>
                            <select
                                v-model="scheduleDayOfWeek"
                                class="w-full bg-[var(--bg-surface)] border border-[var(--border-subtle)] rounded-lg px-3 py-2 text-sm text-[var(--text-primary)] focus:outline-none focus:border-cyan-500/50"
                            >
                                <option value="1">{{ $t('days.monday') }}</option>
                                <option value="2">{{ $t('days.tuesday') }}</option>
                                <option value="3">{{ $t('days.wednesday') }}</option>
                                <option value="4">{{ $t('days.thursday') }}</option>
                                <option value="5">{{ $t('days.friday') }}</option>
                                <option value="6">{{ $t('days.saturday') }}</option>
                                <option value="0">{{ $t('days.sunday') }}</option>
                            </select>
                        </div>

                        <!-- Day of month (for monthly) -->
                        <div v-if="scheduleFrequency === 'monthly'">
                            <label class="text-xs text-[var(--text-secondary)] font-medium block mb-1">{{ $t('modals.schedulerDetail.dayOfMonth') }}</label>
                            <select
                                v-model="scheduleDayOfMonth"
                                class="w-full bg-[var(--bg-surface)] border border-[var(--border-subtle)] rounded-lg px-3 py-2 text-sm text-[var(--text-primary)] focus:outline-none focus:border-cyan-500/50"
                            >
                                <option v-for="d in 28" :key="d" :value="d">{{ d }}</option>
                            </select>
                        </div>

                        <!-- Custom days (for customDays) -->
                        <div v-if="scheduleFrequency === 'customDays'">
                            <label class="text-xs text-[var(--text-secondary)] font-medium block mb-1">{{ $t('modals.schedulerDetail.selectDays') }}</label>
                            <div class="flex flex-wrap gap-2">
                                <label
                                    v-for="day in weekDays"
                                    :key="day.value"
                                    class="flex items-center gap-1.5 px-3 py-1.5 rounded-lg cursor-pointer transition-colors"
                                    :class="selectedDays.includes(day.value)
                                        ? 'bg-cyan-500 text-white border border-cyan-500'
                                        : 'bg-[var(--bg-surface)] text-[var(--text-secondary)] border border-[var(--border-subtle)] hover:bg-[var(--bg-overlay)]'"
                                >
                                    <input
                                        type="checkbox"
                                        v-model="selectedDays"
                                        :value="day.value"
                                        class="sr-only"
                                    />
                                    <span class="text-sm">{{ $t(`days.${day.key}`) }}</span>
                                </label>
                            </div>
                        </div>

                        <!-- Time (hidden for everyMinutes) -->
                        <div v-if="scheduleFrequency !== 'everyMinutes'">
                            <label class="text-xs text-[var(--text-secondary)] font-medium block mb-1">{{ $t('modals.schedulerDetail.time') }}</label>
                            <div class="flex items-center gap-2">
                                <select
                                    v-model="scheduleHour"
                                    class="bg-[var(--bg-surface)] border border-[var(--border-subtle)] rounded-lg px-3 py-2 text-sm text-[var(--text-primary)] focus:outline-none focus:border-cyan-500/50"
                                >
                                    <option v-for="h in 24" :key="h-1" :value="String(h-1).padStart(2, '0')">{{ String(h-1).padStart(2, '0') }}</option>
                                </select>
                                <span class="text-[var(--text-secondary)]">:</span>
                                <select
                                    v-model="scheduleMinute"
                                    class="bg-[var(--bg-surface)] border border-[var(--border-subtle)] rounded-lg px-3 py-2 text-sm text-[var(--text-primary)] focus:outline-none focus:border-cyan-500/50"
                                >
                                    <option v-for="m in 60" :key="m-1" :value="String(m-1).padStart(2, '0')">{{ String(m-1).padStart(2, '0') }}</option>
                                </select>
                            </div>
                        </div>

                        <!-- Actions -->
                        <div class="flex gap-2 pt-2">
                            <button
                                @click="showEditSchedule = false"
                                class="px-4 py-2 text-sm text-[var(--text-primary)] hover:bg-[var(--bg-overlay)] rounded-lg transition-colors"
                            >
                                {{ $t('common.cancel') }}
                            </button>
                            <button
                                @click="updateSchedule"
                                :disabled="saving"
                                class="px-4 py-2 bg-cyan-500 hover:bg-cyan-600 text-white rounded-lg text-sm transition-colors disabled:opacity-50"
                            >
                                {{ saving ? $t('common.saving') : $t('common.save') }}
                            </button>
                        </div>
                    </div>
                </div>

                <!-- Context (if any) -->
                <div v-if="job.context">
                    <h3 class="text-sm font-medium text-[var(--text-primary)] mb-2">{{ $t('modals.schedulerDetail.context') }}</h3>
                    <div class="bg-[var(--bg-elevated)] border border-[var(--border-subtle)] rounded-lg p-3 space-y-2">
                        <div v-if="job.context.steps && job.context.steps.length">
                            <div class="text-[var(--text-muted)] text-xs mb-1">{{ $t('modals.schedulerDetail.steps') }}</div>
                            <ul class="list-disc list-inside text-sm text-[var(--text-secondary)]">
                                <li v-for="(step, i) in job.context.steps" :key="i">{{ step }}</li>
                            </ul>
                        </div>
                        <div v-if="job.context.variables && Object.keys(job.context.variables).length">
                            <div class="text-[var(--text-muted)] text-xs mb-1">{{ $t('modals.schedulerDetail.variables') }}</div>
                            <div class="text-sm text-[var(--text-secondary)]">
                                <div v-for="(value, key) in job.context.variables" :key="key">
                                    <span class="text-cyan-400">{{ key }}</span>: {{ value }}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Files (if any) -->
                <div v-if="job.files && job.files.length">
                    <h3 class="text-sm font-medium text-[var(--text-primary)] mb-2">{{ $t('modals.schedulerDetail.files') }}</h3>
                    <div class="bg-[var(--bg-elevated)] border border-[var(--border-subtle)] rounded-lg p-3">
                        <div class="text-[var(--text-muted)] text-xs mb-2">{{ job.files_dir }}</div>
                        <div class="flex flex-wrap gap-2">
                            <span
                                v-for="file in job.files"
                                :key="file"
                                class="px-2 py-1 bg-[var(--bg-surface)] rounded text-sm text-[var(--text-secondary)]"
                            >
                                {{ file }}
                            </span>
                        </div>
                    </div>
                </div>

                <!-- All Runs (Conversations) -->
                <div>
                    <h3 class="text-sm font-medium text-[var(--text-primary)] mb-2">{{ $t('modals.schedulerDetail.allRuns') }} ({{ job.conversations?.length || 0 }})</h3>
                    <div v-if="job.conversations && job.conversations.length" class="space-y-2">
                        <div
                            v-for="conv in job.conversations"
                            :key="conv.id"
                            class="flex items-center gap-3 p-3 bg-[var(--bg-surface)] border border-[var(--border-subtle)] rounded-lg hover:bg-[var(--bg-overlay)] cursor-pointer transition-colors"
                            @click="$emit('select-conversation', conv.id)"
                        >
                            <Clock class="w-4 h-4 text-cyan-400 flex-shrink-0" />
                            <div class="flex-1 min-w-0">
                                <p class="text-sm text-[var(--text-primary)] truncate">{{ conv.preview || $t('modals.schedulerDetail.noPreview') }}</p>
                                <p class="text-xs text-[var(--text-secondary)] font-medium">{{ formatDate(conv.created_at) }}</p>
                            </div>
                            <ChevronRight class="w-4 h-4 text-[var(--text-muted)]" />
                        </div>
                    </div>
                    <div v-else class="text-sm text-[var(--text-muted)] bg-[var(--bg-elevated)] border border-[var(--border-subtle)] rounded-lg p-3">
                        {{ $t('modals.schedulerDetail.noRunsYet') }}
                    </div>
                </div>

                <!-- Stats -->
                <div class="flex items-center gap-4 text-sm text-[var(--text-muted)]">
                    <span>{{ $t('modals.schedulerDetail.totalRuns') }}: {{ job.run_count || 0 }}</span>
                    <span v-if="job.last_run_at">{{ $t('modals.schedulerDetail.lastRun') }}: {{ formatDate(job.last_run_at) }}</span>
                    <span>{{ $t('modals.schedulerDetail.created') }}: {{ formatDate(job.created_at) }}</span>
                </div>
            </div>

            <!-- Footer Actions -->
            <div v-if="job" class="flex items-center justify-between p-6 border-t border-[var(--border-subtle)]">
                <button
                    @click="deleteScheduler"
                    class="px-4 py-2 text-sm text-red-400 hover:text-red-300 hover:bg-red-500/10 rounded-lg transition-colors"
                >
                    {{ $t('modals.schedulerDetail.deleteScheduler') }}
                </button>
                <div class="flex items-center gap-3">
                    <button
                        @click="triggerNow"
                        :disabled="triggering"
                        class="px-4 py-2 text-sm bg-emerald-500 hover:bg-emerald-600 text-white rounded-lg transition-colors disabled:opacity-50"
                    >
                        {{ triggering ? $t('common.loading') : $t('modals.schedulerDetail.runNow') }}
                    </button>
                    <button
                        @click="$emit('close')"
                        class="px-4 py-2 text-sm bg-white/10 hover:bg-white/20 text-[var(--text-primary)] rounded-lg transition-colors"
                    >
                        {{ $t('common.close') }}
                    </button>
                </div>
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { Clock, X, ChevronRight } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'

const props = defineProps({
    schedulerId: {
        type: String,
        required: true
    }
})

const emit = defineEmits(['close', 'select-conversation', 'deleted'])
const { t, locale } = useI18n()

const job = ref(null)
const loading = ref(true)
const saving = ref(false)
const triggering = ref(false)
const showEditSchedule = ref(false)
const showEditPrompt = ref(false)
const editedPrompt = ref('')
const savingPrompt = ref(false)

// Schedule builder form values
const scheduleFrequency = ref('daily')
const scheduleDayOfWeek = ref('1')
const scheduleDayOfMonth = ref(1)
const scheduleHour = ref('09')
const scheduleMinute = ref('00')
const selectedDays = ref([])
const scheduleInterval = ref(5)

// Weekdays for customDays checkboxes
const weekDays = [
    { key: 'monday', value: '1' },
    { key: 'tuesday', value: '2' },
    { key: 'wednesday', value: '3' },
    { key: 'thursday', value: '4' },
    { key: 'friday', value: '5' },
    { key: 'saturday', value: '6' },
    { key: 'sunday', value: '0' }
]

// Parse existing cron expression to form values
const parseCronToForm = (cron) => {
    if (!cron) return
    const parts = cron.split(' ')
    if (parts.length < 5) return

    const [minute, hour, dayOfMonth, , dayOfWeek] = parts

    // Check for everyMinutes pattern: */X * * * *
    if (minute.startsWith('*/') && hour === '*' && dayOfMonth === '*' && dayOfWeek === '*') {
        scheduleFrequency.value = 'everyMinutes'
        scheduleInterval.value = parseInt(minute.substring(2), 10) || 5
        return
    }

    scheduleMinute.value = minute.padStart(2, '0')
    scheduleHour.value = hour.padStart(2, '0')

    if (dayOfWeek !== '*' && dayOfMonth === '*') {
        // Check if multiple days (customDays) or single day (weekly)
        if (dayOfWeek.includes(',')) {
            scheduleFrequency.value = 'customDays'
            selectedDays.value = dayOfWeek.split(',')
        } else {
            scheduleFrequency.value = 'weekly'
            scheduleDayOfWeek.value = dayOfWeek
        }
    } else if (dayOfMonth !== '*') {
        scheduleFrequency.value = 'monthly'
        scheduleDayOfMonth.value = parseInt(dayOfMonth, 10)
    } else {
        scheduleFrequency.value = 'daily'
    }
}

// Build cron expression from form values
const buildCronFromForm = () => {
    // Handle everyMinutes pattern
    if (scheduleFrequency.value === 'everyMinutes') {
        return `*/${scheduleInterval.value} * * * *`
    }

    const m = parseInt(scheduleMinute.value, 10)
    const h = parseInt(scheduleHour.value, 10)

    if (scheduleFrequency.value === 'daily') {
        return `${m} ${h} * * *`
    } else if (scheduleFrequency.value === 'weekly') {
        return `${m} ${h} * * ${scheduleDayOfWeek.value}`
    } else if (scheduleFrequency.value === 'customDays') {
        const days = selectedDays.value.sort((a, b) => parseInt(a) - parseInt(b)).join(',')
        return `${m} ${h} * * ${days || '*'}`
    } else {
        return `${m} ${h} ${scheduleDayOfMonth.value} * *`
    }
}

// Convert cron expression to human-readable text
const cronToHumanReadable = (cron) => {
    if (!cron) return ''
    const parts = cron.split(' ')
    if (parts.length < 5) return cron

    const [minute, hour, dayOfMonth, , dayOfWeek] = parts

    // Check for everyMinutes pattern: */X * * * *
    if (minute.startsWith('*/') && hour === '*' && dayOfMonth === '*' && dayOfWeek === '*') {
        const interval = parseInt(minute.substring(2), 10)
        return t('modals.schedulerDetail.everyXMinutes', { minutes: interval })
    }

    const time = `${hour.padStart(2, '0')}:${minute.padStart(2, '0')}`

    // Map day numbers to translation keys
    const dayKeyMap = {
        '0': 'sunday',
        '1': 'monday',
        '2': 'tuesday',
        '3': 'wednesday',
        '4': 'thursday',
        '5': 'friday',
        '6': 'saturday'
    }

    // Daily: 0 10 * * *
    if (dayOfWeek === '*' && dayOfMonth === '*') {
        return t('modals.schedulerDetail.everyDay', { time })
    }

    // Monthly: 0 10 15 * *
    if (dayOfMonth !== '*') {
        return t('modals.schedulerDetail.everyMonthDay', { day: dayOfMonth, time })
    }

    // Weekly or custom days: 0 10 * * 1 or 0 10 * * 1,3,5
    if (dayOfWeek !== '*') {
        const days = dayOfWeek.split(',')
        if (days.length === 1) {
            // Single day
            const dayKey = dayKeyMap[days[0]]
            return t('modals.schedulerDetail.everyWeekday', {
                day: t(`days.${dayKey}`),
                time
            })
        } else {
            // Multiple days
            const dayNames = days.map(d => t(`days.${dayKeyMap[d]}`))
            const lastDay = dayNames.pop()
            const daysText = dayNames.length > 0
                ? `${dayNames.join(', ')} ${t('common.and')} ${lastDay}`
                : lastDay
            return t('modals.schedulerDetail.everyWeekdays', { days: daysText, time })
        }
    }

    return cron
}

const fetchDetails = async () => {
    loading.value = true
    try {
        const res = await fetch(`/scheduled-jobs/${props.schedulerId}/details`)
        if (res.ok) {
            job.value = await res.json()
            parseCronToForm(job.value.cron_expression)
        }
    } catch (e) {
        console.error('Failed to fetch scheduler details', e)
    } finally {
        loading.value = false
    }
}

const updateSchedule = async () => {
    saving.value = true
    try {
        const cronExpression = buildCronFromForm()
        const res = await fetch(`/scheduled-jobs/${props.schedulerId}/schedule`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ cron_expression: cronExpression })
        })
        if (res.ok) {
            await fetchDetails()
            showEditSchedule.value = false
        }
    } catch (e) {
        console.error('Failed to update schedule', e)
    } finally {
        saving.value = false
    }
}

const updatePrompt = async () => {
    if (!editedPrompt.value.trim()) return
    savingPrompt.value = true
    try {
        const res = await fetch(`/scheduled-jobs/${props.schedulerId}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt: editedPrompt.value.trim() })
        })
        if (res.ok) {
            await fetchDetails()
            showEditPrompt.value = false
        }
    } catch (e) {
        console.error('Failed to update prompt', e)
    } finally {
        savingPrompt.value = false
    }
}

const triggerNow = async () => {
    triggering.value = true
    try {
        const res = await fetch(`/scheduled-jobs/${props.schedulerId}/trigger`, { method: 'POST' })
        if (res.ok) {
            const data = await res.json()
            if (data.conversation_id) {
                // Redirect to new conversation
                emit('select-conversation', data.conversation_id)
                emit('close')
                return
            }
        }
    } catch (e) {
        console.error('Failed to trigger scheduler', e)
    } finally {
        triggering.value = false
    }
}

const deleteScheduler = async () => {
    if (!confirm(t('confirmations.deleteJob'))) return
    try {
        await fetch(`/scheduled-jobs/${props.schedulerId}`, { method: 'DELETE' })
        emit('deleted')
        emit('close')
    } catch (e) {
        console.error('Failed to delete scheduler', e)
    }
}

const formatDate = (isoString) => {
    if (!isoString) return ''
    const date = new Date(isoString)
    return date.toLocaleString(locale.value, {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    })
}

watch(() => props.schedulerId, () => {
    fetchDetails()
})

onMounted(() => {
    fetchDetails()
})
</script>
