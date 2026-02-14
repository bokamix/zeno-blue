<template>
    <div class="markdown-viewer">
        <div v-if="loading" class="flex items-center justify-center h-64">
            <span class="text-zinc-400">Loading...</span>
        </div>
        <div
            v-else
            v-html="renderedHtml"
            class="prose prose-invert max-w-none prose-headings:text-zinc-100 prose-p:text-zinc-300 prose-strong:text-zinc-200 prose-code:text-blue-300 prose-pre:bg-zinc-900"
        />
    </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { marked } from 'marked'
import { markedHighlight } from 'marked-highlight'
import hljs from 'highlight.js'
import 'highlight.js/styles/github-dark.css'

// Configure marked with syntax highlighting
marked.use(markedHighlight({
    langPrefix: 'hljs language-',
    highlight(code, lang) {
        if (lang && hljs.getLanguage(lang)) {
            return hljs.highlight(code, { language: lang }).value
        }
        return hljs.highlightAuto(code).value
    }
}))

const props = defineProps({
    url: { type: String, required: true }
})

const loading = ref(true)
const content = ref('')

const renderedHtml = computed(() => {
    if (!content.value) return ''
    return marked.parse(content.value)
})

onMounted(async () => {
    try {
        const res = await fetch(props.url)
        content.value = await res.text()
    } catch (e) {
        console.error('Failed to load markdown:', e)
        content.value = '> Failed to load file'
    } finally {
        loading.value = false
    }
})
</script>
