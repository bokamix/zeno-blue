<template>
    <div class="pdf-viewer">
        <VuePdfEmbed
            v-if="pdfSource"
            :source="pdfSource"
            class="mx-auto"
        />
        <div v-else class="flex items-center justify-center h-64">
            <span class="text-[var(--text-muted)]">Loading PDF...</span>
        </div>
    </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import VuePdfEmbed from 'vue-pdf-embed'
// Note: vue-pdf-embed styles are handled via scoped CSS below

const props = defineProps({
    url: { type: String, required: true }
})

const pdfSource = ref(null)
let blobUrl = null

onMounted(async () => {
    try {
        const res = await fetch(props.url)
        const blob = await res.blob()
        blobUrl = URL.createObjectURL(blob)
        pdfSource.value = blobUrl
    } catch (e) {
        console.error('Failed to load PDF:', e)
    }
})

onUnmounted(() => {
    if (blobUrl) {
        URL.revokeObjectURL(blobUrl)
    }
})
</script>

<style scoped>
.pdf-viewer :deep(.vue-pdf-embed) {
    max-width: 100%;
}
.pdf-viewer :deep(canvas) {
    max-width: 100%;
    height: auto !important;
}
</style>
