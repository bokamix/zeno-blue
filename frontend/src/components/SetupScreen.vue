<template>
    <div class="min-h-screen flex items-center justify-center bg-[var(--bg-base)] p-4">
        <div class="w-full max-w-md">
            <div class="text-center mb-8">
                <h1 class="text-3xl font-bold text-[var(--text-primary)] mb-2">ZENO</h1>
                <p class="text-[var(--text-secondary)]">{{ $t('setup.subtitle') }}</p>
            </div>

            <div class="bg-[var(--bg-elevated)] rounded-2xl p-6 border border-[var(--border-subtle)]">
                <div class="space-y-4">
                    <!-- Provider Selection -->
                    <div>
                        <label class="block text-sm font-medium text-[var(--text-secondary)] mb-2">
                            {{ $t('setup.provider') }}
                        </label>
                        <div class="flex gap-2">
                            <button
                                @click="provider = 'anthropic'"
                                class="flex-1 py-3 px-4 rounded-xl text-sm font-medium transition-all border"
                                :class="provider === 'anthropic'
                                    ? 'bg-blue-500/20 border-blue-500/40 text-blue-400'
                                    : 'bg-[var(--bg-surface)] border-[var(--border-subtle)] text-[var(--text-secondary)] hover:border-[var(--border-default)]'"
                            >
                                Anthropic
                            </button>
                            <button
                                @click="provider = 'openai'"
                                class="flex-1 py-3 px-4 rounded-xl text-sm font-medium transition-all border"
                                :class="provider === 'openai'
                                    ? 'bg-emerald-500/20 border-emerald-500/40 text-emerald-400'
                                    : 'bg-[var(--bg-surface)] border-[var(--border-subtle)] text-[var(--text-secondary)] hover:border-[var(--border-default)]'"
                            >
                                OpenAI
                            </button>
                        </div>
                    </div>

                    <!-- API Key Input -->
                    <div>
                        <label class="block text-sm font-medium text-[var(--text-secondary)] mb-2">
                            {{ $t('setup.apiKey') }}
                        </label>
                        <input
                            v-model="apiKey"
                            type="password"
                            :placeholder="provider === 'anthropic' ? 'sk-ant-...' : 'sk-proj-...'"
                            class="w-full px-4 py-3 rounded-xl bg-[var(--bg-surface)] border border-[var(--border-subtle)] text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:border-blue-500/50 transition-colors"
                            @keydown.enter="submitSetup"
                        />
                    </div>

                    <!-- Access Password (optional) -->
                    <div>
                        <label class="block text-sm font-medium text-[var(--text-secondary)] mb-2">
                            {{ $t('setup.accessPassword') }}
                        </label>
                        <input
                            v-model="accessPassword"
                            type="password"
                            :placeholder="$t('setup.accessPasswordPlaceholder')"
                            class="w-full px-4 py-3 rounded-xl bg-[var(--bg-surface)] border border-[var(--border-subtle)] text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:border-blue-500/50 transition-colors"
                        />
                        <input
                            v-if="accessPassword"
                            v-model="accessPasswordConfirm"
                            type="password"
                            :placeholder="$t('setup.accessPasswordConfirm')"
                            class="w-full mt-2 px-4 py-3 rounded-xl bg-[var(--bg-surface)] border border-[var(--border-subtle)] text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:border-blue-500/50 transition-colors"
                            @keydown.enter="submitSetup"
                        />
                        <p class="text-xs text-[var(--text-muted)] mt-1">{{ $t('setup.accessPasswordHint') }}</p>
                    </div>

                    <!-- Error -->
                    <p v-if="error" class="text-sm text-red-400">{{ error }}</p>

                    <!-- Submit -->
                    <button
                        @click="submitSetup"
                        :disabled="!apiKey.trim() || isSubmitting"
                        class="w-full py-3 px-4 rounded-xl text-sm font-medium transition-all bg-blue-500 hover:bg-blue-600 text-white disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        <span v-if="isSubmitting">{{ $t('setup.saving') }}</span>
                        <span v-else>{{ $t('setup.start') }}</span>
                    </button>
                </div>
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'

const emit = defineEmits(['complete'])
const { t } = useI18n()

const provider = ref('anthropic')
const apiKey = ref('')
const accessPassword = ref('')
const accessPasswordConfirm = ref('')
const error = ref('')
const isSubmitting = ref(false)

const submitSetup = async () => {
    if (!apiKey.value.trim()) return

    // Validate password confirmation
    if (accessPassword.value && accessPassword.value !== accessPasswordConfirm.value) {
        error.value = t('setup.passwordMismatch')
        return
    }

    isSubmitting.value = true
    error.value = ''

    try {
        const payload = {
            provider: provider.value,
            api_key: apiKey.value.trim()
        }
        if (accessPassword.value.trim()) {
            payload.password = accessPassword.value.trim()
        }

        const res = await fetch('/setup', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        })

        if (!res.ok) {
            const data = await res.json()
            error.value = data.detail || 'Setup failed'
            return
        }

        emit('complete')
    } catch (e) {
        error.value = 'Connection error. Is the server running?'
    } finally {
        isSubmitting.value = false
    }
}
</script>
