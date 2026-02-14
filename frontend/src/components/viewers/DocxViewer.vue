<template>
    <div class="docx-viewer">
        <div v-if="loading" class="flex items-center justify-center h-64">
            <span class="text-[var(--text-muted)]">Converting document...</span>
        </div>
        <div
            v-else-if="htmlContent"
            v-html="htmlContent"
            class="docx-content prose max-w-none"
        />
        <div v-else-if="error" class="text-red-400 p-4">
            {{ error }}
        </div>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import mammoth from 'mammoth'

const props = defineProps({
    url: { type: String, required: true }
})

const loading = ref(true)
const htmlContent = ref('')
const error = ref(null)

onMounted(async () => {
    try {
        const res = await fetch(props.url)
        const arrayBuffer = await res.arrayBuffer()
        const result = await mammoth.convertToHtml({ arrayBuffer })
        htmlContent.value = result.value

        if (result.messages?.length > 0) {
            console.warn('DOCX conversion warnings:', result.messages)
        }
    } catch (e) {
        console.error('Failed to load DOCX:', e)
        error.value = 'Failed to convert document: ' + e.message
    } finally {
        loading.value = false
    }
})
</script>

<style>
.docx-content {
    color: var(--text-secondary);
}
.docx-content h1,
.docx-content h2,
.docx-content h3,
.docx-content h4,
.docx-content h5,
.docx-content h6 {
    color: var(--text-primary);
}
.docx-content strong {
    color: var(--text-primary);
}
.docx-content a {
    color: var(--accent-primary);
}
</style>
