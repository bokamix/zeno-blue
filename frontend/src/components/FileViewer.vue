<template>
    <div class="file-viewer fixed inset-0 bg-black/90 z-50 flex flex-col">
        <!-- Header -->
        <div class="flex items-center justify-between px-6 py-4 border-b border-zinc-700 bg-zinc-900/80 backdrop-blur">
            <div class="flex items-center gap-3 min-w-0">
                <component :is="fileIcon" class="w-5 h-5 text-zinc-400 flex-shrink-0" />
                <span class="text-zinc-100 font-medium truncate">{{ fileName }}</span>
                <span class="text-xs text-zinc-500 flex-shrink-0">{{ fileType }}</span>
            </div>
            <div class="flex items-center gap-2">
                <a
                    :href="fileUrl"
                    download
                    class="px-3 py-1.5 text-sm text-zinc-300 hover:text-white bg-zinc-800 hover:bg-zinc-700 rounded-lg transition-colors flex items-center gap-2"
                >
                    <Download class="w-4 h-4" />
                    Download
                </a>
                <button
                    @click="$emit('close')"
                    class="p-2 text-zinc-400 hover:text-white hover:bg-zinc-800 rounded-lg transition-colors"
                >
                    <X class="w-5 h-5" />
                </button>
            </div>
        </div>

        <!-- Content -->
        <div class="flex-1 overflow-auto p-6 flex flex-col">
            <div class="max-w-5xl mx-auto flex-1 flex flex-col" :class="{ 'max-w-none w-full': viewerType === 'html' }">
                <!-- Loading state for async components -->
                <Suspense>
                    <template #default>
                        <!-- PDF -->
                        <PdfViewer v-if="viewerType === 'pdf'" :url="fileUrl" />

                        <!-- DOCX -->
                        <DocxViewer v-else-if="viewerType === 'docx'" :url="fileUrl" />

                        <!-- Excel/CSV -->
                        <ExcelViewer v-else-if="viewerType === 'excel'" :url="fileUrl" />

                        <!-- Images -->
                        <ImageViewer v-else-if="viewerType === 'image'" :url="fileUrl" :filename="fileName" />

                        <!-- Videos -->
                        <VideoViewer v-else-if="viewerType === 'video'" :url="fileUrl" :filename="fileName" />

                        <!-- Markdown (editable) -->
                        <NotionEditor
                            v-else-if="viewerType === 'markdown'"
                            :url="fileUrl"
                            :file-path="filePath"
                            :is-markdown="true"
                            @close="$emit('close')"
                            @saved="handleSaved"
                        />

                        <!-- HTML (split view with preview) -->
                        <HtmlViewer v-else-if="viewerType === 'html'" :url="fileUrl" />

                        <!-- Code -->
                        <CodeViewer v-else-if="viewerType === 'code'" :url="fileUrl" :extension="extension" />

                        <!-- Plain text .txt (editable) -->
                        <NotionEditor
                            v-else-if="viewerType === 'text'"
                            :url="fileUrl"
                            :file-path="filePath"
                            :is-markdown="false"
                            @close="$emit('close')"
                            @saved="handleSaved"
                        />

                        <!-- Unknown/other files (read-only) -->
                        <TextViewer v-else :url="fileUrl" />
                    </template>

                    <template #fallback>
                        <div class="flex items-center justify-center h-64">
                            <div class="text-center">
                                <div class="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
                                <span class="text-zinc-400">Loading viewer...</span>
                            </div>
                        </div>
                    </template>
                </Suspense>
            </div>
        </div>
    </div>
</template>

<script setup>
import { computed, defineAsyncComponent } from 'vue'
import {
    X,
    Download,
    FileText,
    FileSpreadsheet,
    FileImage,
    FileVideo,
    FileCode,
    File as FileIcon
} from 'lucide-vue-next'

// Lazy load heavy viewers - they'll only load when needed
const PdfViewer = defineAsyncComponent(() => import('./viewers/PdfViewer.vue'))
const DocxViewer = defineAsyncComponent(() => import('./viewers/DocxViewer.vue'))
const ExcelViewer = defineAsyncComponent(() => import('./viewers/ExcelViewer.vue'))

// Light viewers - can be imported directly (small, already bundled deps)
import ImageViewer from './viewers/ImageViewer.vue'
import VideoViewer from './viewers/VideoViewer.vue'
import CodeViewer from './viewers/CodeViewer.vue'
import HtmlViewer from './viewers/HtmlViewer.vue'
import MarkdownViewer from './viewers/MarkdownViewer.vue'
import TextViewer from './viewers/TextViewer.vue'

// Notion-like editor for editable files
const NotionEditor = defineAsyncComponent(() => import('./viewers/NotionEditor.vue'))

const props = defineProps({
    filePath: { type: String, required: true }
})

const emit = defineEmits(['close', 'saved'])

// Handle file saved event
function handleSaved() {
    emit('saved')
}

// File info
const fileName = computed(() => props.filePath.split('/').pop())
const extension = computed(() => {
    const parts = fileName.value.split('.')
    return parts.length > 1 ? parts.pop().toLowerCase() : ''
})

// Build URL - artifacts are served from /artifacts/{path}
const fileUrl = computed(() => `/artifacts/${props.filePath}`)

// Determine viewer type based on extension
const viewerType = computed(() => {
    const ext = extension.value

    // PDF
    if (ext === 'pdf') return 'pdf'

    // Word documents
    if (ext === 'docx') return 'docx'

    // Spreadsheets
    if (['xlsx', 'xls', 'csv'].includes(ext)) return 'excel'

    // Images
    if (['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'bmp', 'ico'].includes(ext)) return 'image'

    // Videos
    if (['mp4', 'webm', 'ogg', 'mov', 'avi', 'mkv', 'm4v'].includes(ext)) return 'video'

    // HTML (split view with preview)
    if (['html', 'htm'].includes(ext)) return 'html'

    // Markdown (editable)
    if (ext === 'md') return 'markdown'

    // Plain text (editable)
    if (ext === 'txt') return 'text'

    // Code files (read-only with syntax highlighting)
    if ([
        'js', 'ts', 'jsx', 'tsx', 'vue', 'svelte',
        'py', 'rb', 'go', 'rs', 'java', 'kt', 'swift', 'c', 'cpp', 'h', 'hpp', 'cs',
        'php', 'css', 'scss', 'less', 'json', 'xml', 'yaml', 'yml',
        'sql', 'sh', 'bash', 'zsh', 'dockerfile'
    ].includes(ext)) return 'code'

    // Default to unknown (read-only text view)
    return 'unknown'
})

// File type label
const fileType = computed(() => {
    const types = {
        pdf: 'PDF Document',
        docx: 'Word Document',
        excel: 'Spreadsheet',
        image: 'Image',
        video: 'Video',
        html: 'HTML Page',
        markdown: 'Markdown',
        code: 'Code',
        text: 'Text',
        unknown: 'File'
    }
    return types[viewerType.value] || 'File'
})

// Icon based on type
const fileIcon = computed(() => {
    const icons = {
        pdf: FileText,
        docx: FileText,
        excel: FileSpreadsheet,
        image: FileImage,
        video: FileVideo,
        html: FileCode,
        markdown: FileText,
        code: FileCode,
        text: FileText,
        unknown: FileIcon
    }
    return icons[viewerType.value] || FileIcon
})
</script>

<style scoped>
.file-viewer {
    animation: fadeIn 0.15s ease-out;
}

@keyframes fadeIn {
    from {
        opacity: 0;
    }
    to {
        opacity: 1;
    }
}
</style>
