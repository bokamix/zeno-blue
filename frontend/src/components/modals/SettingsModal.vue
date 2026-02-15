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
                <!-- Custom Instructions Section (Collapsible) -->
                <div class="border-b border-[var(--border-subtle)]">
                    <button
                        @click="customInstructionsExpanded = !customInstructionsExpanded"
                        class="w-full flex items-center justify-between py-3 text-left"
                    >
                        <div class="flex items-center gap-3">
                            <div class="p-2 rounded-lg bg-blue-500/20">
                                <MessageSquare class="w-4 h-4 text-blue-400" />
                            </div>
                            <span class="text-sm text-[var(--text-primary)]">{{ $t('modals.settings.customInstructions') }}</span>
                        </div>
                        <ChevronDown
                            class="w-4 h-4 text-zinc-400 transition-transform"
                            :class="{ 'rotate-180': customInstructionsExpanded }"
                        />
                    </button>

                    <div v-show="customInstructionsExpanded" class="pl-4 pb-3 space-y-2">
                        <p class="text-[10px] text-zinc-500">{{ $t('modals.settings.customInstructionsDesc') }}</p>
                        <textarea
                            v-model="localCustomPrompt"
                            :placeholder="$t('modals.settings.customInstructionsPlaceholder')"
                            rows="4"
                            :maxlength="10000"
                            class="w-full px-3 py-2 text-xs rounded-lg bg-[var(--bg-elevated)] text-[var(--text-primary)] border border-[var(--border-subtle)] outline-none focus:border-blue-500/50 resize-y min-h-[80px] max-h-[200px]"
                        ></textarea>
                        <div class="flex items-center justify-between">
                            <span class="text-[10px] text-zinc-500">{{ localCustomPrompt.length }} / 10,000</span>
                            <button
                                @click="handleSaveCustomPrompt"
                                :disabled="customSystemPromptSaving || localCustomPrompt === customSystemPrompt"
                                class="px-3 py-1.5 text-xs rounded-lg font-medium transition-all bg-blue-500/20 text-blue-400 hover:bg-blue-500/30 disabled:opacity-50 disabled:cursor-not-allowed"
                            >
                                {{ customSystemPromptSaving ? $t('common.saving') : customPromptSaved ? $t('common.saved') : $t('common.save') }}
                            </button>
                        </div>
                    </div>
                </div>

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

                        <!-- AI Models -->
                        <div class="flex items-center justify-between py-2">
                            <div class="flex items-center gap-3">
                                <div class="p-1.5 rounded-lg bg-pink-500/20">
                                    <Cpu class="w-3.5 h-3.5 text-pink-400" />
                                </div>
                                <span class="text-sm text-[var(--text-secondary)]">{{ $t('modals.settings.aiModels') }}</span>
                            </div>
                        </div>

                        <div class="ml-9 mt-2 space-y-3 p-3 rounded-xl bg-[var(--bg-surface)]">
                            <p class="text-[10px] text-zinc-500">{{ $t('modals.settings.openrouterHelp') }}</p>

                            <!-- Main Model -->
                            <div>
                                <label class="text-[10px] text-zinc-500 mb-1 block">{{ $t('modals.settings.mainModel') }}</label>
                                <select
                                    v-model="selectedMainModel"
                                    @change="handleSaveModels"
                                    :disabled="modelsLoading"
                                    class="w-full px-3 py-1.5 text-xs rounded-lg bg-[var(--bg-elevated)] text-[var(--text-primary)] border border-[var(--border-subtle)] outline-none cursor-pointer disabled:opacity-50"
                                >
                                    <option v-if="modelsLoading" value="">{{ $t('modals.settings.loadingModels') }}</option>
                                    <option v-for="m in availableModels" :key="m.id" :value="m.id">{{ m.name }}</option>
                                </select>
                            </div>

                            <!-- Fast Model -->
                            <div>
                                <label class="text-[10px] text-zinc-500 mb-1 block">{{ $t('modals.settings.fastModel') }}</label>
                                <select
                                    v-model="selectedFastModel"
                                    @change="handleSaveModels"
                                    :disabled="modelsLoading"
                                    class="w-full px-3 py-1.5 text-xs rounded-lg bg-[var(--bg-elevated)] text-[var(--text-primary)] border border-[var(--border-subtle)] outline-none cursor-pointer disabled:opacity-50"
                                >
                                    <option v-if="modelsLoading" value="">{{ $t('modals.settings.loadingModels') }}</option>
                                    <option v-for="m in availableModels" :key="m.id" :value="m.id">{{ m.name }}</option>
                                </select>
                            </div>
                        </div>
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

                <!-- ZENO API Keys Section -->
                <div class="border-b border-[var(--border-subtle)]">
                    <button
                        @click="zenoApiKeysExpanded = !zenoApiKeysExpanded; if (zenoApiKeysExpanded) loadZenoApiKeys()"
                        class="w-full flex items-center justify-between py-3 text-left"
                    >
                        <div class="flex items-center gap-3">
                            <div class="p-2 rounded-lg bg-orange-500/20">
                                <KeyRound class="w-4 h-4 text-orange-400" />
                            </div>
                            <span class="text-sm text-[var(--text-primary)]">{{ $t('modals.settings.zenoApiKeys') }}</span>
                        </div>
                        <ChevronDown
                            class="w-4 h-4 text-zinc-400 transition-transform"
                            :class="{ 'rotate-180': zenoApiKeysExpanded }"
                        />
                    </button>

                    <div v-show="zenoApiKeysExpanded" class="pl-4 pb-3 space-y-2">
                        <p class="text-[10px] text-zinc-500 mb-2">{{ $t('modals.settings.zenoApiKeysDesc') }}</p>

                        <!-- Existing keys -->
                        <div v-for="key in zenoApiKeys" :key="key.id" class="flex items-center justify-between py-1.5">
                            <div class="flex items-center gap-2 min-w-0">
                                <span class="text-xs text-zinc-400 font-mono truncate">{{ key.masked }}</span>
                                <span class="text-[10px] text-zinc-600">{{ key.created_at }}</span>
                            </div>
                            <button
                                @click="deleteZenoApiKey(key.id)"
                                class="px-2 py-1 text-xs rounded-lg text-red-400 hover:bg-red-500/20 transition-all flex-shrink-0"
                            >
                                {{ $t('common.delete') }}
                            </button>
                        </div>

                        <!-- Newly generated key (show once) -->
                        <div v-if="newlyGeneratedKey" class="p-3 rounded-xl bg-green-500/10 border border-green-500/20">
                            <p class="text-[10px] text-green-400 mb-1">{{ $t('modals.settings.zenoApiKeyCopyHint') }}</p>
                            <div class="flex items-center gap-2">
                                <code class="text-xs text-green-300 font-mono break-all flex-1">{{ newlyGeneratedKey }}</code>
                                <button
                                    @click="copyToClipboard(newlyGeneratedKey)"
                                    class="px-2 py-1 text-xs rounded-lg bg-green-500/20 text-green-400 hover:bg-green-500/30 transition-all flex-shrink-0"
                                >
                                    {{ copied ? $t('common.saved') : 'Copy' }}
                                </button>
                            </div>
                        </div>

                        <!-- Generate button -->
                        <button
                            @click="generateZenoApiKey"
                            :disabled="generatingKey"
                            class="w-full px-3 py-2 text-xs rounded-lg font-medium transition-all bg-orange-500/20 text-orange-400 hover:bg-orange-500/30 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {{ generatingKey ? $t('common.loading') : $t('modals.settings.zenoApiKeyGenerate') }}
                        </button>
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
import { ref, computed, onMounted, inject, watch } from 'vue'
import { Settings, X, Sun, Moon, PanelLeft, PanelRight, Globe, RefreshCw, Volume2, VolumeX, ChevronDown, Cpu, HelpCircle, MessageCircle, HardDrive, KeyRound, Eye, EyeOff, MessageSquare } from 'lucide-vue-next'
import { useApi } from '../../composables/useApi'
import { useSettingsState } from '../../composables/state'

const emit = defineEmits(['close', 'request-restart'])

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
    soundEnabled,
    apiKeys,
    apiKeysLoading,
    customSystemPrompt,
    customSystemPromptSaving,
    saveCustomPrompt,
    toggleTheme,
    toggleSidebarPosition,
    toggleLanguage,
    toggleSound,
    loadApiKeys,
    saveApiKey,
    saveOpenRouterModels
} = useSettingsState()

// AI Models state
const availableModels = ref([])
const selectedMainModel = ref('')
const selectedFastModel = ref('')
const modelsLoading = ref(false)

const loadOpenRouterModels = async () => {
    modelsLoading.value = true
    try {
        const [modelsRes, settingsRes] = await Promise.all([
            fetch('/settings/openrouter-models'),
            fetch('/settings')
        ])
        if (modelsRes.ok) {
            const data = await modelsRes.json()
            availableModels.value = data.models || []
        }
        if (settingsRes.ok) {
            const data = await settingsRes.json()
            selectedMainModel.value = data.openrouter_model || ''
            selectedFastModel.value = data.openrouter_cheap_model || ''
        }
    } catch (e) {
        console.error('Failed to load models', e)
    } finally {
        modelsLoading.value = false
    }
}

const handleSaveModels = async () => {
    await saveOpenRouterModels(selectedMainModel.value, selectedFastModel.value)
}

// Custom instructions state
const customInstructionsExpanded = ref(false)
const localCustomPrompt = ref(customSystemPrompt.value || '')
const customPromptSaved = ref(false)

const handleSaveCustomPrompt = async () => {
    const ok = await saveCustomPrompt(localCustomPrompt.value)
    if (ok) {
        customPromptSaved.value = true
        setTimeout(() => { customPromptSaved.value = false }, 2000)
    }
}

const settingsExpanded = ref(true)
const apiKeysExpanded = ref(false)
// API Keys editing state
const editingKey = ref(null)
const editKeyValue = ref('')
const savingKey = ref(false)
const apiKeySaveStatus = ref(null) // 'success' | 'error' | null
const showKeyValue = ref(false)

const API_KEY_DEFS = [
    { name: 'openrouter_api_key', label: 'openrouterApiKey', iconBg: 'bg-pink-500/20', iconText: 'text-pink-400' },
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
// ZENO API Keys state
const zenoApiKeysExpanded = ref(false)
const zenoApiKeys = ref([])
const newlyGeneratedKey = ref(null)
const generatingKey = ref(false)
const copied = ref(false)

const loadZenoApiKeys = async () => {
    try {
        const res = await fetch('/api/auth/api-keys')
        if (res.ok) {
            zenoApiKeys.value = await res.json()
        }
    } catch {}
}

const generateZenoApiKey = async () => {
    generatingKey.value = true
    newlyGeneratedKey.value = null
    try {
        const res = await fetch('/api/auth/api-keys', { method: 'POST' })
        if (res.ok) {
            const data = await res.json()
            newlyGeneratedKey.value = data.key
            await loadZenoApiKeys()
        }
    } catch {}
    generatingKey.value = false
}

const deleteZenoApiKey = async (keyId) => {
    try {
        const res = await fetch(`/api/auth/api-keys/${keyId}`, { method: 'DELETE' })
        if (res.ok) {
            await loadZenoApiKeys()
        }
    } catch {}
}

const copyToClipboard = async (text) => {
    try {
        await navigator.clipboard.writeText(text)
        copied.value = true
        setTimeout(() => { copied.value = false }, 2000)
    } catch {}
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

// Sync custom prompt when settings load from API
watch(customSystemPrompt, (newVal) => {
    localCustomPrompt.value = newVal || ''
})

onMounted(async () => {
    diskUsage.value = await getDiskUsage()
    loadOpenRouterModels()
})

</script>
