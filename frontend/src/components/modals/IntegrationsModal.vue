<template>
    <div
        class="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
        @click.self="$emit('close')"
    >
        <div class="glass-solid rounded-3xl w-full max-w-lg max-h-[80vh] flex flex-col animate-modal-enter relative overflow-hidden">
            <!-- Gradient top accent -->
            <div class="absolute top-0 left-8 right-8 h-px bg-gradient-to-r from-transparent via-sky-500/50 to-transparent"></div>

            <!-- Modal Header -->
            <div class="flex items-center justify-between p-6 border-b border-white/5">
                <div class="flex items-center gap-3">
                    <div class="p-2 rounded-xl bg-gradient-to-br from-sky-500/20 to-purple-500/20">
                        <Plug class="w-5 h-5 text-sky-400" />
                    </div>
                    <h2 class="text-lg font-semibold text-[var(--text-primary)]">{{ $t('modals.integrations.title') }}</h2>
                </div>
                <button @click="$emit('close')" class="p-2 rounded-xl text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-surface)] transition-all">
                    <X class="w-5 h-5" />
                </button>
            </div>

            <!-- Modal Body -->
            <div class="flex-1 overflow-y-auto p-6 space-y-6 custom-scroll">
                <!-- Connected Services -->
                <div v-if="integrations.connected?.length > 0">
                    <h3 class="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-3">{{ $t('modals.integrations.connected') }}</h3>
                    <div class="space-y-2">
                        <div
                            v-for="service in integrations.connected"
                            :key="service.provider"
                            class="flex items-center justify-between bg-white/5 border border-white/5 rounded-xl p-4 hover:bg-white/[0.07] transition-colors"
                        >
                            <div class="flex items-center gap-3">
                                <div class="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500/20 to-green-500/20 flex items-center justify-center">
                                    <span class="text-emerald-400 font-semibold">{{ service.display_name?.[0] || service.provider[0].toUpperCase() }}</span>
                                </div>
                                <div>
                                    <p class="text-sm font-medium text-[var(--text-primary)]">{{ service.display_name || service.provider }}</p>
                                    <p v-if="service.account_email" class="text-xs text-zinc-500">{{ service.account_email }}</p>
                                </div>
                            </div>
                            <button
                                @click="disconnect(service.provider)"
                                class="text-xs text-zinc-500 hover:text-red-400 px-3 py-1.5 hover:bg-red-500/10 rounded-lg transition-all"
                            >
                                {{ $t('common.disconnect') }}
                            </button>
                        </div>
                    </div>
                </div>

                <!-- Available Services -->
                <div v-if="integrations.available?.length > 0">
                    <h3 class="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-3">{{ $t('modals.integrations.available') }}</h3>
                    <div class="space-y-2">
                        <div
                            v-for="service in integrations.available"
                            :key="service.name"
                            class="flex items-center justify-between bg-white/5 border border-white/5 rounded-xl p-4 hover:bg-white/[0.07] transition-colors"
                        >
                            <div class="flex items-center gap-3">
                                <div class="w-10 h-10 rounded-xl bg-white/5 flex items-center justify-center">
                                    <span class="text-zinc-400 font-semibold">{{ service.display_name?.[0] || service.name[0].toUpperCase() }}</span>
                                </div>
                                <p class="text-sm font-medium text-zinc-300">{{ service.display_name || service.name }}</p>
                            </div>
                            <button
                                @click="connect(service.name)"
                                class="text-xs bg-gradient-to-r from-blue-600 to-sky-600 text-white px-4 py-2 rounded-lg
                                       shadow-lg shadow-blue-500/20 hover:shadow-blue-500/30 hover:scale-105 transition-all"
                            >
                                {{ $t('common.connect') }}
                            </button>
                        </div>
                    </div>
                </div>

                <!-- Empty State -->
                <div v-if="!integrations.connected?.length && !integrations.available?.length" class="text-center py-12">
                    <div class="w-16 h-16 rounded-2xl bg-gradient-to-br from-sky-500/10 to-purple-500/10 flex items-center justify-center mx-auto mb-4">
                        <Plug class="w-8 h-8 text-sky-400/50" />
                    </div>
                    <p class="text-zinc-400">{{ $t('modals.integrations.noIntegrations') }}</p>
                    <p class="text-sm text-zinc-600 mt-1">{{ $t('modals.integrations.configureOAuth') }}</p>
                </div>
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { Plug, X } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'

const emit = defineEmits(['close'])
const { t } = useI18n()

const integrations = ref({ connected: [], available: [] })

const fetchIntegrations = async () => {
    try {
        const res = await fetch('/integrations')
        if (res.ok) {
            integrations.value = await res.json()
        }
    } catch (e) {
        console.error('Failed to fetch integrations', e)
    }
}

const connect = (provider) => {
    window.open(`/oauth/connect/${provider}`, 'oauth', 'width=500,height=600,popup=1')
}

const disconnect = async (provider) => {
    if (!confirm(t('confirmations.disconnectProvider', { provider }))) return
    try {
        await fetch(`/oauth/disconnect/${provider}`, { method: 'DELETE' })
        await fetchIntegrations()
    } catch (e) {
        console.error('Failed to disconnect integration', e)
    }
}

// Listen for OAuth completion from popup
const handleOAuthComplete = (event) => {
    if (event.data?.type === 'oauth_complete') {
        fetchIntegrations()
    }
}

// Handle OAuth completion from localStorage (for popup blocked scenarios)
const handleStorageEvent = (event) => {
    if (event.key !== 'oauth_complete') return

    try {
        const data = JSON.parse(event.newValue)
        if (data?.type === 'oauth_complete') {
            localStorage.removeItem('oauth_complete')
            handleOAuthComplete({ data })
        }
    } catch (e) {
        console.error('Error parsing oauth_complete from localStorage:', e)
    }
}

// Check localStorage on mount for OAuth completion
const checkPendingOAuthInStorage = () => {
    try {
        const stored = localStorage.getItem('oauth_complete')
        if (stored) {
            const data = JSON.parse(stored)
            if (data?.type === 'oauth_complete' && data.timestamp && (Date.now() - data.timestamp) < 30000) {
                localStorage.removeItem('oauth_complete')
                handleOAuthComplete({ data })
            } else {
                localStorage.removeItem('oauth_complete')
            }
        }
    } catch (e) {
        localStorage.removeItem('oauth_complete')
    }
}

onMounted(() => {
    fetchIntegrations()
    window.addEventListener('message', handleOAuthComplete)
    window.addEventListener('storage', handleStorageEvent)
    checkPendingOAuthInStorage()
})

onUnmounted(() => {
    window.removeEventListener('message', handleOAuthComplete)
    window.removeEventListener('storage', handleStorageEvent)
})
</script>
