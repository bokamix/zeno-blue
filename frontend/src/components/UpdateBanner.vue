<template>
    <Transition name="banner">
        <div
            v-if="updatePending"
            class="flex items-center justify-center gap-3 px-4 py-2 text-sm font-medium bg-amber-500 text-amber-950 flex-shrink-0"
        >
            <RefreshCw class="w-4 h-4 animate-spin" />
            <span v-if="activeJobs > 0">
                {{ t('update.pending_with_jobs', { jobs: activeJobs }) }}
            </span>
            <span v-else>
                {{ t('update.in_progress') }}
            </span>
        </div>
    </Transition>

    <Transition name="toast">
        <div
            v-if="canUpdate && !updatePending && !dismissed"
            class="fixed bottom-6 left-1/2 -translate-x-1/2 z-50 flex items-center gap-3 px-5 py-3 rounded-xl border border-white/10 bg-white/5 backdrop-blur-xl shadow-2xl shadow-black/20 text-sm text-white/80"
        >
            <ArrowUpCircle class="w-4 h-4 text-blue-400 flex-shrink-0" />
            <span>{{ t('update.available') }}</span>
            <button
                @click="handleUpdate"
                class="ml-2 px-3 py-1 rounded-lg bg-blue-500/20 hover:bg-blue-500/30 text-blue-300 hover:text-blue-200 text-xs font-medium transition-colors"
            >
                {{ t('update.update_now') }}
            </button>
            <button
                @click="dismissed = true"
                class="p-1 rounded-lg hover:bg-white/10 text-white/40 hover:text-white/70 transition-colors"
            >
                <X class="w-3.5 h-3.5" />
            </button>
        </div>
    </Transition>
</template>

<script setup>
import { ref } from 'vue'
import { RefreshCw, ArrowUpCircle, X } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { useUpdateStatus } from '../composables/useUpdateStatus'

const { t } = useI18n()
const { updatePending, activeJobs, canUpdate, triggerUpdate } = useUpdateStatus()
const dismissed = ref(false)

async function handleUpdate() {
    dismissed.value = true
    await triggerUpdate()
}
</script>

<style scoped>
.banner-enter-active {
    transition: all 0.3s ease-out;
}

.banner-leave-active {
    transition: all 0.2s ease-in;
}

.banner-enter-from,
.banner-leave-to {
    opacity: 0;
    margin-top: -40px;
}

.toast-enter-active {
    transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}

.toast-leave-active {
    transition: all 0.2s ease-in;
}

.toast-enter-from {
    opacity: 0;
    transform: translateX(-50%) translateY(16px);
}

.toast-leave-to {
    opacity: 0;
    transform: translateX(-50%) translateY(8px);
}
</style>
