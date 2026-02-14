<template>
    <div v-if="suggestions.length > 0" class="mt-4 pt-3 border-t border-[var(--border-subtle)]/30">
        <div class="flex flex-col gap-1">
            <button
                v-for="(suggestion, idx) in suggestions"
                :key="idx"
                @click="$emit('select', suggestion)"
                class="flex items-start gap-2.5 px-2 py-2
                       text-sm text-[var(--text-secondary)]
                       hover:text-[var(--text-primary)]
                       hover:bg-[var(--bg-surface)]
                       rounded-lg
                       transition-all duration-200
                       text-left"
            >
                <CornerDownRight class="w-4 h-4 text-[var(--text-muted)] flex-shrink-0 mt-0.5" />
                <span>{{ suggestion }}</span>
            </button>
        </div>
    </div>
</template>

<script setup>
import { CornerDownRight } from 'lucide-vue-next'

defineProps({
    suggestions: {
        type: Array,
        default: () => []
    }
})

defineEmits(['select'])
</script>
