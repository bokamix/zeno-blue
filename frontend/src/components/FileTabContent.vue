<template>
    <div class="file-tab-content h-full flex flex-col bg-[var(--bg-base)]">
        <!-- File Header Bar -->
        <div class="flex items-center justify-between px-4 py-2 border-b border-[var(--border-subtle)] bg-[var(--bg-surface)]/30 shrink-0">
            <div class="flex items-center gap-2 min-w-0">
                <component :is="fileIcon" class="w-4 h-4 text-[var(--text-muted)] flex-shrink-0" />
                <span class="text-sm text-[var(--text-primary)] truncate">{{ fileName }}</span>
                <span class="text-xs text-[var(--text-muted)] flex-shrink-0">{{ fileType }}</span>
            </div>
            <a
                :href="fileUrl"
                download
                class="text-xs text-[var(--text-muted)] hover:text-[var(--text-primary)] flex items-center gap-1 px-2 py-1 rounded hover:bg-[var(--bg-surface)] transition-colors"
            >
                <Download class="w-3.5 h-3.5" />
                Download
            </a>
        </div>

        <!-- File Content -->
        <div class="flex-1 overflow-auto p-4 flex flex-col">
            <div class="flex-1 flex flex-col">
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
                            @saved="$emit('saved')"
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
                            @saved="$emit('saved')"
                        />

                        <!-- Unknown/other files (read-only) -->
                        <TextViewer v-else :url="fileUrl" />
                    </template>

                    <template #fallback>
                        <div class="flex items-center justify-center h-64">
                            <div class="text-center">
                                <div class="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-3"></div>
                                <span class="text-[var(--text-muted)]">Loading viewer...</span>
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
    Download,
    FileText,
    FileSpreadsheet,
    FileImage,
    FileVideo,
    FileCode,
    File as FileIcon
} from 'lucide-vue-next'

// Lazy load heavy viewers
const PdfViewer = defineAsyncComponent(() => import('./viewers/PdfViewer.vue'))
const DocxViewer = defineAsyncComponent(() => import('./viewers/DocxViewer.vue'))
const ExcelViewer = defineAsyncComponent(() => import('./viewers/ExcelViewer.vue'))
const NotionEditor = defineAsyncComponent(() => import('./viewers/NotionEditor.vue'))

// Light viewers
import ImageViewer from './viewers/ImageViewer.vue'
import VideoViewer from './viewers/VideoViewer.vue'
import CodeViewer from './viewers/CodeViewer.vue'
import HtmlViewer from './viewers/HtmlViewer.vue'
import TextViewer from './viewers/TextViewer.vue'

const props = defineProps({
    filePath: { type: String, required: true }
})

defineEmits(['saved'])

// File info
const fileName = computed(() => props.filePath.split('/').pop())
const extension = computed(() => {
    const parts = fileName.value.split('.')
    return parts.length > 1 ? parts.pop().toLowerCase() : ''
})

// Build URL
const fileUrl = computed(() => `/artifacts/${props.filePath}`)

// Determine viewer type based on extension
const viewerType = computed(() => {
    const ext = extension.value

    if (ext === 'pdf') return 'pdf'
    if (ext === 'docx') return 'docx'
    if (['xlsx', 'xls', 'csv'].includes(ext)) return 'excel'
    if (['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'bmp', 'ico'].includes(ext)) return 'image'
    if (['mp4', 'webm', 'ogg', 'mov', 'avi', 'mkv', 'm4v'].includes(ext)) return 'video'
    if (['html', 'htm'].includes(ext)) return 'html'
    if (ext === 'md') return 'markdown'
    if (ext === 'txt') return 'text'
    if ([
        'js', 'ts', 'jsx', 'tsx', 'vue', 'svelte',
        'py', 'rb', 'go', 'rs', 'java', 'kt', 'swift', 'c', 'cpp', 'h', 'hpp', 'cs',
        'php', 'css', 'scss', 'less', 'json', 'xml', 'yaml', 'yml',
        'sql', 'sh', 'bash', 'zsh', 'dockerfile'
    ].includes(ext)) return 'code'

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
