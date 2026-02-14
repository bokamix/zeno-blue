<template>
    <div class="file-item-wrapper">
        <div
            ref="fileItemRef"
            class="file-item group"
            :class="{
                'bg-blue-500/20 ring-1 ring-blue-500/50': isDragOver && item.is_dir,
                'highlight-reveal': isHighlighted,
                'dragging': isDragging
            }"
            :style="{ paddingLeft: (level * 16 + 12) + 'px' }"
            draggable="true"
            @click="handleClick"
            @contextmenu.prevent="handleRightClick"
            @dragstart="handleDragStart"
            @dragend="handleDragEnd"
            @dragenter.prevent="item.is_dir && (isDragOver = true)"
            @dragover.prevent
            @dragleave="handleDragLeave"
            @drop.prevent="handleFolderDrop"
        >
            <span class="mr-2 flex-shrink-0">
                <FolderOpen v-if="item.is_dir && isOpen" class="w-4 h-4 text-amber-400" />
                <Folder v-else-if="item.is_dir" class="w-4 h-4 text-amber-400" />
                <component v-else :is="fileIconConfig.icon" class="w-4 h-4" :class="fileIconConfig.color" />
            </span>
            <span class="truncate text-[13px] flex-1">{{ item.name }}</span>
            <!-- Open in tab indicator (right of filename) -->
            <span
                v-if="isOpenInTab"
                class="w-1.5 h-1.5 rounded-full bg-blue-400 flex-shrink-0 ml-1 mr-1"
                :title="$t('sidebar.openInTab')"
            ></span>

            <!-- Desktop: hover-reveal action buttons -->
            <button
                v-if="item.is_dir"
                @click.stop="handleDownloadZip"
                class="action-btn desktop-only flex-shrink-0 p-1 rounded hover:bg-blue-500/20"
                :title="$t('sidebar.downloadAsZip')"
            >
                <Download class="w-4 h-4" />
            </button>
            <button
                @click.stop="handleRename"
                class="action-btn desktop-only flex-shrink-0 p-1 rounded hover:bg-blue-500/20"
                :title="$t('sidebar.renameFile')"
            >
                <Pencil class="w-4 h-4" />
            </button>
            <button
                @click.stop="handleDelete"
                class="action-btn desktop-only flex-shrink-0 p-1 rounded hover:bg-red-500/20"
                :title="$t('sidebar.deleteFile')"
            >
                <Trash2 class="w-4 h-4" />
            </button>

            <!-- Mobile: 3-dot menu button -->
            <button
                @click.stop="toggleMenu"
                class="menu-btn mobile-only flex-shrink-0 p-1 rounded"
                :class="{ 'menu-open': menuOpen }"
            >
                <MoreVertical class="w-4 h-4" />
            </button>
        </div>

        <!-- Mobile dropdown menu -->
        <div v-if="menuOpen" class="dropdown-menu" @click.stop>
            <button v-if="item.is_dir" @click="handleDownloadZipAndClose">
                <Download class="w-4 h-4" />
                {{ $t('sidebar.downloadAsZip') }}
            </button>
            <button @click="handleRenameAndClose">
                <Pencil class="w-4 h-4" />
                {{ $t('sidebar.renameFile') }}
            </button>
            <button @click="handleDeleteAndClose" class="delete-action">
                <Trash2 class="w-4 h-4" />
                {{ $t('sidebar.deleteFile') }}
            </button>
        </div>

        <!-- Children -->
        <div v-if="item.is_dir && isOpen">
            <div v-if="isLoadingChildren" class="pl-8 py-2 text-xs text-zinc-600">Loading...</div>
            <FileTreeItem
                v-for="child in children"
                :key="child.path"
                :item="child"
                :level="level + 1"
                :open-file-paths="openFilePaths"
                @select="$emit('select', $event)"
                @delete="$emit('delete', $event)"
                @open="$emit('open', $event)"
                @rename="$emit('rename', $event)"
                @upload-to-folder="(files, path) => $emit('upload-to-folder', files, path)"
                @move-to-folder="(source, dest) => $emit('move-to-folder', source, dest)"
            />
        </div>
    </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, onMounted, onUnmounted, inject } from 'vue'
import { Folder, FolderOpen, Trash2, Download, Pencil, MoreVertical } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { useApi } from '../composables/useApi'
import { getFileIconConfig } from '../composables/useFileDetection'
import { useWorkspaceState } from '../composables/state/useWorkspaceState'

const { t } = useI18n()
const { revealFilePath, clearRevealFile } = useWorkspaceState()
const artifactsRefreshKey = inject('artifactsRefreshKey', ref(0))
const globalOpenMenuId = inject('globalOpenMenuId', ref(null))

const props = defineProps({
    item: Object,
    level: {
        type: Number,
        default: 0
    },
    openFilePaths: {
        type: Set,
        default: () => new Set()
    },
    refreshKey: {
        type: Number,
        default: 0
    }
})

const emit = defineEmits(['select', 'delete', 'open', 'upload-to-folder', 'move-to-folder', 'rename'])
const { getArtifacts, getZipDownloadUrl } = useApi()

const isOpen = ref(false)
const children = ref([])
const isLoadingChildren = ref(false)
const isDragOver = ref(false)
const isDragging = ref(false)
const fileItemRef = ref(null)
const isHighlighted = ref(false)
let highlightTimeoutId = null

// Menu state - uses global state (prefixed with 'file:' to avoid conflicts with conversation ids)
const menuId = computed(() => `file:${props.item.path}`)
const menuOpen = computed(() => globalOpenMenuId.value === menuId.value)

// Toggle dropdown menu
const toggleMenu = () => {
    if (menuOpen.value) {
        globalOpenMenuId.value = null
    } else {
        globalOpenMenuId.value = menuId.value
    }
}

// Close menu
const closeMenu = () => {
    globalOpenMenuId.value = null
}

// Close menu when clicking outside
const handleClickOutside = (event) => {
    if (menuOpen.value && fileItemRef.value && !fileItemRef.value.contains(event.target)) {
        closeMenu()
    }
}

// Menu action handlers (close menu after action)
const handleDownloadZipAndClose = () => {
    closeMenu()
    handleDownloadZip()
}

const handleRenameAndClose = () => {
    closeMenu()
    handleRename()
}

const handleDeleteAndClose = () => {
    closeMenu()
    handleDelete()
}

onMounted(() => {
    document.addEventListener('click', handleClickOutside)
})

// Cleanup on unmount
onUnmounted(() => {
    if (highlightTimeoutId) {
        clearTimeout(highlightTimeoutId)
    }
    document.removeEventListener('click', handleClickOutside)
})

// Check if this file is open in a tab
const isOpenInTab = computed(() => !props.item.is_dir && props.openFilePaths.has(props.item.path))

// File icon configuration from composable
const fileIconConfig = computed(() => {
    if (props.item.is_dir) return null
    return getFileIconConfig(props.item.name)
})

const handleClick = async (e) => {
    emit('select', props.item)

    if (props.item.is_dir) {
        isOpen.value = !isOpen.value
        if (isOpen.value) {
            await fetchChildren()
        }
    } else {
        // Shift+click = download directly, otherwise open in viewer
        if (e.shiftKey && props.item.download_url) {
            window.open('/api' + props.item.download_url, '_blank')
        } else {
            emit('open', props.item)
        }
    }
}

const fetchChildren = async () => {
    isLoadingChildren.value = true
    try {
        children.value = await getArtifacts(props.item.path)
    } catch (e) {
        console.error(e)
    } finally {
        isLoadingChildren.value = false
    }
}

const handleDelete = () => {
    if (confirm(t('sidebar.confirmDeleteFile', { name: props.item.name }))) {
        emit('delete', props.item)
    }
}

const handleRename = () => {
    emit('rename', props.item)
}

const handleRightClick = () => {
    handleDelete()
}

const handleDownloadZip = () => {
    window.open(getZipDownloadUrl(props.item.path), '_blank')
}

// Drag & drop handlers
const handleDragStart = (event) => {
    // Store the file path for move operation
    event.dataTransfer.setData('application/x-artifact-path', props.item.path)
    event.dataTransfer.setData('text/plain', props.item.name)
    event.dataTransfer.effectAllowed = 'move'
    isDragging.value = true

    // Create a clean drag image (prevents weird background content showing)
    const dragEl = document.createElement('div')
    dragEl.textContent = props.item.name
    dragEl.style.cssText = `
        position: absolute;
        top: -1000px;
        left: -1000px;
        padding: 8px 12px;
        background: #1e1e2e;
        color: #fff;
        border-radius: 6px;
        font-size: 13px;
        white-space: nowrap;
        box-shadow: 0 4px 12px rgba(0,0,0,0.3);
    `
    document.body.appendChild(dragEl)
    event.dataTransfer.setDragImage(dragEl, 0, 0)

    // Clean up after drag starts
    setTimeout(() => dragEl.remove(), 0)
}

const handleDragEnd = () => {
    isDragging.value = false
}

const handleDragLeave = (event) => {
    if (!event.currentTarget.contains(event.relatedTarget)) {
        isDragOver.value = false
    }
}

const handleFolderDrop = (event) => {
    isDragOver.value = false

    const sourcePath = event.dataTransfer.getData('application/x-artifact-path')

    // If dropping on a non-folder, move source to root (if source is in a subfolder)
    if (!props.item.is_dir) {
        if (sourcePath && sourcePath.includes('/')) {
            event.stopPropagation()
            emit('move-to-folder', sourcePath, '')  // Move to root
        }
        return
    }

    // Case 1: Moving existing file within workspace (to this folder)
    if (sourcePath) {
        // Prevent dropping on self
        if (sourcePath === props.item.path) return
        // Prevent dropping folder into its own descendant
        if (props.item.path.startsWith(sourcePath + '/')) return

        event.stopPropagation()
        emit('move-to-folder', sourcePath, props.item.path)
        return
    }

    // Case 2: Uploading files from PC (existing behavior)
    const files = Array.from(event.dataTransfer?.files || [])
    if (files.length) {
        event.stopPropagation()
        emit('upload-to-folder', files, props.item.path)
    }
}

// Watch for refreshKey changes to refresh open folder contents
watch(artifactsRefreshKey, async (newVal, oldVal) => {
    if (newVal !== oldVal && props.item.is_dir && isOpen.value) {
        await fetchChildren()
    }
})

// Watch for reveal events to expand folders and highlight files
watch(() => revealFilePath.value, async (reveal) => {
    if (!reveal) return
    const targetPath = reveal.path

    // Case 1: This is the target file - scroll to it and highlight
    if (targetPath === props.item.path) {
        await nextTick()
        if (fileItemRef.value) {
            fileItemRef.value.scrollIntoView({ behavior: 'smooth', block: 'center' })
            isHighlighted.value = true
            highlightTimeoutId = setTimeout(() => { isHighlighted.value = false }, 1500)
        }
        clearRevealFile()
        return
    }

    // Case 2: This is a parent folder - expand it
    if (props.item.is_dir && targetPath.startsWith(props.item.path + '/')) {
        if (!isOpen.value) {
            isOpen.value = true
            await fetchChildren()
        }
    }
}, { immediate: true })
</script>

<style scoped>
/* Desktop: hover-reveal action buttons */
.action-btn.desktop-only {
    color: #71717a;
    opacity: 0;
    transition: all 0.15s ease;
}

.action-btn.desktop-only:hover {
    color: var(--text-primary, #fff);
}

.file-item:hover .action-btn.desktop-only {
    opacity: 1;
}

/* Mobile: 3-dot menu button */
.menu-btn.mobile-only {
    display: none;
    color: var(--text-muted);
    transition: all 0.15s ease;
}

.menu-btn.mobile-only:hover,
.menu-btn.mobile-only.menu-open {
    color: var(--text-primary);
    background: var(--bg-elevated);
}

/* Show/hide based on device */
@media (hover: none) {
    .action-btn.desktop-only {
        display: none;
    }
    .menu-btn.mobile-only {
        display: flex;
    }
}

/* File item wrapper for dropdown positioning */
.file-item-wrapper {
    position: relative;
}

/* Dropdown menu */
.dropdown-menu {
    position: absolute;
    right: 8px;
    top: 100%;
    margin-top: 4px;
    background: #2a2a3e;
    border: 1px solid rgba(37, 99, 235, 0.4);
    border-radius: 10px;
    box-shadow:
        0 4px 16px rgba(0,0,0,0.3),
        0 0 20px rgba(37, 99, 235, 0.15);
    z-index: 100;
    min-width: 160px;
    overflow: hidden;
}

.dropdown-menu button {
    display: flex;
    align-items: center;
    gap: 10px;
    width: 100%;
    padding: 10px 14px;
    text-align: left;
    font-size: 14px;
    color: var(--text-primary);
    background: transparent;
    border: none;
    cursor: pointer;
    transition: background 0.15s ease;
}

.dropdown-menu button:hover {
    background: var(--bg-surface);
}

.dropdown-menu button.delete-action {
    color: #f87171;
}

.dropdown-menu button.delete-action:hover {
    background: rgba(239, 68, 68, 0.15);
}

/* Light theme adjustments */
[data-theme="light"] .dropdown-menu {
    background: white;
    border: 1px solid rgba(79, 70, 229, 0.3);
    box-shadow:
        0 4px 16px rgba(0,0,0,0.12),
        0 0 20px rgba(79, 70, 229, 0.1);
}

/* Dragging state */
.file-item.dragging {
    opacity: 0.5;
}

/* Prevent text selection during drag on touch devices */
.file-item {
    -webkit-user-select: none;
    user-select: none;
    -webkit-touch-callout: none;
}
</style>
