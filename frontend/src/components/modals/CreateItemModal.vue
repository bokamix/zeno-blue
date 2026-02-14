<template>
    <div
        class="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
        @click.self="$emit('cancel')"
    >
        <div class="glass-solid rounded-2xl p-6 max-w-sm w-full animate-modal-enter">
            <h3 class="text-lg font-semibold text-[var(--text-primary)] mb-4">
                {{ modalTitle }}
            </h3>

            <input
                ref="inputRef"
                v-model="name"
                type="text"
                :placeholder="mode === 'folder' ? $t('sidebar.folderNamePlaceholder') : $t('sidebar.fileNamePlaceholder')"
                class="w-full px-4 py-3 bg-[var(--bg-input)] border border-[var(--border-subtle)] rounded-xl text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500"
                @keyup.enter="handleSubmit"
                @keyup.escape="$emit('cancel')"
            />

            <p v-if="mode === 'file'" class="mt-2 text-xs text-[var(--text-muted)]">
                {{ $t('sidebar.fileNameHint') }}
            </p>

            <p v-if="error" class="mt-2 text-xs text-red-400">
                {{ error }}
            </p>

            <div class="flex justify-end gap-3 mt-6">
                <button
                    @click="$emit('cancel')"
                    class="px-4 py-2.5 text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-white/10 rounded-xl transition-all"
                >
                    {{ $t('common.cancel') }}
                </button>
                <button
                    @click="handleSubmit"
                    :disabled="!isValid"
                    class="px-5 py-2.5 text-sm bg-gradient-to-r from-blue-600 to-blue-500 text-white rounded-xl
                           shadow-lg shadow-blue-500/25 hover:shadow-blue-500/40 hover:scale-105 transition-all font-medium
                           disabled:opacity-50 disabled:cursor-not-allowed disabled:hover:scale-100"
                >
                    {{ mode === 'rename' ? $t('common.save') : $t('common.create') }}
                </button>
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const props = defineProps({
    mode: {
        type: String,
        default: 'folder',
        validator: (value) => ['folder', 'file', 'rename'].includes(value)
    },
    initialValue: {
        type: String,
        default: ''
    }
})

const emit = defineEmits(['cancel', 'create', 'rename'])

const inputRef = ref(null)
const name = ref(props.initialValue)
const error = ref('')

const modalTitle = computed(() => {
    if (props.mode === 'rename') return t('sidebar.renameFile')
    if (props.mode === 'folder') return t('sidebar.createFolder')
    return t('sidebar.createFile')
})

// Validation: no slashes allowed
const isValid = computed(() => {
    const trimmed = name.value.trim()
    if (!trimmed) return false
    if (trimmed.includes('/') || trimmed.includes('\\')) {
        error.value = 'Name cannot contain / or \\'
        return false
    }
    error.value = ''
    return true
})

const handleSubmit = () => {
    if (!isValid.value) return
    if (props.mode === 'rename') {
        emit('rename', name.value.trim())
    } else {
        emit('create', name.value.trim())
    }
}

onMounted(() => {
    // Auto-focus the input and select filename without extension for rename
    if (inputRef.value) {
        inputRef.value.focus()
        if (props.mode === 'rename' && props.initialValue) {
            const dotIndex = props.initialValue.lastIndexOf('.')
            if (dotIndex > 0) {
                inputRef.value.setSelectionRange(0, dotIndex)
            } else {
                inputRef.value.select()
            }
        }
    }
})
</script>
