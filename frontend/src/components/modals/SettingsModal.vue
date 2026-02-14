<template>
    <div
        class="fixed inset-0 z-50"
        :class="[
            // Desktop: centered modal with backdrop
            'md:bg-black/60 md:backdrop-blur-sm md:flex md:items-center md:justify-center md:p-4',
            // Mobile: backdrop for tap-to-close
            'bg-black/30 backdrop-blur-sm',
            // Disable transition when dragging
            isDraggingSettings ? '' : 'transition-colors duration-300'
        ]"
        @click.self="$emit('close')"
    >
        <div
            class="glass-solid flex flex-col overflow-hidden"
            :class="[
                // Mobile (default): full-height panel sliding from RIGHT edge
                'fixed top-0 bottom-0 right-0 w-[calc(100vw-40px)] max-w-sm rounded-l-3xl rounded-tr-none rounded-br-none',
                // Desktop: centered modal (overrides mobile)
                'md:static md:rounded-3xl md:w-full md:max-w-md md:max-h-[calc(100dvh-2rem)] md:animate-modal-enter',
                // Animation
                isDraggingSettings ? '' : 'transition-transform duration-300'
            ]"
            :style="panelStyle"
        >
            <!-- Gradient top accent -->
            <div class="absolute top-0 left-8 right-8 h-px bg-gradient-to-r from-transparent via-zinc-500/50 to-transparent"></div>

            <!-- Modal Header -->
            <div class="flex-shrink-0 flex items-center justify-between p-6 border-b border-white/5">
                <div class="flex items-center gap-3">
                    <div class="p-2 rounded-xl bg-white/5">
                        <Settings class="w-5 h-5 text-zinc-400" />
                    </div>
                    <h2 class="text-lg font-semibold text-[var(--text-primary)]">{{ $t('modals.settings.title') }}</h2>
                </div>
                <button @click="$emit('close')" class="p-2 rounded-xl text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-surface)] transition-all">
                    <X class="w-5 h-5" />
                </button>
            </div>

            <!-- Modal Body -->
            <div class="p-6 space-y-6 overflow-y-auto">
                <!-- Preferences Section (Collapsible) -->
                <div class="border-b border-[var(--border-subtle)]">
                    <button
                        @click="settingsExpanded = !settingsExpanded"
                        class="w-full flex items-center justify-between py-3 text-left"
                    >
                        <div class="flex items-center gap-3">
                            <div class="p-2 rounded-lg bg-zinc-500/20">
                                <Settings class="w-4 h-4 text-zinc-400" />
                            </div>
                            <span class="text-sm text-[var(--text-primary)]">{{ $t('modals.settings.preferences') }}</span>
                        </div>
                        <ChevronDown
                            class="w-4 h-4 text-zinc-400 transition-transform"
                            :class="{ 'rotate-180': settingsExpanded }"
                        />
                    </button>

                    <div v-show="settingsExpanded" class="pl-4 pb-3 space-y-1">
                        <!-- Theme Toggle -->
                        <div class="flex items-center justify-between py-2">
                            <div class="flex items-center gap-3">
                                <div class="p-1.5 rounded-lg" :class="isDarkTheme ? 'bg-blue-500/20' : 'bg-amber-500/20'">
                                    <Moon v-if="isDarkTheme" class="w-3.5 h-3.5 text-blue-400" />
                                    <Sun v-else class="w-3.5 h-3.5 text-amber-500" />
                                </div>
                                <span class="text-sm text-[var(--text-secondary)]">{{ $t('modals.settings.theme') }}</span>
                            </div>
                            <button
                                @click="toggleTheme"
                                class="px-3 py-1.5 text-xs rounded-lg font-medium transition-all"
                                :class="isDarkTheme
                                    ? 'bg-white/10 text-zinc-300 hover:bg-white/20'
                                    : 'bg-amber-500/20 text-amber-600 hover:bg-amber-500/30'"
                            >
                                {{ isDarkTheme ? $t('modals.settings.themeDark') : $t('modals.settings.themeLight') }}
                            </button>
                        </div>

                        <!-- Sidebar Position Toggle -->
                        <div class="flex items-center justify-between py-2">
                            <div class="flex items-center gap-3">
                                <div class="p-1.5 rounded-lg" :class="sidebarPosition === 'left' ? 'bg-blue-500/20' : 'bg-sky-500/20'">
                                    <PanelLeft v-if="sidebarPosition === 'left'" class="w-3.5 h-3.5 text-blue-400" />
                                    <PanelRight v-else class="w-3.5 h-3.5 text-sky-400" />
                                </div>
                                <span class="text-sm text-[var(--text-secondary)]">{{ $t('modals.settings.sidebar') }}</span>
                            </div>
                            <button
                                @click="toggleSidebarPosition"
                                class="px-3 py-1.5 text-xs rounded-lg font-medium transition-all"
                                :class="sidebarPosition === 'left'
                                    ? 'bg-white/10 text-zinc-300 hover:bg-white/20'
                                    : 'bg-sky-500/20 text-sky-400 hover:bg-sky-500/30'"
                            >
                                {{ sidebarPosition === 'left' ? $t('modals.settings.sidebarLeft') : $t('modals.settings.sidebarRight') }}
                            </button>
                        </div>

                        <!-- Language Toggle -->
                        <div class="flex items-center justify-between py-2">
                            <div class="flex items-center gap-3">
                                <div class="p-1.5 rounded-lg bg-cyan-500/20">
                                    <Globe class="w-3.5 h-3.5 text-cyan-400" />
                                </div>
                                <span class="text-sm text-[var(--text-secondary)]">{{ $t('modals.settings.language') }}</span>
                            </div>
                            <button
                                @click="toggleLanguage"
                                class="px-3 py-1.5 text-xs rounded-lg font-medium transition-all bg-white/10 text-zinc-300 hover:bg-white/20"
                            >
                                {{ $t('language.' + currentLanguage) }}
                            </button>
                        </div>

                        <!-- Sound Notifications Toggle -->
                        <div class="flex items-center justify-between py-2">
                            <div class="flex items-center gap-3">
                                <div class="p-1.5 rounded-lg" :class="soundEnabled ? 'bg-green-500/20' : 'bg-zinc-500/20'">
                                    <Volume2 v-if="soundEnabled" class="w-3.5 h-3.5 text-green-400" />
                                    <VolumeX v-else class="w-3.5 h-3.5 text-zinc-400" />
                                </div>
                                <span class="text-sm text-[var(--text-secondary)]">{{ $t('modals.settings.soundNotifications') }}</span>
                            </div>
                            <button
                                @click="toggleSound"
                                class="px-3 py-1.5 text-xs rounded-lg font-medium transition-all"
                                :class="soundEnabled
                                    ? 'bg-green-500/20 text-green-400 hover:bg-green-500/30'
                                    : 'bg-white/10 text-zinc-300 hover:bg-white/20'"
                            >
                                {{ soundEnabled ? $t('modals.settings.soundOn') : $t('modals.settings.soundOff') }}
                            </button>
                        </div>

                        <!-- Model Provider Select -->
                        <div class="flex items-center justify-between py-2">
                            <div class="flex items-center gap-3">
                                <div class="p-1.5 rounded-lg" :class="modelProvider === 'anthropic' ? 'bg-orange-500/20' : 'bg-emerald-500/20'">
                                    <Cpu class="w-3.5 h-3.5" :class="modelProvider === 'anthropic' ? 'text-orange-400' : 'text-emerald-400'" />
                                </div>
                                <span class="text-sm text-[var(--text-secondary)]">{{ $t('modals.settings.modelProvider') }}</span>
                            </div>
                            <select
                                :value="modelProvider"
                                @change="handleModelProviderChange($event.target.value)"
                                :disabled="modelProviderLoading"
                                class="px-3 py-1.5 text-xs rounded-lg font-medium transition-all bg-[var(--bg-elevated)] text-[var(--text-secondary)] hover:bg-[var(--bg-surface)] border border-[var(--border-subtle)] outline-none cursor-pointer disabled:opacity-50 disabled:cursor-wait"
                            >
                                <option value="anthropic" class="bg-[var(--bg-elevated)] text-[var(--text-primary)]">Anthropic (Claude)</option>
                                <option value="openai" class="bg-[var(--bg-elevated)] text-[var(--text-primary)]">OpenAI (GPT)</option>
                            </select>
                        </div>
                        <!-- Model Provider Error -->
                        <p v-if="modelProviderError" class="text-xs text-red-400 mt-1 ml-9">{{ modelProviderError }}</p>
                    </div>
                </div>

                <!-- API Keys Section (Collapsible) -->
                <div class="border-b border-[var(--border-subtle)]">
                    <button
                        @click="apiKeysExpanded = !apiKeysExpanded; if (apiKeysExpanded) loadApiKeys()"
                        class="w-full flex items-center justify-between py-3 text-left"
                    >
                        <div class="flex items-center gap-3">
                            <div class="p-2 rounded-lg bg-violet-500/20">
                                <KeyRound class="w-4 h-4 text-violet-400" />
                            </div>
                            <span class="text-sm text-[var(--text-primary)]">{{ $t('modals.settings.apiKeys') }}</span>
                        </div>
                        <ChevronDown
                            class="w-4 h-4 text-zinc-400 transition-transform"
                            :class="{ 'rotate-180': apiKeysExpanded }"
                        />
                    </button>

                    <div v-show="apiKeysExpanded" class="pl-4 pb-3 space-y-2">
                        <!-- Status message -->
                        <p v-if="apiKeySaveStatus === 'success'" class="text-xs text-green-400 mb-1">{{ $t('modals.settings.apiKeySaved') }}</p>
                        <p v-if="apiKeySaveStatus === 'error'" class="text-xs text-red-400 mb-1">{{ $t('modals.settings.apiKeyError') }}</p>

                        <div v-for="keyDef in API_KEY_DEFS" :key="keyDef.name" class="py-2">
                            <div class="flex items-center justify-between">
                                <div class="flex items-center gap-3 min-w-0">
                                    <div class="p-1.5 rounded-lg" :class="keyDef.iconBg">
                                        <KeyRound class="w-3.5 h-3.5" :class="keyDef.iconText" />
                                    </div>
                                    <div class="min-w-0">
                                        <span class="text-sm text-[var(--text-secondary)] block">{{ $t('modals.settings.' + keyDef.label) }}</span>
                                        <span v-if="apiKeys[keyDef.name]?.configured && editingKey !== keyDef.name" class="text-xs text-zinc-500 font-mono">{{ apiKeys[keyDef.name]?.masked }}</span>
                                    </div>
                                </div>
                                <div class="flex items-center gap-2 flex-shrink-0">
                                    <span v-if="apiKeys[keyDef.name]?.configured && editingKey !== keyDef.name"
                                        class="px-2 py-0.5 text-[10px] rounded-full bg-green-500/20 text-green-400 font-medium">
                                        {{ $t('modals.settings.apiKeyConfigured') }}
                                    </span>
                                    <span v-else-if="!apiKeys[keyDef.name]?.configured && editingKey !== keyDef.name"
                                        class="px-2 py-0.5 text-[10px] rounded-full bg-zinc-500/20 text-zinc-400 font-medium">
                                        {{ $t('modals.settings.apiKeyNotSet') }}
                                    </span>
                                    <button v-if="editingKey !== keyDef.name"
                                        @click="startEditKey(keyDef.name)"
                                        class="px-2.5 py-1 text-xs rounded-lg font-medium transition-all bg-white/10 text-zinc-300 hover:bg-white/20">
                                        {{ apiKeys[keyDef.name]?.configured ? $t('modals.settings.apiKeyChange') : $t('modals.settings.apiKeySave') }}
                                    </button>
                                </div>
                            </div>
                            <!-- Edit mode -->
                            <div v-if="editingKey === keyDef.name" class="mt-2 flex gap-2">
                                <div class="relative flex-1">
                                    <input
                                        v-model="editKeyValue"
                                        :type="showKeyValue ? 'text' : 'password'"
                                        placeholder="sk-..."
                                        class="w-full px-3 py-1.5 text-xs rounded-lg bg-[var(--bg-elevated)] text-[var(--text-primary)] border border-[var(--border-subtle)] outline-none focus:border-violet-500/50 font-mono pr-8"
                                        @keydown.enter="handleSaveKey(keyDef.name)"
                                        @keydown.escape="cancelEditKey"
                                    />
                                    <button @click="showKeyValue = !showKeyValue" class="absolute right-2 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-300">
                                        <Eye v-if="!showKeyValue" class="w-3.5 h-3.5" />
                                        <EyeOff v-else class="w-3.5 h-3.5" />
                                    </button>
                                </div>
                                <button
                                    @click="handleSaveKey(keyDef.name)"
                                    :disabled="savingKey || !editKeyValue.trim()"
                                    class="px-3 py-1.5 text-xs rounded-lg font-medium transition-all bg-violet-500/20 text-violet-400 hover:bg-violet-500/30 disabled:opacity-50 disabled:cursor-not-allowed">
                                    {{ $t('modals.settings.apiKeySave') }}
                                </button>
                                <button
                                    @click="cancelEditKey"
                                    class="px-3 py-1.5 text-xs rounded-lg font-medium transition-all bg-white/10 text-zinc-300 hover:bg-white/20">
                                    {{ $t('common.cancel') }}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Help Button -->
                <button
                    @click="openCrispChat"
                    class="w-full flex items-center justify-between p-4 rounded-2xl bg-gradient-to-r from-blue-500/10 to-cyan-500/10 border border-blue-500/20 hover:border-blue-500/40 transition-all group"
                >
                    <div class="flex items-center gap-3">
                        <div class="p-2 rounded-xl bg-blue-500/20">
                            <HelpCircle class="w-5 h-5 text-blue-400" />
                        </div>
                        <div class="text-left">
                            <span class="text-sm font-medium text-[var(--text-primary)]">{{ $t('modals.settings.help') }}</span>
                            <p class="text-xs text-zinc-500">{{ $t('modals.settings.helpDesc') }}</p>
                        </div>
                    </div>
                    <MessageCircle class="w-4 h-4 text-zinc-500 group-hover:text-blue-400 transition-colors" />
                </button>

                <!-- System Section -->
                <div class="pt-2">
                    <h3 class="text-xs font-semibold text-zinc-500 uppercase tracking-wider mb-4">{{ $t('modals.settings.system') }}</h3>

                    <!-- Storage Usage -->
                    <div v-if="diskUsage" class="mb-4 p-3 rounded-xl bg-[var(--bg-surface)]">
                        <div class="flex items-center justify-between text-xs mb-2">
                            <div class="flex items-center gap-2">
                                <div class="p-1.5 rounded-lg bg-blue-500/20">
                                    <HardDrive class="w-3.5 h-3.5 text-blue-400" />
                                </div>
                                <span class="text-[var(--text-secondary)]">{{ $t('sidebar.storage') }}</span>
                            </div>
                            <span class="text-[var(--text-muted)]">
                                {{ $t('sidebar.storageUsed', { used: diskUsage.used_human, total: diskUsage.total_human }) }}
                            </span>
                        </div>
                        <div class="h-2 bg-[var(--bg-base)] rounded-full overflow-hidden">
                            <div
                                class="h-full rounded-full transition-all duration-300"
                                :class="storageBarColorClass"
                                :style="{ width: diskUsage.used_percent + '%' }"
                            ></div>
                        </div>
                    </div>

                    <!-- Restart Button -->
                    <div class="flex items-center justify-between py-3">
                        <div class="flex items-center gap-3">
                            <div class="p-2 rounded-lg bg-orange-500/20">
                                <RefreshCw class="w-4 h-4 text-orange-400" :class="{ 'animate-spin': isRestarting }" />
                            </div>
                            <div>
                                <span class="text-sm text-[var(--text-primary)]">{{ $t('modals.settings.restartContainer') }}</span>
                                <p class="text-xs text-zinc-500">{{ $t('modals.settings.restartContainerDesc') }}</p>
                            </div>
                        </div>
                        <button
                            @click="$emit('request-restart')"
                            :disabled="restartCooldown > 0 || isRestarting"
                            class="px-4 py-2 text-sm rounded-xl font-medium transition-all"
                            :class="restartCooldown > 0 || isRestarting
                                ? 'bg-zinc-500/20 text-zinc-500 cursor-not-allowed'
                                : 'bg-orange-500/20 text-orange-400 hover:bg-orange-500/30 border border-orange-500/20'"
                        >
                            <span v-if="isRestarting">{{ $t('modals.settings.restarting') }}</span>
                            <span v-else-if="restartCooldown > 0">{{ restartCooldown }}s</span>
                            <span v-else>{{ $t('modals.settings.restart') }}</span>
                        </button>
                    </div>

                    <!-- Error message -->
                    <p v-if="restartError" class="text-xs text-red-400 mt-2">{{ restartError }}</p>

                </div>
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref, computed, onMounted, watch, inject } from 'vue'
import { Settings, X, Sun, Moon, PanelLeft, PanelRight, Globe, RefreshCw, User, ExternalLink, Volume2, VolumeX, ChevronDown, Cpu, HelpCircle, MessageCircle, Plus, CreditCard, HardDrive, KeyRound, Check, Eye, EyeOff } from 'lucide-vue-next'
import { useApi } from '../../composables/useApi'
import { useSettingsState } from '../../composables/state'

const emit = defineEmits(['close', 'request-restart', 'open-topup'])

// Swipe gesture state from parent
const swipeState = inject('swipeState', {
    isDragging: ref(false),
    dragTarget: ref(null),
    settingsDragOffset: ref(0)
})

// Check if currently dragging settings
const isDraggingSettings = computed(() =>
    swipeState.isDragging.value && swipeState.dragTarget.value === 'settings'
)

// Panel style for drag animation on mobile
const panelStyle = computed(() => {
    if (!isDraggingSettings.value) return {}
    // Apply transform based on drag offset (settingsDragOffset is distance from right edge)
    return {
        transform: `translateX(${swipeState.settingsDragOffset.value}px)`
    }
})

const { getDiskUsage } = useApi()
const diskUsage = ref(null)

const storageBarColorClass = computed(() => {
    if (!diskUsage.value) return 'bg-blue-500'
    const percent = diskUsage.value.used_percent
    if (percent >= 90) return 'bg-red-500'
    if (percent >= 75) return 'bg-amber-500'
    return 'bg-blue-500'
})

const {
    isDarkTheme,
    sidebarPosition,
    currentLanguage,
    balance,
    soundEnabled,
    modelProvider,
    modelProviderLoading,
    modelProviderError,
    checkoutAvailable,
    apiKeys,
    apiKeysLoading,
    toggleTheme,
    toggleSidebarPosition,
    toggleLanguage,
    toggleSound,
    setModelProvider,
    validateApiKey,
    loadApiKeys,
    saveApiKey
} = useSettingsState()

// Handle model provider change with validation
const handleModelProviderChange = async (provider) => {
    const isValid = await validateApiKey(provider)
    if (isValid) {
        setModelProvider(provider)
    }
}

const settingsExpanded = ref(true)
const apiKeysExpanded = ref(false)
const transactionsExpanded = ref(false)

// API Keys editing state
const editingKey = ref(null)
const editKeyValue = ref('')
const savingKey = ref(false)
const apiKeySaveStatus = ref(null) // 'success' | 'error' | null
const showKeyValue = ref(false)

const API_KEY_DEFS = [
    { name: 'anthropic_api_key', label: 'anthropicApiKey', iconBg: 'bg-orange-500/20', iconText: 'text-orange-400' },
    { name: 'openai_api_key', label: 'openaiApiKey', iconBg: 'bg-emerald-500/20', iconText: 'text-emerald-400' },
    { name: 'serper_api_key', label: 'serperApiKey', iconBg: 'bg-cyan-500/20', iconText: 'text-cyan-400' },
]

const startEditKey = (keyName) => {
    editingKey.value = keyName
    editKeyValue.value = ''
    apiKeySaveStatus.value = null
    showKeyValue.value = false
}

const cancelEditKey = () => {
    editingKey.value = null
    editKeyValue.value = ''
    apiKeySaveStatus.value = null
    showKeyValue.value = false
}

const handleSaveKey = async (keyName) => {
    if (!editKeyValue.value.trim()) return
    savingKey.value = true
    apiKeySaveStatus.value = null
    const ok = await saveApiKey(keyName, editKeyValue.value.trim())
    savingKey.value = false
    if (ok) {
        apiKeySaveStatus.value = 'success'
        editingKey.value = null
        editKeyValue.value = ''
        setTimeout(() => { apiKeySaveStatus.value = null }, 2000)
    } else {
        apiKeySaveStatus.value = 'error'
    }
}
const transactions = ref([])
const transactionsLoading = ref(false)
const transactionsError = ref(false)

const formatDate = (isoString) => {
    if (!isoString) return ''
    const date = new Date(isoString)
    return date.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })
}

const fetchTransactions = async () => {
    transactionsLoading.value = true
    transactionsError.value = false
    try {
        const res = await fetch('/billing/transactions')
        if (res.ok) {
            const data = await res.json()
            transactions.value = data.transactions || []
        } else {
            transactionsError.value = true
        }
    } catch (e) {
        console.error('Failed to fetch transactions', e)
        transactionsError.value = true
    } finally {
        transactionsLoading.value = false
    }
}

const openCrispChat = () => {
    emit('close')
    if (window.$crisp) {
        window.$crisp.push(['do', 'chat:show'])
        window.$crisp.push(['do', 'chat:open'])
    }
}

// Dashboard URL - use app subdomain of base domain
// e.g., slug.zeno-stg.blue -> https://app.zeno-stg.blue/dashboard
const dashboardUrl = computed(() => {
    const hostname = window.location.hostname
    const parts = hostname.split('.')
    // Remove slug prefix (first part) to get base domain, then prepend 'app'
    const baseDomain = parts.length > 2 ? parts.slice(1).join('.') : hostname
    return `https://app.${baseDomain}/dashboard`
})

// Restart state (passed as props or from composable)
const props = defineProps({
    restartCooldown: { type: Number, default: 0 },
    isRestarting: { type: Boolean, default: false },
    restartError: { type: String, default: null }
})

const fetchBalance = async () => {
    try {
        const res = await fetch('/balance')
        if (res.ok) {
            balance.value = await res.json()
        }
    } catch (e) {
        console.error('Failed to fetch balance', e)
    }
}

onMounted(async () => {
    fetchBalance()
    diskUsage.value = await getDiskUsage()
})

// Fetch transactions when section is expanded
watch(transactionsExpanded, (expanded) => {
    if (expanded && transactions.value.length === 0) {
        fetchTransactions()
    }
})
</script>
