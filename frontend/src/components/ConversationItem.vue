<template>
    <!-- Mobile: Compact layout with 3-dot menu -->
    <div
        v-if="isMobile"
        class="conv-item-mobile"
        :class="{ 'active': isActive && !hideActiveIndicator }"
        ref="mobileItemRef"
    >
        <div
            class="item-content"
            @click="handleMobileClick"
        >
            <!-- Line 1: Status (only when active) + Title -->
            <div class="line-1">
                <!-- Status indicator - only shown for active/pending/scheduler -->
                <!-- Active job (pulsing green) -->
                <span v-if="conv.has_active_job" class="status-dot">
                    <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                    <span class="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                </span>
                <!-- Pending question (pulsing amber) -->
                <span v-else-if="conv.has_pending_question" class="status-dot">
                    <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
                    <span class="relative inline-flex rounded-full h-2 w-2 bg-amber-500"></span>
                </span>
                <!-- Scheduler run (clock icon in cyan) -->
                <Clock v-else-if="conv.is_scheduler_run" class="w-3.5 h-3.5 text-cyan-400 flex-shrink-0" />
                <!-- No icon for regular chats - ChatGPT style -->

                <span class="title">{{ conv.preview || $t('sidebar.emptyConversation') }}</span>
                <span
                    v-if="unreadCount > 0 && !isActive && !conv.has_active_job && !conv.has_pending_question"
                    class="unread-badge"
                >
                    {{ unreadCount > 99 ? '99+' : unreadCount }}
                </span>
            </div>
        </div>

        <!-- 3-dot menu button -->
        <button
            @click.stop="toggleMenu"
            class="menu-button"
            :class="{ 'menu-open': menuOpen }"
        >
            <MoreVertical :size="18" />
        </button>

        <!-- Dropdown menu -->
        <div v-if="menuOpen" class="dropdown-menu" @click.stop>
            <button @click="startRename">
                <Pencil :size="16" />
                {{ $t('sidebar.renameConversation') }}
            </button>
            <button @click="handleArchive" class="archive-action">
                <Archive :size="16" />
                {{ $t('sidebar.archiveConversation') }}
            </button>
        </div>

        <!-- Mobile rename overlay -->
        <div v-if="isEditing" class="rename-overlay" @click.stop>
            <input
                ref="editInput"
                v-model="editName"
                @keydown.enter="saveRename"
                @keydown.escape="cancelRename"
                class="rename-input"
                :placeholder="$t('sidebar.enterName')"
            />
            <button @click.stop="saveRename" class="rename-save">
                <Check class="w-5 h-5" />
            </button>
            <button @click.stop="cancelRename" class="rename-cancel">
                <X class="w-5 h-5" />
            </button>
        </div>
    </div>

    <!-- Desktop: Keep existing layout -->
    <div
        v-else
        @click="!isEditing && $emit('select', conv.id)"
        class="sidebar-item mb-1 group"
        :class="{
            'active': isActive && !hideActiveIndicator,
            'status-active': conv.has_active_job,
            'status-pending': !conv.has_active_job && conv.has_pending_question,
            'status-unread': !conv.has_active_job && !conv.has_pending_question && !isActive && unreadCount > 0
        }"
    >
        <!-- Status indicator -->
        <span class="flex-shrink-0 w-4 h-4 flex items-center justify-center">
            <!-- Active job (pulsing green) -->
            <span v-if="conv.has_active_job" class="relative flex items-center justify-center w-2.5 h-2.5">
                <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                <span class="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <!-- Pending question (pulsing amber) -->
            <span v-else-if="conv.has_pending_question" class="relative flex items-center justify-center w-2.5 h-2.5">
                <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
                <span class="relative inline-flex rounded-full h-2 w-2 bg-amber-500"></span>
            </span>
            <!-- Scheduler run (clock icon in cyan) -->
            <Clock v-else-if="conv.is_scheduler_run" class="w-4 h-4 text-cyan-400" />
            <!-- Default (message icon) -->
            <MessageSquare v-else class="w-4 h-4 text-zinc-500" />
        </span>

        <!-- Edit mode -->
        <div v-if="isEditing" class="flex items-center gap-1 flex-1 min-w-0" @click.stop>
            <input
                ref="editInput"
                v-model="editName"
                @keydown.enter="saveRename"
                @keydown.escape="cancelRename"
                class="flex-1 min-w-0 px-2 py-0.5 bg-[var(--bg-surface)] border border-[var(--border-subtle)] rounded text-[13px] text-[var(--text-primary)] focus:outline-none focus:border-blue-500"
                :placeholder="$t('sidebar.enterName')"
            />
            <button
                @click.stop="saveRename"
                class="p-1 text-emerald-400 hover:text-emerald-300 hover:bg-emerald-500/20 rounded transition-all"
            >
                <Check class="w-3.5 h-3.5" />
            </button>
            <button
                @click.stop="cancelRename"
                class="p-1 text-zinc-400 hover:text-zinc-300 hover:bg-white/10 rounded transition-all"
            >
                <X class="w-3.5 h-3.5" />
            </button>
        </div>

        <!-- Display mode -->
        <template v-else>
            <!-- Preview text -->
            <span class="truncate text-[14px] font-medium flex-1">{{ conv.preview || $t('sidebar.emptyConversation') }}</span>

            <!-- Unread count badge -->
            <span
                v-if="unreadCount > 0 && !isActive && !conv.has_active_job && !conv.has_pending_question"
                class="flex-shrink-0 min-w-[20px] h-5 px-1.5 flex items-center justify-center rounded-full bg-blue-500 text-white text-xs font-medium"
            >
                {{ unreadCount > 99 ? '99+' : unreadCount }}
            </span>

            <!-- Scheduler info button (for scheduler runs) -->
            <button
                v-if="conv.is_scheduler_run && conv.scheduler_id"
                @click.stop="$emit('show-scheduler', conv.scheduler_id)"
                class="scheduler-info-btn flex-shrink-0 p-1 rounded hover:bg-cyan-500/20"
                :title="$t('sidebar.viewScheduler')"
            >
                <Clock class="w-4 h-4" />
            </button>

            <!-- Rename button -->
            <button
                @click.stop="startRename"
                class="rename-conv-btn flex-shrink-0 p-1 rounded hover:bg-blue-500/20"
                :title="$t('sidebar.renameConversation')"
            >
                <Pencil class="w-4 h-4" />
            </button>

            <!-- Archive button -->
            <button
                @click.stop="$emit('archive', conv.id)"
                class="archive-conv-btn flex-shrink-0 p-1 rounded hover:bg-amber-500/20"
                :title="$t('sidebar.archiveConversation')"
            >
                <Archive class="w-4 h-4" />
            </button>
        </template>
    </div>
</template>

<script setup>
import { ref, nextTick, computed, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { MessageSquare, Archive, Clock, Pencil, Check, X, MoreVertical } from 'lucide-vue-next'
import { useApi } from '../composables/useApi'

const { t } = useI18n()
const api = useApi()

const props = defineProps({
    conv: {
        type: Object,
        required: true
    },
    isActive: {
        type: Boolean,
        default: false
    },
    hideActiveIndicator: {
        type: Boolean,
        default: false
    },
    unreadCount: {
        type: Number,
        default: 0
    },
    isMobile: {
        type: Boolean,
        default: false
    },
    openMenuId: {
        type: String,
        default: null
    }
})

const emit = defineEmits(['select', 'archive', 'show-scheduler', 'renamed', 'menu-open', 'menu-close'])

const isEditing = ref(false)
const editName = ref('')
const editInput = ref(null)
const mobileItemRef = ref(null)

// Menu state for mobile - computed from parent's openMenuId
const menuOpen = computed(() => props.openMenuId === props.conv.id)

const toggleMenu = () => {
    if (menuOpen.value) {
        emit('menu-close')
    } else {
        emit('menu-open', props.conv.id)
    }
}

const closeMenu = () => {
    emit('menu-close')
}

// Close menu when clicking elsewhere
const handleDocumentClick = (e) => {
    if (menuOpen.value && mobileItemRef.value && !mobileItemRef.value.contains(e.target)) {
        closeMenu()
    }
}

onMounted(() => {
    if (props.isMobile) {
        document.addEventListener('click', handleDocumentClick)
    }
})

onUnmounted(() => {
    document.removeEventListener('click', handleDocumentClick)
})

// Handle mobile click - select conversation
const handleMobileClick = () => {
    if (isEditing.value || menuOpen.value) {
        return
    }
    emit('select', props.conv.id)
}

// Handle archive from menu
const handleArchive = () => {
    closeMenu()
    emit('archive', props.conv.id)
}

// Relative time calculation
const relativeTime = computed(() => {
    const timestamp = props.conv.last_user_message_at || props.conv.last_message_at
    if (!timestamp) return ''

    const now = new Date()
    const date = new Date(timestamp)
    const diffMs = now - date
    const diffMins = Math.floor(diffMs / 60000)
    const diffHours = Math.floor(diffMs / 3600000)
    const diffDays = Math.floor(diffMs / 86400000)

    if (diffMins < 1) return t('time.now')
    if (diffMins < 60) return t('time.minutes', { n: diffMins })
    if (diffHours < 24) return t('time.hours', { n: diffHours })
    if (diffDays === 1) return t('time.yesterday')
    if (diffDays < 7) return t('time.days', { n: diffDays })

    // For older dates, show short date
    return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
})

const startRename = () => {
    closeMenu()
    editName.value = props.conv.preview || ''
    isEditing.value = true
    nextTick(() => {
        editInput.value?.focus()
        editInput.value?.select()
    })
}

const cancelRename = () => {
    isEditing.value = false
    editName.value = ''
}

const saveRename = async () => {
    const newName = editName.value.trim()
    if (!newName) {
        cancelRename()
        return
    }

    try {
        await api.renameConversation(props.conv.id, newName)
        // Update local state immediately for responsive UI
        props.conv.preview = newName
        emit('renamed', props.conv.id, newName)
    } catch (e) {
        console.error('Failed to rename conversation:', e)
    }

    isEditing.value = false
    editName.value = ''
}
</script>

<style scoped>
/* Desktop action buttons */
.archive-conv-btn,
.rename-conv-btn,
.scheduler-info-btn {
    color: #71717a;
    opacity: 0;
    transition: all 0.15s ease;
}

.archive-conv-btn:hover {
    color: #f59e0b;
}

.rename-conv-btn:hover {
    color: #3b82f6;
}

.scheduler-info-btn:hover {
    color: #22d3ee;
}

.sidebar-item:hover .archive-conv-btn,
.sidebar-item:hover .rename-conv-btn,
.sidebar-item:hover .scheduler-info-btn {
    opacity: 1;
}

/* On mobile/touch devices, always show buttons (desktop only - mobile uses swipe) */
@media (hover: none) {
    .archive-conv-btn,
    .rename-conv-btn,
    .scheduler-info-btn {
        opacity: 1;
    }
}

/* === Mobile conversation item styles === */
.conv-item-mobile {
    position: relative;
    border-radius: 12px;
    margin-bottom: 4px;
    display: flex;
    align-items: center;
}

.conv-item-mobile .item-content {
    display: flex;
    flex-direction: column;
    flex: 1;
    min-width: 0;
    padding: 10px 12px;
    padding-right: 36px;
    background: var(--bg-surface);
    border-radius: 12px;
}

.conv-item-mobile .line-1 {
    display: flex;
    align-items: center;
    gap: 8px;
}

/* Status dot - only for active/pending states */
.conv-item-mobile .status-dot {
    position: relative;
    flex-shrink: 0;
    width: 10px;
    height: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
}

.conv-item-mobile .title {
    flex: 1;
    font-weight: 500;
    font-size: 13px;
    color: var(--text-primary);
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.conv-item-mobile .unread-badge {
    flex-shrink: 0;
    min-width: 18px;
    height: 16px;
    padding: 0 5px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 8px;
    background: #2563eb;
    color: white;
    font-size: 10px;
    font-weight: 600;
    margin-left: 6px;
}

/* 3-dot menu button */
.conv-item-mobile .menu-button {
    position: absolute;
    right: 4px;
    top: 50%;
    transform: translateY(-50%);
    padding: 6px;
    border-radius: 8px;
    color: var(--text-secondary);
    background: transparent;
    border: none;
    cursor: pointer;
    transition: all 0.15s ease;
    z-index: 2;
}

.conv-item-mobile .menu-button:hover,
.conv-item-mobile .menu-button.menu-open {
    color: var(--text-primary);
    background: var(--bg-elevated);
}

/* Dropdown menu */
.conv-item-mobile .dropdown-menu {
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
    min-width: 180px;
    overflow: hidden;
}

.conv-item-mobile .dropdown-menu button {
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

.conv-item-mobile .dropdown-menu button:hover {
    background: var(--bg-elevated);
}

.conv-item-mobile .dropdown-menu button.archive-action {
    color: #f59e0b;
}

.conv-item-mobile .dropdown-menu button.archive-action:hover {
    background: rgba(245, 158, 11, 0.15);
}

/* Active/selected state for mobile */
.conv-item-mobile.active .item-content {
    background: rgba(37, 99, 235, 0.12);
}

/* Mobile rename overlay */
.conv-item-mobile .rename-overlay {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 12px;
    background: var(--bg-surface);
    z-index: 10;
}

.conv-item-mobile .rename-input {
    flex: 1;
    min-width: 0;
    padding: 8px 12px;
    background: var(--bg-base);
    border: 1px solid var(--border-subtle);
    border-radius: 8px;
    font-size: 14px;
    color: var(--text-primary);
    outline: none;
}

.conv-item-mobile .rename-input:focus {
    border-color: #2563eb;
}

.conv-item-mobile .rename-save {
    padding: 8px;
    border-radius: 8px;
    background: #10b981;
    color: white;
    border: none;
    cursor: pointer;
}

.conv-item-mobile .rename-cancel {
    padding: 8px;
    border-radius: 8px;
    background: var(--bg-elevated);
    color: var(--text-secondary);
    border: none;
    cursor: pointer;
}

/* Light theme adjustments */
[data-theme="light"] .conv-item-mobile .item-content {
    background: var(--bg-base);
}

[data-theme="light"] .conv-item-mobile.active .item-content {
    background: rgba(79, 70, 229, 0.08);
}

[data-theme="light"] .conv-item-mobile .rename-overlay {
    background: var(--bg-base);
}

[data-theme="light"] .conv-item-mobile .dropdown-menu {
    background: white;
    border: 1px solid rgba(79, 70, 229, 0.3);
    box-shadow:
        0 4px 16px rgba(0,0,0,0.12),
        0 0 20px rgba(79, 70, 229, 0.1);
}
</style>
