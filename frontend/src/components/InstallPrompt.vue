<template>
    <Teleport to="body">
        <Transition name="fade">
            <div
                v-if="showPrompt"
                class="fixed inset-0 bg-black/60 backdrop-blur-sm z-[200] flex items-end sm:items-center justify-center p-4"
                @click.self="dismiss"
            >
                <div class="glass-solid rounded-3xl w-full max-w-sm animate-modal-enter relative overflow-hidden safe-area-bottom">
                    <!-- Gradient top accent -->
                    <div class="absolute top-0 left-8 right-8 h-px bg-gradient-to-r from-transparent via-blue-500/50 to-transparent"></div>

                    <!-- Content -->
                    <div class="p-6 text-center">
                        <!-- Logo -->
                        <div class="w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center mx-auto mb-4 shadow-lg shadow-blue-500/25">
                            <span class="text-white text-2xl font-black">Z</span>
                        </div>

                        <h2 class="text-xl font-semibold text-[var(--text-primary)] mb-2">
                            {{ $t('pwa.install.title') }}
                        </h2>

                        <!-- iOS Instructions -->
                        <div v-if="isIOS" class="text-left space-y-4 mt-6">
                            <div class="flex items-start gap-3">
                                <div class="w-8 h-8 rounded-full bg-blue-500/20 flex items-center justify-center flex-shrink-0">
                                    <span class="text-blue-400 font-semibold">1</span>
                                </div>
                                <div>
                                    <p class="text-[var(--text-primary)]">
                                        {{ $t('pwa.install.clickIcon') }}
                                        <span class="inline-flex items-center justify-center w-6 h-6 bg-white/10 rounded mx-1">
                                            <svg class="w-4 h-4 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"/>
                                            </svg>
                                        </span>
                                        {{ $t('pwa.install.shareIcon') }}
                                    </p>
                                </div>
                            </div>

                            <div class="flex items-start gap-3">
                                <div class="w-8 h-8 rounded-full bg-blue-500/20 flex items-center justify-center flex-shrink-0">
                                    <span class="text-blue-400 font-semibold">2</span>
                                </div>
                                <div>
                                    <p class="text-[var(--text-primary)]">
                                        {{ $t('pwa.install.scrollAndSelect') }}
                                        <span class="text-blue-400 font-medium">"{{ $t('pwa.install.addToHomeScreen') }}"</span>
                                    </p>
                                </div>
                            </div>

                            <button
                                @click="dismiss"
                                class="w-full mt-4 px-6 py-3 bg-white/10 hover:bg-white/15 text-[var(--text-primary)] font-medium rounded-xl transition-all"
                            >
                                {{ $t('pwa.install.understood') }}
                            </button>
                        </div>

                        <!-- Android / Chrome Install Button -->
                        <div v-else class="mt-4">
                            <p class="text-[var(--text-secondary)] text-sm mb-6">
                                {{ $t('pwa.install.androidDescription') }}
                            </p>

                            <div class="flex gap-3">
                                <button
                                    @click="dismiss"
                                    class="flex-1 px-6 py-3 bg-white/10 hover:bg-white/15 text-[var(--text-secondary)] font-medium rounded-xl transition-all"
                                >
                                    {{ $t('pwa.install.notNow') }}
                                </button>
                                <button
                                    @click="install"
                                    class="flex-1 px-6 py-3 bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 text-white font-medium rounded-xl transition-all shadow-lg shadow-blue-500/25"
                                >
                                    {{ $t('pwa.install.installButton') }}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </Transition>
    </Teleport>
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'

const showPrompt = ref(false)
const deferredPrompt = ref(null)

// Platform detection
const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream
const isAndroid = /Android/.test(navigator.userAgent)
const isStandalone = window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone

// Check if we should show the prompt
const shouldShowPrompt = () => {
    // Don't show if already installed
    if (isStandalone) return false

    // Don't show if already dismissed
    if (localStorage.getItem('pwa-prompt-dismissed')) return false

    // Only show on mobile
    return isIOS || isAndroid
}

// Handle beforeinstallprompt event (Android/Chrome)
const handleBeforeInstallPrompt = (e) => {
    e.preventDefault()
    deferredPrompt.value = e
}

// Install the app (Android)
const install = async () => {
    if (deferredPrompt.value) {
        deferredPrompt.value.prompt()
        const { outcome } = await deferredPrompt.value.userChoice
        if (outcome === 'accepted') {
            localStorage.setItem('pwa-prompt-dismissed', 'true')
        }
        deferredPrompt.value = null
    }
    showPrompt.value = false
}

// Dismiss the prompt
const dismiss = () => {
    localStorage.setItem('pwa-prompt-dismissed', 'true')
    showPrompt.value = false
}

onMounted(() => {
    // Listen for the install prompt event
    window.addEventListener('beforeinstallprompt', handleBeforeInstallPrompt)

    // Show prompt after 3 seconds if applicable
    if (shouldShowPrompt()) {
        setTimeout(() => {
            // For Android, only show if we have the deferred prompt OR if it's iOS
            if (isIOS || deferredPrompt.value) {
                showPrompt.value = true
            }
        }, 3000)
    }
})

onBeforeUnmount(() => {
    window.removeEventListener('beforeinstallprompt', handleBeforeInstallPrompt)
})
</script>

<style scoped>
.fade-enter-active,
.fade-leave-active {
    transition: opacity 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
    opacity: 0;
}
</style>
