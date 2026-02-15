<template>
    <div class="min-h-screen flex items-center justify-center bg-[var(--bg-base)] p-4">
        <div class="w-full max-w-md">
            <div class="text-center mb-8">
                <h1 class="text-3xl font-bold text-[var(--text-primary)] mb-2">ZENO</h1>
                <p class="text-[var(--text-secondary)]">{{ $t('auth.loginSubtitle') }}</p>
            </div>

            <div class="bg-[var(--bg-elevated)] rounded-2xl p-6 border border-[var(--border-subtle)]">
                <div class="space-y-4">
                    <!-- Password Input -->
                    <div>
                        <label class="block text-sm font-medium text-[var(--text-secondary)] mb-2">
                            {{ $t('auth.password') }}
                        </label>
                        <input
                            ref="passwordInput"
                            v-model="password"
                            type="password"
                            :placeholder="$t('auth.passwordPlaceholder')"
                            class="w-full px-4 py-3 rounded-xl bg-[var(--bg-surface)] border border-[var(--border-subtle)] text-[var(--text-primary)] placeholder-[var(--text-muted)] focus:outline-none focus:border-blue-500/50 transition-colors"
                            @keydown.enter="submitLogin"
                        />
                    </div>

                    <!-- Error -->
                    <p v-if="error" class="text-sm text-red-400">{{ error }}</p>

                    <!-- Submit -->
                    <button
                        @click="submitLogin"
                        :disabled="!password.trim() || isSubmitting"
                        class="w-full py-3 px-4 rounded-xl text-sm font-medium transition-all bg-blue-500 hover:bg-blue-600 text-white disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        <span v-if="isSubmitting">{{ $t('common.loading') }}</span>
                        <span v-else>{{ $t('auth.login') }}</span>
                    </button>
                </div>
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'

const emit = defineEmits(['authenticated'])
const { t } = useI18n()

const password = ref('')
const error = ref('')
const isSubmitting = ref(false)
const passwordInput = ref(null)

const submitLogin = async () => {
    if (!password.value.trim()) return

    isSubmitting.value = true
    error.value = ''

    try {
        const res = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ password: password.value })
        })

        if (res.status === 401) {
            error.value = t('auth.invalidPassword')
            return
        }

        if (!res.ok) {
            const data = await res.json()
            error.value = data.detail || 'Login failed'
            return
        }

        emit('authenticated')
    } catch (e) {
        error.value = t('errors.serverUnavailable.message')
    } finally {
        isSubmitting.value = false
    }
}

onMounted(() => {
    passwordInput.value?.focus()
})
</script>
