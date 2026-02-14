<template>
    <div
        class="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
        @click.self="$emit('cancel')"
    >
        <div class="glass-solid rounded-2xl p-6 max-w-sm w-full animate-modal-enter">
            <h3 class="text-lg font-semibold text-[var(--text-primary)] mb-2">{{ $t('modals.cancelConfirm.title') }}</h3>
            <p class="text-sm text-zinc-400 mb-6">{{ $t('modals.cancelConfirm.message') }}</p>
            <div class="flex justify-end gap-3">
                <button
                    @click="$emit('cancel')"
                    class="px-4 py-2.5 text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-white/10 rounded-xl transition-all"
                >
                    {{ $t('common.cancel') }}
                </button>
                <button
                    @click="$emit('confirm')"
                    class="px-5 py-2.5 text-sm bg-gradient-to-r from-red-600 to-red-500 text-white rounded-xl
                           shadow-lg shadow-red-500/25 hover:shadow-red-500/40 hover:scale-105 transition-all font-medium"
                >
                    {{ $t('modals.cancelConfirm.confirmButton') }}
                </button>
            </div>
        </div>
    </div>
</template>

<script setup>
defineEmits(['cancel', 'confirm'])
</script>
