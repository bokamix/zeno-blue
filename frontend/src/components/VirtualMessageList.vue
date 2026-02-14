<template>
    <div
        ref="parentRef"
        class="h-full overflow-y-auto custom-scroll pb-4"
        @scroll="handleScroll"
    >
        <!-- Virtual list container -->
        <div
            :style="{ height: `${totalSize}px`, position: 'relative' }"
            class="max-w-3xl mx-auto px-4 md:px-6"
        >
            <!-- Virtual items -->
            <div
                v-for="virtualRow in virtualItems"
                :key="messages[virtualRow.index].id"
                :data-index="virtualRow.index"
                :ref="el => measureElement(el, virtualRow.index)"
                :style="{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    right: 0,
                    transform: `translateY(${virtualRow.start}px)`,
                    paddingLeft: 'inherit',
                    paddingRight: 'inherit'
                }"
                class="pb-8"
            >
                <!-- Unread separator - shows before first unread message -->
                <div
                    v-if="virtualRow.index === firstUnreadIndex"
                    class="unread-separator flex items-center gap-3 mb-6"
                >
                    <div class="flex-1 h-px bg-blue-500/40"></div>
                    <span class="text-xs font-medium text-blue-400 px-2">{{ $t('chat.newMessages') }}</span>
                    <div class="flex-1 h-px bg-blue-500/40"></div>
                </div>
                <ChatMessage
                    :message="messages[virtualRow.index]"
                    :message-id="messages[virtualRow.index].dbId"
                    @fork="$emit('fork', $event)"
                    @open-file="$emit('open-file', $event)"
                    @mark-unread="$emit('mark-unread', $event)"
                    @edit="$emit('edit', $event)"
                />
            </div>
        </div>

        <!-- Non-virtualized footer items (always rendered) -->
        <div class="max-w-3xl mx-auto px-4 md:px-6 pb-6">
            <slot name="footer"></slot>
        </div>
    </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick } from 'vue'
import { useVirtualizer } from '@tanstack/vue-virtual'
import ChatMessage from './ChatMessage.vue'

const props = defineProps({
    messages: { type: Array, required: true },
    isAtBottom: { type: Boolean, default: true },
    readAt: { type: String, default: null }
})

const emit = defineEmits(['fork', 'open-file', 'scroll', 'update:isAtBottom', 'mark-unread', 'edit'])

// Compute index of first unread message (only assistant messages count as "unread")
const firstUnreadIndex = computed(() => {
    if (!props.readAt) return -1
    // Find first assistant message with created_at > readAt
    const idx = props.messages.findIndex(m =>
        m.role === 'assistant' && m.created_at && m.created_at > props.readAt
    )
    return idx
})

const parentRef = ref(null)
const resizeObserver = ref(null)
const observedElements = new Map()

// Virtualizer setup with dynamic measurement
const virtualizerOptions = computed(() => ({
    count: props.messages.length,
    getScrollElement: () => parentRef.value,
    estimateSize: () => 150,
    overscan: 5,
    paddingStart: 64
}))

const virtualizer = useVirtualizer(virtualizerOptions)

const virtualItems = computed(() => virtualizer.value.getVirtualItems())
const totalSize = computed(() => virtualizer.value.getTotalSize())

// Measure element and observe for resize
const measureElement = (el, index) => {
    if (!el) {
        // Element unmounted, stop observing
        const oldEl = observedElements.get(index)
        if (oldEl && resizeObserver.value) {
            resizeObserver.value.unobserve(oldEl)
            observedElements.delete(index)
        }
        return
    }

    // Measure element
    virtualizer.value.measureElement(el)

    // Start observing for size changes (markdown rendering, images loading, etc.)
    if (resizeObserver.value && !observedElements.has(index)) {
        resizeObserver.value.observe(el)
        observedElements.set(index, el)
    }
}

// Scroll handling
const handleScroll = () => {
    if (!parentRef.value) return
    const { scrollTop, scrollHeight, clientHeight } = parentRef.value
    const isBottom = scrollTop + clientHeight >= scrollHeight - 100
    emit('update:isAtBottom', isBottom)
    emit('scroll')
}

// Scroll to bottom methods
const scrollToBottom = (smooth = false) => {
    if (!parentRef.value) return

    nextTick(() => {
        if (parentRef.value) {
            parentRef.value.scrollTo({
                top: parentRef.value.scrollHeight,
                behavior: smooth ? 'smooth' : 'instant'
            })
        }
    })
}

const scrollToBottomSmooth = () => scrollToBottom(true)

// Initial scroll to bottom when conversation is loaded/switched
watch(
    () => props.messages,
    (newMessages, oldMessages) => {
        // Only scroll on initial load or conversation switch (different first message = different conversation)
        const isConversationSwitch = newMessages.length > 0 &&
            (!oldMessages || oldMessages.length === 0 || newMessages[0]?.id !== oldMessages[0]?.id)

        if (isConversationSwitch) {
            // Use double nextTick + requestAnimationFrame to ensure virtualizer has rendered
            nextTick(() => {
                nextTick(() => {
                    requestAnimationFrame(() => {
                        scrollToBottom()
                    })
                })
            })
        }
    },
    { immediate: true }
)

// Setup ResizeObserver
onMounted(() => {
    resizeObserver.value = new ResizeObserver((entries) => {
        // Debounce measurements to avoid excessive recalculations
        for (const entry of entries) {
            const index = entry.target.dataset?.index
            if (index !== undefined) {
                virtualizer.value.measureElement(entry.target)
            }
        }
    })
})

// Cleanup
onUnmounted(() => {
    if (resizeObserver.value) {
        resizeObserver.value.disconnect()
        resizeObserver.value = null
    }
    observedElements.clear()
})

// Expose methods for parent component
defineExpose({
    scrollToBottom: () => scrollToBottom(false),
    scrollToBottomSmooth,
    parentRef
})
</script>
