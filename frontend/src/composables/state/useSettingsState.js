import { ref } from 'vue'
import { setLanguage, getCurrentLanguage } from '../../locales'

// Singleton state (shared across all components)
const isDarkTheme = ref(true)
const sidebarPosition = ref('left')
const currentLanguage = ref(getCurrentLanguage())
const soundEnabled = ref(false)
const modelProvider = ref('anthropic')  // "anthropic", "openai", or "custom"
const modelProviderLoading = ref(false)
const modelProviderError = ref(null)
const apiKeys = ref({})
const apiKeysLoading = ref(false)
const customProviderSettings = ref({
    model: '',
    cheapModel: '',
    baseUrl: '',
})

export function useSettingsState() {
    // Apply theme to document
    const applyTheme = () => {
        document.documentElement.setAttribute('data-theme', isDarkTheme.value ? 'dark' : 'light')
    }

    // Toggle dark/light theme
    const toggleTheme = () => {
        isDarkTheme.value = !isDarkTheme.value
        localStorage.setItem('app-theme', isDarkTheme.value ? 'dark' : 'light')
        applyTheme()
    }

    // Load theme from localStorage (or system preference if not set)
    const loadTheme = () => {
        const savedTheme = localStorage.getItem('app-theme')
        if (savedTheme) {
            isDarkTheme.value = savedTheme === 'dark'
        } else {
            // No saved preference - use system preference
            isDarkTheme.value = window.matchMedia('(prefers-color-scheme: dark)').matches
        }
        applyTheme()
    }

    // Toggle sidebar position (left/right)
    const toggleSidebarPosition = () => {
        sidebarPosition.value = sidebarPosition.value === 'left' ? 'right' : 'left'
        localStorage.setItem('sidebar-position', sidebarPosition.value)
    }

    // Load sidebar position from localStorage
    const loadSidebarPosition = () => {
        const savedPosition = localStorage.getItem('sidebar-position')
        if (savedPosition === 'right') {
            sidebarPosition.value = 'right'
        }
    }

    // Toggle language (en/pl)
    const toggleLanguage = () => {
        const newLang = currentLanguage.value === 'en' ? 'pl' : 'en'
        currentLanguage.value = newLang
        setLanguage(newLang)
    }

    // Toggle sound notifications
    const toggleSound = () => {
        soundEnabled.value = !soundEnabled.value
        localStorage.setItem('sound-enabled', soundEnabled.value ? 'true' : 'false')
    }

    // Load sound setting from localStorage
    const loadSoundSetting = () => {
        const saved = localStorage.getItem('sound-enabled')
        soundEnabled.value = saved === 'true'
    }

    // Play notification sound
    const playNotificationSound = () => {
        if (soundEnabled.value) {
            const audio = new Audio('/sounds/notification.mp3')
            audio.volume = 0.5
            audio.play().catch(e => console.warn('Could not play notification sound:', e))
        }
    }

    // Load model provider from API
    const loadModelProvider = async () => {
        try {
            const res = await fetch('/settings')
            if (res.ok) {
                const data = await res.json()
                modelProvider.value = data.model_provider || 'anthropic'
                // Load custom provider settings if applicable
                if (data.model_provider === 'custom') {
                    customProviderSettings.value = {
                        model: data.custom_provider_model || '',
                        cheapModel: data.custom_provider_cheap_model || '',
                        baseUrl: data.custom_provider_base_url || '',
                    }
                }
            }
        } catch (e) {
            console.error('Failed to load model provider setting', e)
        }
    }

    // Validate API key for provider before switching
    const validateApiKey = async (provider) => {
        modelProviderError.value = null
        modelProviderLoading.value = true
        try {
            const res = await fetch(`/settings/validate-provider?provider=${provider}`)
            if (res.ok) {
                const data = await res.json()
                if (!data.valid) {
                    modelProviderError.value = data.error || `API key for ${provider} is not configured`
                    return false
                }
                return true
            }
            modelProviderError.value = 'Failed to validate provider'
            return false
        } catch (e) {
            console.error('Failed to validate provider', e)
            modelProviderError.value = 'Failed to validate provider'
            return false
        } finally {
            modelProviderLoading.value = false
        }
    }

    // Set model provider via API
    const setModelProvider = async (provider) => {
        if (!['anthropic', 'openai', 'custom'].includes(provider)) return
        modelProviderError.value = null
        modelProviderLoading.value = true
        try {
            const res = await fetch('/settings', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ model_provider: provider })
            })
            if (res.ok) {
                modelProvider.value = provider
            }
        } catch (e) {
            console.error('Failed to save model provider setting', e)
        } finally {
            modelProviderLoading.value = false
        }
    }

    // Save custom provider settings via API
    const saveCustomProvider = async (settings) => {
        modelProviderError.value = null
        modelProviderLoading.value = true
        try {
            const res = await fetch('/settings', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    model_provider: 'custom',
                    custom_provider_model: settings.model || '',
                    custom_provider_cheap_model: settings.cheapModel || '',
                    custom_provider_base_url: settings.baseUrl || '',
                })
            })
            if (res.ok) {
                modelProvider.value = 'custom'
                customProviderSettings.value = { ...settings }
                return true
            }
            return false
        } catch (e) {
            console.error('Failed to save custom provider settings', e)
            modelProviderError.value = 'Failed to save custom provider settings'
            return false
        } finally {
            modelProviderLoading.value = false
        }
    }

    // Load API key statuses from backend
    const loadApiKeys = async () => {
        apiKeysLoading.value = true
        try {
            const res = await fetch('/settings/api-keys')
            if (res.ok) {
                const data = await res.json()
                apiKeys.value = data.keys || {}
            }
        } catch (e) {
            console.error('Failed to load API keys', e)
        } finally {
            apiKeysLoading.value = false
        }
    }

    // Save a single API key
    const saveApiKey = async (keyName, value) => {
        try {
            const res = await fetch('/settings/api-keys', {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ [keyName]: value })
            })
            if (res.ok) {
                await loadApiKeys()
                return true
            }
            return false
        } catch (e) {
            console.error('Failed to save API key', e)
            return false
        }
    }

    // Load all settings from localStorage
    const loadSettings = () => {
        loadTheme()
        loadSidebarPosition()
        loadSoundSetting()
        loadModelProvider()
    }

    return {
        // State
        isDarkTheme,
        sidebarPosition,
        currentLanguage,
        soundEnabled,
        modelProvider,
        modelProviderLoading,
        modelProviderError,
        apiKeys,
        apiKeysLoading,
        customProviderSettings,

        // Actions
        applyTheme,
        toggleTheme,
        loadTheme,
        toggleSidebarPosition,
        loadSidebarPosition,
        toggleLanguage,
        toggleSound,
        loadSoundSetting,
        playNotificationSound,
        loadModelProvider,
        setModelProvider,
        saveCustomProvider,
        validateApiKey,
        loadApiKeys,
        saveApiKey,
        loadSettings
    }
}
