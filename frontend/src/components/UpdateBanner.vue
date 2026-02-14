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
</template>

<script setup>
import { RefreshCw } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { useUpdateStatus } from '../composables/useUpdateStatus'

const { t } = useI18n()
const { updatePending, activeJobs } = useUpdateStatus()
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
</style>
