<template>
    <div class="notion-editor flex flex-col h-full">
        <!-- Loading state -->
        <div v-if="loading" class="flex items-center justify-center h-64">
            <span class="text-[var(--text-muted)]">Loading...</span>
        </div>

        <template v-else>
            <!-- Toolbar -->
            <div class="toolbar sticky top-0 z-10 flex items-center gap-1 p-2 bg-[var(--bg-surface)] border-b border-[var(--border-subtle)] rounded-t-lg flex-wrap">
                <button
                    @click="editor?.chain().focus().toggleBold().run()"
                    :class="{ 'bg-[var(--bg-elevated)]': editor?.isActive('bold') }"
                    class="toolbar-btn"
                    title="Bold (Ctrl+B)"
                >
                    <strong>B</strong>
                </button>
                <button
                    @click="editor?.chain().focus().toggleItalic().run()"
                    :class="{ 'bg-[var(--bg-elevated)]': editor?.isActive('italic') }"
                    class="toolbar-btn"
                    title="Italic (Ctrl+I)"
                >
                    <em>I</em>
                </button>
                <button
                    @click="editor?.chain().focus().toggleStrike().run()"
                    :class="{ 'bg-[var(--bg-elevated)]': editor?.isActive('strike') }"
                    class="toolbar-btn"
                    title="Strikethrough"
                >
                    <s>S</s>
                </button>

                <div class="w-px h-5 bg-[var(--border-subtle)] mx-1"></div>

                <button
                    @click="editor?.chain().focus().toggleHeading({ level: 1 }).run()"
                    :class="{ 'bg-[var(--bg-elevated)]': editor?.isActive('heading', { level: 1 }) }"
                    class="toolbar-btn"
                    title="Heading 1"
                >
                    H1
                </button>
                <button
                    @click="editor?.chain().focus().toggleHeading({ level: 2 }).run()"
                    :class="{ 'bg-[var(--bg-elevated)]': editor?.isActive('heading', { level: 2 }) }"
                    class="toolbar-btn"
                    title="Heading 2"
                >
                    H2
                </button>
                <button
                    @click="editor?.chain().focus().toggleHeading({ level: 3 }).run()"
                    :class="{ 'bg-[var(--bg-elevated)]': editor?.isActive('heading', { level: 3 }) }"
                    class="toolbar-btn"
                    title="Heading 3"
                >
                    H3
                </button>

                <div class="w-px h-5 bg-[var(--border-subtle)] mx-1"></div>

                <button
                    @click="editor?.chain().focus().toggleBulletList().run()"
                    :class="{ 'bg-[var(--bg-elevated)]': editor?.isActive('bulletList') }"
                    class="toolbar-btn"
                    title="Bullet List"
                >
                    &#8226; List
                </button>
                <button
                    @click="editor?.chain().focus().toggleOrderedList().run()"
                    :class="{ 'bg-[var(--bg-elevated)]': editor?.isActive('orderedList') }"
                    class="toolbar-btn"
                    title="Numbered List"
                >
                    1. List
                </button>
                <button
                    @click="editor?.chain().focus().toggleBlockquote().run()"
                    :class="{ 'bg-[var(--bg-elevated)]': editor?.isActive('blockquote') }"
                    class="toolbar-btn"
                    title="Quote"
                >
                    &ldquo; Quote
                </button>

                <div class="w-px h-5 bg-[var(--border-subtle)] mx-1"></div>

                <button
                    @click="editor?.chain().focus().toggleCode().run()"
                    :class="{ 'bg-[var(--bg-elevated)]': editor?.isActive('code') }"
                    class="toolbar-btn"
                    title="Inline Code"
                >
                    &lt;/&gt;
                </button>
                <button
                    @click="editor?.chain().focus().toggleCodeBlock().run()"
                    :class="{ 'bg-[var(--bg-elevated)]': editor?.isActive('codeBlock') }"
                    class="toolbar-btn"
                    title="Code Block"
                >
                    Code
                </button>

                <div class="w-px h-5 bg-[var(--border-subtle)] mx-1"></div>

                <button
                    @click="editor?.chain().focus().setHorizontalRule().run()"
                    class="toolbar-btn"
                    title="Horizontal Rule"
                >
                    &#8212;
                </button>

                <!-- Spacer -->
                <div class="flex-1"></div>

                <!-- Save indicator + button -->
                <span v-if="hasChanges" class="text-xs text-amber-400 mr-3">
                    Unsaved changes
                </span>
                <span v-else-if="saved" class="text-xs text-green-400 mr-3">
                    Saved
                </span>
                <button
                    @click="handleSave"
                    :disabled="saving || !hasChanges"
                    class="px-3 py-1 text-sm text-white bg-blue-600 hover:bg-blue-500 disabled:bg-[var(--bg-elevated)] disabled:text-[var(--text-muted)] disabled:cursor-not-allowed rounded transition-colors"
                    title="Save (Ctrl+S)"
                >
                    {{ saving ? 'Saving...' : 'Save' }}
                </button>
            </div>

            <!-- Editor content -->
            <div class="editor-wrapper flex-1 overflow-auto bg-[var(--bg-base)] rounded-b-lg">
                <EditorContent
                    :editor="editor"
                    class="editor-content p-6 min-h-[400px]"
                />
            </div>

            <!-- Close button -->
            <div class="actions flex items-center justify-end mt-4">
                <button
                    @click="handleCancel"
                    class="px-4 py-2 text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)] bg-[var(--bg-surface)] hover:bg-[var(--bg-elevated)] rounded-lg transition-colors"
                >
                    Close
                </button>
            </div>
        </template>
    </div>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import { useEditor, EditorContent } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import Placeholder from '@tiptap/extension-placeholder'
import { Markdown } from 'tiptap-markdown'

const props = defineProps({
    url: { type: String, required: true },
    filePath: { type: String, required: true },
    isMarkdown: { type: Boolean, default: true }
})

const emit = defineEmits(['close', 'saved'])

const loading = ref(true)
const saving = ref(false)
const saved = ref(false)
const hasChanges = ref(false)
const originalContent = ref('')

// Initialize editor
const editor = useEditor({
    extensions: [
        StarterKit.configure({
            heading: { levels: [1, 2, 3] }
        }),
        Placeholder.configure({
            placeholder: 'Start typing...'
        }),
        Markdown.configure({
            html: true,
            tightLists: true,
            bulletListMarker: '-',
            linkify: true,
            breaks: true
        })
    ],
    editorProps: {
        attributes: {
            class: 'prose max-w-none focus:outline-none'
        }
    },
    onUpdate: () => {
        hasChanges.value = true
        saved.value = false
    }
})

// Load content
onMounted(async () => {
    try {
        const res = await fetch(props.url)
        const text = await res.text()
        originalContent.value = text

        if (editor.value) {
            if (props.isMarkdown) {
                // Import markdown
                editor.value.commands.setContent(text)
            } else {
                // Plain text - escape HTML special characters and convert newlines
                const escapedText = text
                    .replace(/&/g, '&amp;')
                    .replace(/</g, '&lt;')
                    .replace(/>/g, '&gt;')
                    .replace(/\n/g, '<br>')
                editor.value.commands.setContent(`<p>${escapedText}</p>`)
            }
            // Reset change tracking after initial load
            hasChanges.value = false
        }
    } catch (e) {
        console.error('Failed to load file:', e)
        if (editor.value) {
            editor.value.commands.setContent('<p><em>Failed to load file</em></p>')
        }
    } finally {
        loading.value = false
    }
})

// Clean up editor
onBeforeUnmount(() => {
    editor.value?.destroy()
})

// Get content as markdown or plain text
function getContent() {
    if (!editor.value) return ''

    if (props.isMarkdown) {
        // Export as markdown
        return editor.value.storage.markdown.getMarkdown()
    } else {
        // Export as plain text
        return editor.value.getText()
    }
}

// Save handler
async function handleSave() {
    if (!hasChanges.value || saving.value) return

    saving.value = true

    try {
        const content = getContent()

        const res = await fetch('/artifacts/content', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                path: props.filePath,
                content: content
            })
        })

        if (!res.ok) {
            const error = await res.json()
            throw new Error(error.detail || 'Save failed')
        }

        hasChanges.value = false
        saved.value = true
        originalContent.value = content
        emit('saved')

        // Clear saved indicator after 2s
        setTimeout(() => {
            saved.value = false
        }, 2000)

    } catch (e) {
        console.error('Save failed:', e)
        alert('Failed to save: ' + e.message)
    } finally {
        saving.value = false
    }
}

// Cancel handler with unsaved changes warning
function handleCancel() {
    if (hasChanges.value) {
        if (!confirm('You have unsaved changes. Are you sure you want to close?')) {
            return
        }
    }
    emit('close')
}

// Keyboard shortcuts
function handleKeydown(e) {
    // Ctrl/Cmd + S to save
    if ((e.ctrlKey || e.metaKey) && e.key === 's') {
        e.preventDefault()
        handleSave()
    }
    // Escape to cancel
    if (e.key === 'Escape') {
        e.preventDefault()
        handleCancel()
    }
}

onMounted(() => {
    document.addEventListener('keydown', handleKeydown)
})

onBeforeUnmount(() => {
    document.removeEventListener('keydown', handleKeydown)
})
</script>

<style>
.toolbar-btn {
    @apply px-2 py-1 text-sm rounded transition-colors;
    color: var(--text-secondary);
}
.toolbar-btn:hover {
    color: var(--text-primary);
    background: var(--bg-elevated);
}

.editor-content .ProseMirror {
    @apply min-h-[400px] outline-none;
    color: var(--text-primary);
}

.editor-content .ProseMirror p.is-editor-empty:first-child::before {
    @apply float-left h-0 pointer-events-none;
    color: var(--text-muted);
    content: attr(data-placeholder);
}

/* Headings */
.editor-content .ProseMirror h1,
.editor-content .ProseMirror h2,
.editor-content .ProseMirror h3 {
    color: var(--text-primary);
}

/* Paragraphs */
.editor-content .ProseMirror p {
    color: var(--text-secondary);
}

/* Code block styling */
.editor-content .ProseMirror pre {
    @apply rounded-lg p-4 font-mono text-sm overflow-x-auto;
    background: var(--bg-surface);
}

.editor-content .ProseMirror pre code {
    @apply bg-transparent p-0;
}

/* Inline code */
.editor-content .ProseMirror code {
    @apply px-1.5 py-0.5 rounded font-mono text-sm;
    background: var(--bg-surface);
    color: var(--accent-tertiary);
}

/* Blockquote */
.editor-content .ProseMirror blockquote {
    @apply border-l-4 pl-4 italic;
    border-color: var(--border-subtle);
    color: var(--text-muted);
}

/* Lists */
.editor-content .ProseMirror ul,
.editor-content .ProseMirror ol {
    @apply pl-6;
}

.editor-content .ProseMirror li {
    color: var(--text-secondary);
}

/* Horizontal rule */
.editor-content .ProseMirror hr {
    @apply my-4;
    border-color: var(--border-subtle);
}

/* Strong/Bold */
.editor-content .ProseMirror strong {
    color: var(--text-primary);
}
</style>
