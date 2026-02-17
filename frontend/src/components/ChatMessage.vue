<template>
    <!-- Question Message (ask_user) - Yellow Bubble -->
    <div v-if="isQuestionMessage" class="flex gap-4 mb-8 group">
        <!-- Question Avatar -->
        <div class="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-amber-400 to-orange-500 flex items-center justify-center shadow-lg shadow-amber-500/20">
            <HelpCircle class="w-4 h-4 text-white" />
        </div>
        <!-- Message Content -->
        <div class="flex-1 min-w-0">
            <div class="question-message-bubble bg-amber-50 dark:bg-amber-900/30 border border-amber-200 dark:border-amber-700 rounded-2xl rounded-tl-md px-5 py-3 shadow-md">
                <div class="question-message-text text-amber-800 dark:text-amber-200 text-[15px] leading-relaxed whitespace-pre-wrap break-anywhere">
                    {{ message.text }}
                </div>
                <!-- Options if present -->
                <div v-if="questionOptions?.length" class="flex flex-wrap gap-2 mt-3 pt-3 border-t border-amber-200 dark:border-amber-700">
                    <button
                        v-for="option in questionOptions"
                        :key="option"
                        @click="$emit('suggestion-select', option)"
                        class="question-option-tag px-3 py-1.5 text-xs font-medium rounded-full bg-amber-100 dark:bg-amber-800/50 text-amber-700 dark:text-amber-300 hover:bg-amber-200 dark:hover:bg-amber-700/50 transition-colors cursor-pointer"
                    >
                        {{ option }}
                    </button>
                </div>
            </div>

            <!-- Action buttons -->
            <div class="flex gap-1 mt-2 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                <button
                    @click="copyMessage"
                    class="p-1.5 rounded-md text-zinc-500 hover:text-zinc-300 hover:bg-white/5 transition-colors"
                    :title="copied ? 'Copied!' : 'Copy message'"
                >
                    <Check v-if="copied" class="w-3.5 h-3.5 text-emerald-400" />
                    <Copy v-else class="w-3.5 h-3.5" />
                </button>
            </div>
        </div>
    </div>

    <!-- User Message - Gradient Bubble -->
    <div v-else-if="message.role === 'user'" class="flex justify-end mb-8">
        <div class="max-w-[75%] relative group">
            <!-- Attachments cards (parsed from text or from attachments array) -->
            <div v-if="parsedAttachments.length" class="flex flex-wrap gap-2 mb-2 justify-end">
                <div
                    v-for="filePath in parsedAttachments"
                    :key="filePath"
                    @click.stop="$emit('open-file', filePath)"
                    class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg cursor-pointer transition-all text-xs font-medium"
                    :class="isImageFile(filePath)
                        ? 'bg-emerald-100 border border-emerald-300 hover:bg-emerald-200 text-emerald-800'
                        : 'bg-blue-100 border border-blue-300 hover:bg-blue-200 text-blue-800'"
                    :title="`Click to open ${getFileName(filePath)}`"
                >
                    <span>{{ isImageFile(filePath) ? '🖼️' : '📄' }}</span>
                    <span class="truncate max-w-[150px]">{{ getFileName(filePath) }}</span>
                </div>
            </div>

            <div
                class="bg-gradient-to-br from-blue-600 to-blue-700 text-white py-3 px-5 rounded-2xl rounded-br-md shadow-lg shadow-blue-500/20 text-[15px] leading-relaxed break-anywhere
                       prose prose-sm max-w-none prose-invert
                       prose-p:my-1 prose-p:text-white prose-headings:text-white prose-strong:text-white
                       prose-code:text-blue-200 prose-code:bg-white/10 prose-code:px-1 prose-code:py-0.5 prose-code:rounded
                       prose-pre:bg-black/20 prose-pre:border prose-pre:border-white/10 prose-pre:rounded-xl
                       prose-a:text-blue-200 prose-a:underline hover:prose-a:text-white
                       prose-ul:my-1 prose-ol:my-1 prose-li:my-0 prose-li:text-white"
                v-html="renderedUserContent"
            ></div>

            <!-- Action buttons -->
            <div class="flex justify-end gap-1 mt-1.5 opacity-0 group-hover:opacity-100 transition-opacity duration-200 relative z-10">
                <button
                    @click="$emit('edit', { id: messageId, text: message.text })"
                    class="p-1.5 rounded-md text-zinc-500 hover:text-zinc-300 hover:bg-white/5 transition-colors"
                    :title="t('chat.editMessage')"
                >
                    <Pencil class="w-3.5 h-3.5" />
                </button>
                <button
                    @click="copyMessage"
                    class="p-1.5 rounded-md text-zinc-500 hover:text-zinc-300 hover:bg-white/5 transition-colors"
                    :title="copied ? 'Copied!' : 'Copy message'"
                >
                    <Check v-if="copied" class="w-3.5 h-3.5 text-emerald-400" />
                    <Copy v-else class="w-3.5 h-3.5" />
                </button>
                <button
                    v-if="messageId"
                    @click="$emit('fork', messageId)"
                    class="p-1.5 rounded-md text-zinc-500 hover:text-zinc-300 hover:bg-white/5 transition-colors"
                    title="Fork conversation from here"
                >
                    <GitFork class="w-3.5 h-3.5" />
                </button>
            </div>
        </div>
    </div>

    <!-- AI Message -->
    <div v-else class="flex gap-4 mb-8 group">
        <!-- AI Avatar -->
        <div class="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center shadow-lg shadow-emerald-500/20">
            <Sparkles class="w-4 h-4 text-white" />
        </div>
        <!-- Message Content -->
        <div class="flex-1 min-w-0">
            <div
                class="prose prose-zinc max-w-none text-[15px] break-anywhere
                       prose-pre:bg-[var(--bg-surface)] prose-pre:border prose-pre:border-[var(--border-subtle)] prose-pre:rounded-xl prose-pre:overflow-x-auto
                       prose-code:text-cyan-600 dark:prose-code:text-cyan-400
                       prose-a:text-blue-600 dark:prose-a:text-blue-400 prose-a:no-underline hover:prose-a:underline prose-a:break-all
                       prose-strong:text-[var(--text-primary)] prose-headings:text-[var(--text-primary)]
                       prose-p:text-[var(--text-secondary)] prose-li:text-[var(--text-secondary)]"
                v-html="renderedContent"
            ></div>

            <!-- Action buttons -->
            <div class="flex gap-1 mt-2 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                <button
                    @click="copyMessage"
                    class="p-1.5 rounded-md text-zinc-500 hover:text-zinc-300 hover:bg-white/5 transition-colors"
                    :title="copied ? 'Copied!' : 'Copy message'"
                >
                    <Check v-if="copied" class="w-3.5 h-3.5 text-emerald-400" />
                    <Copy v-else class="w-3.5 h-3.5" />
                </button>
                <button
                    v-if="messageId"
                    @click="$emit('fork', messageId)"
                    class="p-1.5 rounded-md text-zinc-500 hover:text-zinc-300 hover:bg-white/5 transition-colors"
                    title="Fork conversation from here"
                >
                    <GitFork class="w-3.5 h-3.5" />
                </button>
                <button
                    v-if="message.created_at"
                    @click="$emit('mark-unread', message.created_at)"
                    class="p-1.5 rounded-md text-zinc-500 hover:text-zinc-300 hover:bg-white/5 transition-colors"
                    :title="t('chat.markUnread')"
                >
                    <MailOpen class="w-3.5 h-3.5" />
                </button>
            </div>

            <!-- Follow-up suggestions (persisted with message) -->
            <div v-if="messageSuggestions.length > 0" class="mt-4 pt-3 border-t border-[var(--border-subtle)]/30">
                <div class="flex flex-col gap-1">
                    <button
                        v-for="(suggestion, idx) in messageSuggestions"
                        :key="idx"
                        @click="$emit('suggestion-select', suggestion)"
                        class="flex items-start gap-2.5 px-2 py-2
                               text-sm text-[var(--text-secondary)]
                               hover:text-[var(--text-primary)]
                               hover:bg-[var(--bg-surface)]
                               rounded-lg
                               transition-all duration-200
                               text-left"
                    >
                        <CornerDownRight class="w-4 h-4 text-[var(--text-muted)] flex-shrink-0 mt-0.5" />
                        <span>{{ suggestion }}</span>
                    </button>
                </div>
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { Sparkles, GitFork, Copy, Check, MailOpen, Pencil, HelpCircle, CornerDownRight } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { useMarkdownRenderer, isImageFile, getFileName } from '../composables/useMarkdownRenderer'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import { ALL_FILE_EXTENSIONS } from '../composables/useFileDetection'

const { t } = useI18n()

const props = defineProps({
    message: {
        type: Object,
        required: true
    },
    messageId: {
        type: Number,
        default: null
    }
})

defineEmits(['fork', 'open-file', 'mark-unread', 'edit', 'suggestion-select'])

// Detect if this is a question message (ask_user)
const isQuestionMessage = computed(() => {
    return props.message.metadata?.type === 'question'
})

// Get question options from metadata
const questionOptions = computed(() => {
    return props.message.metadata?.options || []
})

// Get follow-up suggestions from metadata
const messageSuggestions = computed(() => {
    return props.message.metadata?.suggestions || []
})

// Use markdown renderer composable (with getter for reactivity)
const { renderedContent } = useMarkdownRenderer(() => props.message)

// Copy functionality
const copied = ref(false)

const copyMessage = async () => {
    try {
        await navigator.clipboard.writeText(props.message.text)
        copied.value = true
        setTimeout(() => {
            copied.value = false
        }, 2000)
    } catch (e) {
        console.error('Failed to copy:', e)
    }
}

// Regex that matches @filename.ext including filenames with spaces
// Matches: @anything.ext where ext is a known extension
const FILE_PATTERN = new RegExp(`@([^@]+?\\.(${ALL_FILE_EXTENSIONS.join('|')}))(?=\\s|$)`, 'gi')

// Extract attachments: use message.attachments if provided, otherwise parse from text
const parsedAttachments = computed(() => {
    if (props.message.role !== 'user') return []

    // If attachments array is provided (new messages), use it
    if (props.message.attachments?.length) {
        return props.message.attachments
    }

    // Otherwise, parse @filename patterns from text (loaded messages from DB)
    if (!props.message.text) return []

    const attachments = []
    let match

    // Reset regex lastIndex
    FILE_PATTERN.lastIndex = 0
    while ((match = FILE_PATTERN.exec(props.message.text)) !== null) {
        attachments.push(match[1])
    }

    return attachments
})

// Get clean text without @filename mentions
const cleanMessageText = computed(() => {
    if (props.message.role !== 'user' || !props.message.text) return props.message.text || ''

    // If attachments array is provided, text is already clean
    if (props.message.attachments?.length) {
        return props.message.text
    }

    // Otherwise, strip @filename patterns from text
    FILE_PATTERN.lastIndex = 0
    return props.message.text
        .replace(FILE_PATTERN, '')
        .trim()
})

// Render markdown for user messages
const renderedUserContent = computed(() => {
    const text = cleanMessageText.value
    if (!text) return ''

    try {
        let html = marked.parse(text, { breaks: true, gfm: true })
        // Add target="_blank" to all external links
        html = html.replace(/<a href="(https?:\/\/[^"]+)"/g, '<a target="_blank" rel="noopener noreferrer" href="$1"')
        return DOMPurify.sanitize(html, { ADD_ATTR: ['target', 'rel'] })
    } catch (e) {
        console.error('Markdown parse error:', e)
        return text
    }
})

</script>
