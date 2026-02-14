<template>
    <div class="text-viewer">
        <div v-if="loading" class="flex items-center justify-center h-64">
            <span class="text-[var(--text-muted)]">Loading...</span>
        </div>
        <div v-else class="relative">
            <div class="flex text-sm font-mono">
                <!-- Line numbers -->
                <div class="select-none pr-4 text-right text-[var(--text-muted)] border-r border-[var(--border-subtle)] mr-4">
                    <div v-for="n in lineCount" :key="n">{{ n }}</div>
                </div>
                <!-- Content -->
                <pre class="flex-1 text-[var(--text-secondary)] whitespace-pre-wrap break-words overflow-x-auto">{{ content }}</pre>
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'

const props = defineProps({
    url: { type: String, required: true }
})

const loading = ref(true)
const content = ref('')

const lineCount = computed(() => {
    if (!content.value) return 0
    return content.value.split('\n').length
})

onMounted(async () => {
    try {
        const res = await fetch(props.url)
        content.value = await res.text()
    } catch (e) {
        console.error('Failed to load text:', e)
        content.value = 'Failed to load file'
    } finally {
        loading.value = false
    }
})
</script>
