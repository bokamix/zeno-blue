<template>
    <div
        class="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
        @click.self="$emit('cancel')"
    >
        <div class="glass-solid rounded-2xl p-6 max-w-sm w-full animate-modal-enter">
            <div class="flex items-center gap-3 mb-4">
                <div class="p-2 rounded-xl bg-orange-500/20">
                    <RefreshCw class="w-5 h-5 text-orange-400" />
                </div>
                <h3 class="text-lg font-semibold text-[var(--text-primary)]">Restart Container?</h3>
            </div>
            <p class="text-sm text-zinc-400 mb-2">This will restart the agent container.</p>
            <p class="text-sm text-zinc-500 mb-6">If there are active jobs, they will be given up to 30 seconds to complete.</p>
            <div class="flex justify-end gap-3">
                <button
                    @click="$emit('cancel')"
                    class="px-4 py-2.5 text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-white/10 rounded-xl transition-all"
                >
                    Cancel
                </button>
                <button
                    @click="$emit('confirm')"
                    class="px-5 py-2.5 text-sm bg-gradient-to-r from-orange-600 to-orange-500 text-white rounded-xl
                           shadow-lg shadow-orange-500/25 hover:shadow-orange-500/40 hover:scale-105 transition-all font-medium"
                >
                    Restart
                </button>
            </div>
        </div>
    </div>
</template>

<script setup>
import { RefreshCw } from 'lucide-vue-next'

defineEmits(['cancel', 'confirm'])
</script>
