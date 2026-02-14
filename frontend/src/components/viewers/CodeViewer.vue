<template>
    <div class="code-viewer">
        <div v-if="loading" class="flex items-center justify-center h-64">
            <span class="text-[var(--text-muted)]">Loading...</span>
        </div>
        <div v-else class="relative">
            <pre class="text-sm bg-[var(--bg-surface)] rounded-lg p-4 overflow-x-auto"><code
                v-html="highlightedCode"
                class="hljs"
            /></pre>
        </div>
    </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import hljs from 'highlight.js'

const props = defineProps({
    url: { type: String, required: true },
    extension: { type: String, default: '' }
})

const loading = ref(true)
const content = ref('')

// Map extensions to highlight.js language names
const languageMap = {
    js: 'javascript',
    ts: 'typescript',
    py: 'python',
    rb: 'ruby',
    go: 'go',
    rs: 'rust',
    java: 'java',
    kt: 'kotlin',
    swift: 'swift',
    c: 'c',
    cpp: 'cpp',
    h: 'c',
    hpp: 'cpp',
    cs: 'csharp',
    php: 'php',
    html: 'html',
    css: 'css',
    scss: 'scss',
    less: 'less',
    json: 'json',
    xml: 'xml',
    yaml: 'yaml',
    yml: 'yaml',
    md: 'markdown',
    sql: 'sql',
    sh: 'bash',
    bash: 'bash',
    zsh: 'bash',
    dockerfile: 'dockerfile',
    vue: 'html',
    jsx: 'javascript',
    tsx: 'typescript',
    svelte: 'html'
}

const language = computed(() => {
    const ext = props.extension.toLowerCase()
    return languageMap[ext] || 'plaintext'
})

const highlightedCode = computed(() => {
    if (!content.value) return ''

    try {
        if (hljs.getLanguage(language.value)) {
            return hljs.highlight(content.value, { language: language.value }).value
        }
    } catch (e) {
        console.warn('Highlight failed:', e)
    }

    return hljs.highlightAuto(content.value).value
})

onMounted(async () => {
    try {
        const res = await fetch(props.url)
        content.value = await res.text()
    } catch (e) {
        console.error('Failed to load code:', e)
        content.value = '// Failed to load file'
    } finally {
        loading.value = false
    }
})
</script>
