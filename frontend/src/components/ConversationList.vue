<template>
    <div class="p-2">
        <!-- Today -->
        <template v-if="groupedConversations.today.length">
            <div class="date-separator">{{ $t('dates.today') }}</div>
            <ConversationItem
                v-for="conv in groupedConversations.today"
                :key="conv.id"
                :conv="conv"
                :is-active="conv.id === currentConversationId"
                :hide-active-indicator="hideActiveIndicator"
                :unread-count="conv.unread_count || 0"
                :is-mobile="isMobile"
                :open-menu-id="openMenuId"
                @select="$emit('select-conversation', $event)"
                @archive="$emit('archive-conversation', $event)"
                @show-scheduler="$emit('show-scheduler', $event)"
                @menu-open="handleMenuOpen"
                @menu-close="handleMenuClose"
            />
        </template>

        <!-- Yesterday -->
        <template v-if="groupedConversations.yesterday.length">
            <div class="date-separator">{{ $t('dates.yesterday') }}</div>
            <ConversationItem
                v-for="conv in groupedConversations.yesterday"
                :key="conv.id"
                :conv="conv"
                :is-active="conv.id === currentConversationId"
                :hide-active-indicator="hideActiveIndicator"
                :unread-count="conv.unread_count || 0"
                :is-mobile="isMobile"
                :open-menu-id="openMenuId"
                @select="$emit('select-conversation', $event)"
                @archive="$emit('archive-conversation', $event)"
                @show-scheduler="$emit('show-scheduler', $event)"
                @menu-open="handleMenuOpen"
                @menu-close="handleMenuClose"
            />
        </template>

        <!-- This week -->
        <template v-if="groupedConversations.thisWeek.length">
            <div class="date-separator">{{ $t('dates.thisWeek') }}</div>
            <ConversationItem
                v-for="conv in groupedConversations.thisWeek"
                :key="conv.id"
                :conv="conv"
                :is-active="conv.id === currentConversationId"
                :hide-active-indicator="hideActiveIndicator"
                :unread-count="conv.unread_count || 0"
                :is-mobile="isMobile"
                :open-menu-id="openMenuId"
                @select="$emit('select-conversation', $event)"
                @archive="$emit('archive-conversation', $event)"
                @show-scheduler="$emit('show-scheduler', $event)"
                @menu-open="handleMenuOpen"
                @menu-close="handleMenuClose"
            />
        </template>

        <!-- Older -->
        <template v-if="groupedConversations.older.length">
            <div class="date-separator">{{ $t('dates.older') }}</div>
            <ConversationItem
                v-for="conv in groupedConversations.older"
                :key="conv.id"
                :conv="conv"
                :is-active="conv.id === currentConversationId"
                :hide-active-indicator="hideActiveIndicator"
                :unread-count="conv.unread_count || 0"
                :is-mobile="isMobile"
                :open-menu-id="openMenuId"
                @select="$emit('select-conversation', $event)"
                @archive="$emit('archive-conversation', $event)"
                @show-scheduler="$emit('show-scheduler', $event)"
                @menu-open="handleMenuOpen"
                @menu-close="handleMenuClose"
            />
        </template>

        <!-- Empty state -->
        <div v-if="conversations.length === 0" class="px-4 py-6 text-xs text-zinc-600 text-center">
            {{ $t('sidebar.noConversations') }}
        </div>
    </div>
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted, inject } from 'vue'
import ConversationItem from './ConversationItem.vue'
import { useConversationGrouping } from '../composables/useConversationGrouping'

const props = defineProps({
    conversations: {
        type: Array,
        default: () => []
    },
    currentConversationId: {
        type: String,
        default: null
    }
})

// Hide active indicator when only 1 conversation
const hideActiveIndicator = computed(() => props.conversations.length <= 1)

defineEmits(['select-conversation', 'archive-conversation', 'show-scheduler'])

// Use global menu state (shared with files section)
const globalOpenMenuId = inject('globalOpenMenuId', ref(null))

// Computed to extract conversation id from global state (prefixed with 'conv:')
const openMenuId = computed(() => {
    const id = globalOpenMenuId.value
    if (id && id.startsWith('conv:')) {
        return id.slice(5) // Remove 'conv:' prefix
    }
    return null
})

const handleMenuOpen = (convId) => {
    globalOpenMenuId.value = `conv:${convId}`
}

const handleMenuClose = () => {
    globalOpenMenuId.value = null
}

// Mobile detection (< 768px = md breakpoint)
const isMobile = ref(false)
const checkMobile = () => {
    isMobile.value = window.innerWidth < 768
}

onMounted(() => {
    checkMobile()
    window.addEventListener('resize', checkMobile)
})

onUnmounted(() => {
    window.removeEventListener('resize', checkMobile)
})

// Group conversations by date
const { groupedConversations } = useConversationGrouping(() => props.conversations)
</script>
