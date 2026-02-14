<template>
    <div v-show="visible" class="w-full mb-6">
        <!-- Main loading row -->
        <div class="flex items-center gap-3">
            <!-- Typing indicator -->
            <div class="flex items-center gap-1.5 px-4 py-2.5 rounded-xl bg-white/5">
                <span class="w-2 h-2 rounded-full bg-blue-400 animate-bounce" style="animation-delay: 0ms"></span>
                <span class="w-2 h-2 rounded-full bg-sky-400 animate-bounce" style="animation-delay: 150ms"></span>
                <span class="w-2 h-2 rounded-full bg-cyan-400 animate-bounce" style="animation-delay: 300ms"></span>
            </div>

            <!-- Simple status message (user-friendly) -->
            <span class="text-sm text-zinc-500">
                {{ simpleStatusMessage }}
            </span>

        </div>

        <!-- Hint that appears after delay -->
        <Transition name="fade-slide">
            <p v-if="showHint" class="mt-4 text-sm text-zinc-500 text-center max-w-md">
                {{ $t('loading.longThinkingHint') }}
                <button
                    @click="$emit('new-chat')"
                    class="text-blue-400 hover:text-blue-300 underline underline-offset-2 transition-colors"
                >
                    {{ $t('loading.createNewChat') }}
                </button>
            </p>
        </Transition>
    </div>
</template>

<script setup>
import { computed, ref, watch, onUnmounted } from 'vue'
// Icons removed - stop button moved to input area
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const props = defineProps({
    visible: {
        type: Boolean,
        default: false
    },
    currentActivity: {
        type: Object,
        default: null
    },
    activities: {
        type: Array,
        default: () => []
    },
})

const emit = defineEmits(['new-chat'])

// Hint timer state
const showHint = ref(false)
let hintTimer = null

const HINT_DELAY = 5000 // 5 seconds before showing hint

const startHintTimer = () => {
    stopHintTimer()
    showHint.value = false
    hintTimer = setTimeout(() => {
        showHint.value = true
    }, HINT_DELAY)
}

const stopHintTimer = () => {
    if (hintTimer) {
        clearTimeout(hintTimer)
        hintTimer = null
    }
    showHint.value = false
}

// Watch visibility to start/stop timer
watch(() => props.visible, (visible) => {
    if (visible) {
        startHintTimer()
    } else {
        stopHintTimer()
    }
}, { immediate: true })

onUnmounted(() => {
    stopHintTimer()
})

// Map activity to simple user-friendly message
const simpleStatusMessage = computed(() => {
    const activity = props.currentActivity
    if (!activity) return t('loading.statusWorking')

    const toolName = (activity.tool_name || '').toLowerCase()
    const activityType = (activity.type || '').toLowerCase()

    // Check tool name for specific actions
    if (toolName.includes('shell') || toolName.includes('bash') || toolName.includes('command')) {
        return t('loading.statusRunningCommand')
    }
    if (toolName.includes('file') || toolName.includes('write') || toolName.includes('create')) {
        return t('loading.statusCreatingFile')
    }
    if (toolName.includes('web') || toolName.includes('search') || toolName.includes('fetch')) {
        return t('loading.statusSearchingWeb')
    }

    // Check activity type
    if (activityType === 'llm_call' || activityType === 'thinking' || activityType.includes('think')) {
        return t('loading.statusThinking')
    }

    // Default
    return t('loading.statusWorking')
})
</script>

<style scoped>
/* Fade slide animation for suggestion button */
.fade-slide-enter-active {
    transition: all 0.4s ease-out;
}

.fade-slide-leave-active {
    transition: all 0.3s ease-in;
}

.fade-slide-enter-from {
    opacity: 0;
    transform: translateY(8px);
}

.fade-slide-leave-to {
    opacity: 0;
    transform: translateY(-8px);
}
</style>
