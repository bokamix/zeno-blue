<template>
    <div v-if="tabs.length > 1" class="hidden md:flex items-center gap-1 h-12 px-4 overflow-x-auto hide-scrollbar">
        <div
            v-for="tab in tabs"
            :key="tab.id"
            @click="handleTabClick(tab)"
            class="relative flex items-center gap-2 px-3 py-2 rounded-xl text-sm whitespace-nowrap cursor-pointer transition-all"
            :class="[
                tab.id === activeTabId
                    ? 'bg-blue-500/10 text-[var(--text-primary)] border border-blue-500/20'
                    : 'text-[var(--text-muted)] hover:text-[var(--text-secondary)] hover:bg-[var(--bg-surface)]/50'
            ]"
        >
            <!-- Left indicator for active tab -->
            <div
                v-if="tab.id === activeTabId"
                class="absolute left-0 top-1.5 bottom-1.5 w-[3px] rounded-r-full bg-gradient-to-b from-blue-500 to-sky-500"
            ></div>
            <component :is="getTabIcon(tab)" class="w-4 h-4 flex-shrink-0" :class="tab.id === activeTabId ? 'text-blue-400' : ''" />
            <span class="max-w-[120px] truncate">{{ tab.title }}</span>
            <button
                v-if="tab.closable"
                @click.stop="$emit('close', tab.id)"
                class="p-0.5 rounded hover:bg-[var(--bg-overlay)] text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors ml-1"
            >
                <X class="w-3 h-3" />
            </button>
        </div>
    </div>
</template>

<script setup>
import {
    X,
    MessageSquare,
    FileText,
    FileSpreadsheet,
    FileImage,
    FileCode,
    File as FileIcon
} from 'lucide-vue-next'

defineProps({
    tabs: {
        type: Array,
        required: true
    },
    activeTabId: {
        type: String,
        required: true
    }
})

const emit = defineEmits(['select', 'close', 'reveal'])

const handleTabClick = (tab) => {
    emit('select', tab.id)
    if (tab.type === 'file') {
        emit('reveal', tab.path)
    }
}

// Get icon based on tab type and file extension
const getTabIcon = (tab) => {
    if (tab.type === 'chat') return MessageSquare

    // For file tabs, determine icon by extension
    const ext = tab.path?.split('.').pop()?.toLowerCase() || ''

    // PDF
    if (ext === 'pdf') return FileText

    // Spreadsheets
    if (['xlsx', 'xls', 'csv'].includes(ext)) return FileSpreadsheet

    // Images
    if (['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'bmp', 'ico'].includes(ext)) return FileImage

    // Code files
    if ([
        'js', 'ts', 'jsx', 'tsx', 'vue', 'svelte',
        'py', 'rb', 'go', 'rs', 'java', 'kt', 'swift', 'c', 'cpp', 'h', 'hpp', 'cs',
        'php', 'html', 'css', 'scss', 'less', 'json', 'xml', 'yaml', 'yml',
        'sql', 'sh', 'bash', 'zsh', 'dockerfile'
    ].includes(ext)) return FileCode

    return FileIcon
}
</script>
