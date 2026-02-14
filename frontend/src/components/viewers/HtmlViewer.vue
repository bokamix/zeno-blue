<template>
    <div class="html-viewer flex flex-col flex-1 min-h-0">
        <!-- View mode toggle -->
        <div class="flex items-center justify-end gap-2 mb-3 px-1">
            <button
                @click="viewMode = viewMode === 'preview' ? 'code' : 'preview'"
                class="px-3 py-1 text-xs rounded-lg transition-all bg-[var(--bg-surface)] text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-hover)]"
            >
                {{ viewMode === 'preview' ? t('viewer.showCode') : t('viewer.hideCode') }}
            </button>
        </div>

        <!-- Loading state -->
        <div v-if="loading" class="flex items-center justify-center h-64">
            <span class="text-[var(--text-muted)]">Loading...</span>
        </div>

        <!-- Content -->
        <div v-else class="flex flex-1 gap-2 min-h-0">
            <!-- Code panel -->
            <div
                v-if="viewMode === 'code'"
                class="flex-1 overflow-auto bg-[var(--bg-surface)] rounded-lg border border-[var(--border-subtle)]"
            >
                <pre class="text-sm p-4 overflow-x-auto h-full"><code
                    v-html="highlightedCode"
                    class="hljs"
                /></pre>
            </div>

            <!-- Preview panel -->
            <div
                v-if="viewMode === 'preview'"
                class="flex-1 overflow-hidden bg-white rounded-lg border border-[var(--border-subtle)]"
            >
                <iframe
                    :srcdoc="content"
                    sandbox="allow-scripts allow-same-origin"
                    class="w-full h-full border-0"
                    title="HTML Preview"
                />
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import hljs from 'highlight.js'

const { t } = useI18n()

const props = defineProps({
    url: { type: String, required: true }
})

const loading = ref(true)
const content = ref('')
const viewMode = ref('preview')

const highlightedCode = computed(() => {
    if (!content.value) return ''
    try {
        return hljs.highlight(content.value, { language: 'html' }).value
    } catch (e) {
        console.warn('Highlight failed:', e)
        return content.value
    }
})

onMounted(async () => {
    try {
        const res = await fetch(props.url)
        content.value = await res.text()
    } catch (e) {
        console.error('Failed to load HTML:', e)
        content.value = '<!-- Failed to load file -->'
    } finally {
        loading.value = false
    }
})
</script>

<style scoped>
.html-viewer iframe {
    background: white;
}
</style>
