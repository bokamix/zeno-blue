<template>
    <!-- Collapsed strip (desktop only) -->
    <div
        v-if="isCollapsed"
        class="hidden md:flex flex-col items-center py-4 px-1 bg-[var(--bg-base)]"
    >
        <button
            @click="$emit('toggle-collapsed')"
            class="p-2 text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-surface)] rounded-xl transition-all"
            :title="$t('nav.showSidebar')"
        >
            <PanelRightClose v-if="position === 'left'" class="w-5 h-5" />
            <PanelLeftClose v-else class="w-5 h-5" />
        </button>
    </div>

    <!-- Mobile backdrop with blur (show when open OR dragging sidebar) -->
    <div
        v-if="isOpen || isDraggingSidebar"
        class="fixed inset-0 backdrop-blur-sm bg-black/30 z-40 md:hidden"
        :class="{ 'transition-opacity duration-300': !isDraggingSidebar }"
        @click="$emit('close')"
    ></div>

    <!-- Full sidebar -->
    <div
        v-show="!isCollapsed || isOpen || isDraggingSidebar"
        class="fixed inset-y-0 z-50 w-[calc(100vw-40px)] md:w-auto transform md:relative md:z-auto flex flex-col"
        :class="[
            position === 'left' ? 'left-0' : 'right-0',
            isDraggingSidebar
                ? ''
                : (position === 'left'
                    ? (isOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0')
                    : (isOpen ? 'translate-x-0' : 'translate-x-full md:translate-x-0')),
            isCollapsed ? 'md:hidden' : '',
            (isResizing || isDraggingSidebar) ? '' : 'transition-all duration-300'
        ]"
        :style="{
            width: isDesktop ? sidebarWidth + 'px' : undefined,
            transform: isDraggingSidebar ? swipeState.sidebarTransform.value : undefined
        }"
        :data-position="position"
    >
        <!-- Resize handle (desktop only) -->
        <div
            v-if="isDesktop && !isCollapsed"
            class="hidden md:block absolute top-0 bottom-0 w-1.5 cursor-col-resize hover:bg-blue-500/50 active:bg-blue-500/70 transition-colors z-20"
            :class="position === 'left' ? '-right-0.5' : '-left-0.5'"
            @mousedown="startResize"
        ></div>
        <!-- Logo area (desktop only) -->
        <div class="hidden md:flex items-center justify-between h-16 px-4 bg-[var(--bg-base)]">
            <a href="/" @click.prevent="$emit('navigate-home')" class="relative cursor-pointer hover:opacity-80 transition-opacity">
                <span class="text-xl font-bold tracking-wide" style="font-family: 'Orbitron', sans-serif;">
                    <span class="logo-text">ZENO</span><span class="text-blue-400 font-medium">.blue</span>
                </span>
                <div class="absolute -inset-4 bg-blue-500/10 blur-2xl -z-10"></div>
            </a>
            <!-- Collapse button -->
            <button
                @click="$emit('toggle-collapsed')"
                class="p-2 text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-surface)] rounded-xl transition-all"
                :title="$t('nav.hideSidebar')"
            >
                <PanelLeftClose v-if="position === 'left'" class="w-5 h-5" />
                <PanelRightClose v-else class="w-5 h-5" />
            </button>
        </div>

        <!-- Card panel -->
        <div class="flex-1 md:mx-3 md:mb-3 card card-premium rounded-none rounded-r-2xl md:rounded-3xl overflow-hidden flex flex-col relative">

            <!-- Single scroll container (both mobile and desktop) -->
            <div ref="scrollContainer" class="flex-1 overflow-y-auto custom-scroll" @scroll="onScroll">
                <!-- Files Section with drag & drop -->
                <div
                    ref="filesSectionRef"
                    class="relative"
                    @dragenter.prevent="handleFilesDragEnter"
                    @dragover.prevent
                    @dragleave="handleFilesDragLeave"
                    @drop.prevent="handleFilesDrop"
                >
                    <!-- Drag overlay -->
                    <div
                        v-if="isDraggingOnFiles"
                        class="absolute inset-0 z-10 bg-blue-500/10 border-2 border-dashed border-blue-500/50 flex items-center justify-center"
                    >
                        <div class="text-center">
                            <Upload class="w-6 h-6 text-blue-400 mx-auto mb-1" />
                            <span class="text-xs text-blue-300">{{ $t('sidebar.dropFilesHere') }}</span>
                        </div>
                    </div>

                    <!-- Files header (sticky) -->
                    <div class="sticky top-0 z-10 px-4 py-3 flex justify-between items-center border-b border-[var(--border-subtle)] bg-[var(--bg-surface)]">
                        <span class="text-xs font-semibold uppercase tracking-wider text-zinc-600 dark:text-zinc-400">{{ $t('sidebar.files') }}</span>
                        <div class="flex gap-1">
                            <button @click="$emit('create-folder')" class="p-1.5 rounded-lg text-[var(--text-muted)] hover:text-[var(--text-primary)]" :title="$t('sidebar.createFolder')">
                                <FolderPlus class="w-3.5 h-3.5" />
                            </button>
                            <button @click="$emit('create-file')" class="p-1.5 rounded-lg text-[var(--text-muted)] hover:text-[var(--text-primary)]" :title="$t('sidebar.createFile')">
                                <FilePlus class="w-3.5 h-3.5" />
                            </button>
                            <button @click="$emit('refresh')" class="p-1.5 rounded-lg text-[var(--text-muted)] hover:text-[var(--text-primary)]">
                                <RefreshCw class="w-3.5 h-3.5" />
                            </button>
                            <label class="p-1.5 rounded-lg text-[var(--text-muted)] hover:text-[var(--text-primary)] cursor-pointer">
                                <Upload class="w-3.5 h-3.5" />
                                <input type="file" class="hidden" @change="handleUpload" multiple>
                            </label>
                        </div>
                    </div>

                    <!-- File list -->
                    <div v-if="artifacts.length > 0" class="p-2">
                        <FileTreeItem
                            v-for="item in (showAllFiles ? artifacts : artifacts.slice(0, 5))"
                            :key="item.path"
                            :item="item"
                            :open-file-paths="openFilePaths"
                            @select="$emit('select-file', $event)"
                            @delete="$emit('delete-file', $event)"
                            @open="$emit('open-file', $event)"
                            @rename="$emit('rename-file', $event)"
                            @upload-to-folder="handleUploadToFolder"
                            @move-to-folder="handleMoveToFolder"
                        />

                        <!-- Show more button (inline, not sticky) -->
                        <button
                            v-if="artifacts.length > 5 && !showAllFiles"
                            @click="toggleShowAllFiles"
                            class="w-full py-2 text-xs text-zinc-500 hover:text-[var(--text-primary)] flex items-center justify-center gap-1 transition-colors"
                        >
                            <span>{{ $t('sidebar.showMore', { count: artifacts.length - 5 }) }}</span>
                            <ChevronDown class="w-3 h-3" />
                        </button>
                    </div>
                    <div v-else class="px-4 py-6 text-xs text-zinc-600 text-center">
                        {{ $t('sidebar.noFilesYet') }}
                    </div>
                </div>

                <!-- Divider -->
                <div ref="dividerRef" class="mx-4 h-px bg-[var(--border-subtle)]"></div>

                <!-- Chats Section (sticky header) -->
                <div class="sticky top-0 z-10 px-4 py-3 border-b border-[var(--border-subtle)] bg-[var(--bg-surface)]">
                    <span class="text-xs font-semibold uppercase tracking-wider text-zinc-600 dark:text-zinc-400">{{ $t('sidebar.chats') }}</span>
                </div>

                <!-- Conversations list -->
                <ConversationList
                    :conversations="conversations"
                    :current-conversation-id="currentConversationId"
                    @select-conversation="$emit('select-conversation', $event)"
                    @archive-conversation="$emit('archive-conversation', $event)"
                    @show-scheduler="$emit('show-scheduler', $event)"
                />

                <!-- Archived Section (collapsed by default) -->
                <div v-if="archivedConversations.length > 0">
                    <!-- Divider -->
                    <div class="mx-4 h-px bg-[var(--border-subtle)]"></div>

                    <!-- Archived header -->
                    <button
                        @click="showArchived = !showArchived"
                        class="w-full px-4 py-3 flex justify-between items-center text-xs font-semibold uppercase tracking-wider text-zinc-500 hover:text-zinc-400 transition-colors"
                    >
                        <span>{{ $t('sidebar.archived') }}</span>
                        <ChevronDown class="w-3 h-3 transition-transform" :class="{ 'rotate-180': showArchived }" />
                    </button>

                    <!-- Archived conversations list -->
                    <div v-show="showArchived" class="pb-2">
                        <div
                            v-for="conv in archivedConversations"
                            :key="conv.id"
                            class="mx-2 mb-1 px-3 py-2 rounded-lg bg-[var(--bg-surface)]/50 flex items-center gap-2 text-sm text-[var(--text-muted)]"
                        >
                            <Archive class="w-4 h-4 flex-shrink-0" />
                            <span class="truncate flex-1">{{ conv.preview || $t('sidebar.emptyConversation') }}</span>
                            <button
                                @click="$emit('restore-conversation', conv.id)"
                                class="p-1 rounded hover:bg-emerald-500/20 text-zinc-500 hover:text-emerald-400"
                                :title="$t('sidebar.restore')"
                            >
                                <RotateCcw class="w-3.5 h-3.5" />
                            </button>
                            <button
                                @click="$emit('delete-archived', conv.id)"
                                class="p-1 rounded hover:bg-red-500/20 text-zinc-500 hover:text-red-400"
                                :title="$t('sidebar.deletePermanently')"
                            >
                                <Trash2 class="w-3.5 h-3.5" />
                            </button>
                        </div>
                    </div>
                </div>

            </div>

            <!-- Sticky "Show less" button (visible when files expanded and in view) -->
            <div
                v-if="showAllFiles && artifacts.length > 5 && showStickyShowLess"
                class="absolute bottom-0 left-0 right-0 p-2 bg-[var(--bg-surface)] border-t border-[var(--border-subtle)]"
            >
                <button
                    @click="toggleShowAllFiles"
                    class="w-full py-2 text-xs text-zinc-500 hover:text-[var(--text-primary)] flex items-center justify-center gap-1 transition-colors bg-[var(--bg-base)] rounded-lg"
                >
                    <span>{{ $t('sidebar.showLess') }}</span>
                    <ChevronUp class="w-3 h-3" />
                </button>
            </div>

            <!-- Sticky "Scroll to top" button (visible when deep in chats) -->
            <div
                v-if="showScrollToTop && !showStickyShowLess"
                class="absolute bottom-0 left-0 right-0 p-2 bg-[var(--bg-surface)] border-t border-[var(--border-subtle)]"
            >
                <button
                    @click="scrollToTop"
                    class="w-full py-2 text-xs text-zinc-500 hover:text-[var(--text-primary)] flex items-center justify-center gap-1 transition-colors bg-[var(--bg-base)] rounded-lg"
                >
                    <ArrowUp class="w-3 h-3" />
                    <span>{{ $t('sidebar.scrollToTop') }}</span>
                </button>
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, inject, provide } from 'vue'
import { RefreshCw, Upload, ChevronDown, ChevronUp, ArrowUp, PanelLeftClose, PanelRightClose, Archive, RotateCcw, Trash2, FolderPlus, FilePlus } from 'lucide-vue-next'
import FileTreeItem from './FileTreeItem.vue'
import ConversationList from './ConversationList.vue'
import { useWorkspaceState } from '../composables/state/useWorkspaceState'
import { useUIState } from '../composables/state/useUIState'

const { openFilePaths, revealFilePath } = useWorkspaceState()
const { sidebarWidth, setSidebarWidth, loadSidebarWidth } = useUIState()
const artifactsRefreshKey = inject('artifactsRefreshKey', ref(0))

// Swipe gesture state from parent
const swipeState = inject('swipeState', {
    isDragging: ref(false),
    dragTarget: ref(null),
    sidebarTransform: ref(null)
})

// Check if currently dragging sidebar
const isDraggingSidebar = computed(() =>
    swipeState.isDragging.value && swipeState.dragTarget.value === 'sidebar'
)

// Global menu state - only one dropdown can be open at a time (files + conversations)
const globalOpenMenuId = ref(null)
provide('globalOpenMenuId', globalOpenMenuId)

// Desktop detection
const isDesktop = ref(false)
const checkDesktop = () => {
    isDesktop.value = window.innerWidth >= 768
}

onMounted(() => {
    checkDesktop()
    loadSidebarWidth()
    window.addEventListener('resize', checkDesktop)
})

onUnmounted(() => {
    window.removeEventListener('resize', checkDesktop)
    document.removeEventListener('mousemove', onResize)
    document.removeEventListener('mouseup', stopResize)
})

// Ref for conversation list scroll
const conversationListRef = ref(null)

const scrollConversationsToTop = () => {
    if (conversationListRef.value) {
        conversationListRef.value.scrollTop = 0
    }
}

defineExpose({ scrollConversationsToTop })

const props = defineProps({
    artifacts: {
        type: Array,
        default: () => []
    },
    conversations: {
        type: Array,
        default: () => []
    },
    archivedConversations: {
        type: Array,
        default: () => []
    },
    currentConversationId: {
        type: String,
        default: null
    },
    isOpen: {
        type: Boolean,
        default: false
    },
    isCollapsed: {
        type: Boolean,
        default: false
    },
    position: {
        type: String,
        default: 'left'
    },
    refreshKey: {
        type: Number,
        default: 0
    }
})

const emit = defineEmits(['refresh', 'select-file', 'delete-file', 'open-file', 'rename-file', 'select-conversation', 'archive-conversation', 'restore-conversation', 'delete-archived', 'upload', 'upload-multiple', 'toggle-collapsed', 'navigate-home', 'show-scheduler', 'create-folder', 'create-file', 'move-to-folder', 'close'])

// Show all files state
const showAllFiles = ref(false)

// Resize handling
const isResizing = ref(false)
const resizeStartX = ref(0)
const resizeStartWidth = ref(0)

const startResize = (e) => {
    isResizing.value = true
    resizeStartX.value = e.clientX
    resizeStartWidth.value = sidebarWidth.value
    document.addEventListener('mousemove', onResize)
    document.addEventListener('mouseup', stopResize)
    document.body.style.cursor = 'col-resize'
    document.body.style.userSelect = 'none'
}

const onResize = (e) => {
    if (!isResizing.value) return
    const delta = props.position === 'left'
        ? e.clientX - resizeStartX.value
        : resizeStartX.value - e.clientX
    setSidebarWidth(resizeStartWidth.value + delta)
}

const stopResize = () => {
    isResizing.value = false
    document.removeEventListener('mousemove', onResize)
    document.removeEventListener('mouseup', stopResize)
    document.body.style.cursor = ''
    document.body.style.userSelect = ''
}

// Auto-expand file list when revealing a file beyond first 5
watch(() => revealFilePath.value, (reveal) => {
    if (reveal && !showAllFiles.value) {
        const targetIndex = props.artifacts.findIndex(item =>
            item.path === reveal.path || reveal.path.startsWith(item.path + '/')
        )
        if (targetIndex >= 5) {
            showAllFiles.value = true
        }
    }
})

// Show archived conversations
const showArchived = ref(false)
const scrollContainer = ref(null)
const filesSectionRef = ref(null)
const dividerRef = ref(null)

// Sticky "Show less" button visibility
const showStickyShowLess = ref(true)
// Scroll to top button visibility (when deep in chats)
const showScrollToTop = ref(false)
const STICKY_BUTTON_OFFSET = 50 // px offset for sticky button visibility threshold

const onScroll = () => {
    if (!scrollContainer.value || !dividerRef.value) {
        showStickyShowLess.value = true
        showScrollToTop.value = false
        return
    }

    const containerRect = scrollContainer.value.getBoundingClientRect()
    const dividerRect = dividerRef.value.getBoundingClientRect()

    // Show "Show less" only when files expanded and divider is below visible area
    if (showAllFiles.value) {
        showStickyShowLess.value = dividerRect.top > containerRect.bottom - STICKY_BUTTON_OFFSET
    } else {
        showStickyShowLess.value = false
    }

    // Show "scroll to top" when divider is above visible area (user scrolled past files into chats)
    showScrollToTop.value = dividerRect.bottom < containerRect.top + STICKY_BUTTON_OFFSET
}

const scrollToTop = () => {
    if (scrollContainer.value) {
        scrollContainer.value.scrollTo({ top: 0, behavior: 'smooth' })
    }
}

// Toggle show all files with scroll reset on collapse
const toggleShowAllFiles = () => {
    const wasExpanded = showAllFiles.value
    showAllFiles.value = !showAllFiles.value

    // Reset scroll to top when collapsing to prevent scroll lock on mobile
    if (wasExpanded && scrollContainer.value) {
        scrollContainer.value.scrollTop = 0
    }
}

const handleUpload = (event) => {
    const files = Array.from(event.target.files || [])
    if (files.length) {
        emit('upload-multiple', files, '')
    }
    event.target.value = ''
}

// Drag & drop state
const isDraggingOnFiles = ref(false)

// Handle drag enter - only show overlay for PC file drops, not internal moves
const handleFilesDragEnter = (event) => {
    // Check if this is an internal drag (moving files within the app)
    // Internal drags have 'application/x-artifact-path' type
    const types = event.dataTransfer?.types || []
    const isInternalDrag = types.includes('application/x-artifact-path')

    // Only show the upload overlay for external (PC) file drags
    if (!isInternalDrag) {
        isDraggingOnFiles.value = true
    }
}

// Handle drag leave (prevent false triggers from child elements)
const handleFilesDragLeave = (event) => {
    if (!event.currentTarget.contains(event.relatedTarget)) {
        isDraggingOnFiles.value = false
    }
}

// Handle drop on files section (uploads to root)
const handleFilesDrop = (event) => {
    isDraggingOnFiles.value = false

    const types = event.dataTransfer?.types || []

    // Handle internal file moves - move to root
    if (types.includes('application/x-artifact-path')) {
        const sourcePath = event.dataTransfer.getData('application/x-artifact-path')
        if (sourcePath && sourcePath.includes('/')) {
            // File is in a folder - move to root
            emit('move-to-folder', sourcePath, '')
        }
        return
    }

    // Handle external file uploads
    const files = Array.from(event.dataTransfer?.files || [])
    if (files.length) {
        emit('upload-multiple', files, '')
    }
}

// Handle upload to specific folder (from FileTreeItem)
const handleUploadToFolder = (files, path) => {
    emit('upload-multiple', files, path)
}

// Handle move to folder (from FileTreeItem)
const handleMoveToFolder = (sourcePath, destFolderPath) => {
    emit('move-to-folder', sourcePath, destFolderPath)
}
</script>
