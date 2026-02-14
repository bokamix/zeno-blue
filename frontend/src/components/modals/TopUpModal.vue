<template>
    <div
        class="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
        @click.self="$emit('close')"
    >
        <div class="glass-solid rounded-3xl w-full max-w-md animate-modal-enter relative flex flex-col overflow-hidden">
            <!-- Gradient top accent -->
            <div class="absolute top-0 left-8 right-8 h-px bg-gradient-to-r from-transparent via-emerald-500/50 to-transparent"></div>

            <!-- Modal Header -->
            <div class="flex-shrink-0 flex items-center justify-between p-6 border-b border-white/5">
                <div class="flex items-center gap-3">
                    <div class="p-2 rounded-xl bg-emerald-500/20">
                        <CreditCard class="w-5 h-5 text-emerald-400" />
                    </div>
                    <h2 class="text-lg font-semibold text-[var(--text-primary)]">{{ $t('topUp.title') }}</h2>
                </div>
                <button @click="$emit('close')" class="p-2 rounded-xl text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-surface)] transition-all">
                    <X class="w-5 h-5" />
                </button>
            </div>

            <!-- Modal Body -->
            <div class="p-6 space-y-6">
                <!-- Loading state -->
                <div v-if="isLoading" class="flex items-center justify-center py-8">
                    <Loader2 class="w-6 h-6 animate-spin text-emerald-400" />
                </div>

                <!-- Polar checkout -->
                <template v-else>
                    <p class="text-center text-[var(--text-secondary)]">
                        {{ $t('topUp.polarDescription') }}
                    </p>

                    <!-- Error message -->
                    <p v-if="error" class="text-sm text-red-400 bg-red-500/10 border border-red-500/20 rounded-xl p-3">
                        {{ error }}
                    </p>

                    <!-- Checkout Button -->
                    <button
                        @click="handleCheckout"
                        :disabled="isProcessing || !checkoutUrl"
                        class="w-full py-4 px-6 rounded-2xl font-semibold text-white transition-all flex items-center justify-center gap-2"
                        :class="isProcessing || !checkoutUrl
                            ? 'bg-zinc-600 cursor-not-allowed'
                            : 'bg-gradient-to-r from-emerald-500 to-green-500 hover:from-emerald-600 hover:to-green-600 shadow-lg shadow-emerald-500/20'"
                    >
                        <Loader2 v-if="isProcessing" class="w-5 h-5 animate-spin" />
                        <CreditCard v-else class="w-5 h-5" />
                        <span>{{ isProcessing ? $t('topUp.processing') : $t('topUp.goToCheckout') }}</span>
                    </button>

                    <!-- Polar Badge -->
                    <div class="flex items-center justify-center gap-2 text-xs text-zinc-500">
                        <Lock class="w-3.5 h-3.5" />
                        <span>{{ $t('topUp.securedByPolar') }}</span>
                    </div>
                </template>
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { CreditCard, X, Loader2, Lock } from 'lucide-vue-next'

const { t } = useI18n()
const emit = defineEmits(['close'])

const checkoutUrl = ref(null)
const isLoading = ref(true)
const isProcessing = ref(false)
const error = ref(null)

const fetchCheckoutUrl = async () => {
    try {
        // Use local proxy endpoint (user container proxies to central)
        const res = await fetch('/billing/checkout-url')
        if (res.ok) {
            const data = await res.json()
            checkoutUrl.value = data.checkout_url
        } else {
            error.value = t('topUp.loadError')
        }
    } catch (e) {
        console.error('Failed to fetch checkout URL:', e)
        error.value = t('topUp.loadError')
    } finally {
        isLoading.value = false
    }
}

const handleCheckout = () => {
    if (!checkoutUrl.value || isProcessing.value) return
    isProcessing.value = true
    window.location.href = checkoutUrl.value
}

onMounted(fetchCheckoutUrl)
</script>
