<template>
    <header class="h-16 flex items-center px-4 md:px-6 relative z-30 shrink-0">
        <!-- Background with blur -->
        <div class="absolute inset-0 bg-[var(--bg-base)]/80 backdrop-blur-xl">
            <!-- Gradient line at bottom -->
            <div class="absolute bottom-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-blue-500/60 to-transparent"></div>
        </div>

        <!-- Content -->
        <div class="relative flex items-center justify-between w-full">
            <!-- Left: Hamburger (mobile) + Apps menu (mobile) -->
            <div class="flex items-center gap-1">
                <!-- Hamburger menu (mobile only) -->
                <button
                    @click="$emit('toggle-sidebar')"
                    class="md:hidden p-2 -ml-2 text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
                >
                    <Menu class="w-5 h-5" />
                </button>
                <!-- Apps menu (mobile only) -->
                <button
                    @click="$emit('open-mobile-nav')"
                    class="md:hidden p-2 text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
                >
                    <LayoutGrid class="w-5 h-5" />
                </button>
            </div>

            <!-- Center: Navigation Pills (desktop only) -->
            <nav class="hidden md:flex nav-pill absolute left-1/2 -translate-x-1/2">
                <button @click="$emit('open-apps')" class="nav-pill-item flex items-center gap-2">
                    <LayoutGrid class="w-4 h-4" /> {{ $t('nav.apps') }}
                </button>
                <button @click="$emit('open-integrations')" class="nav-pill-item flex items-center gap-2">
                    <Plug class="w-4 h-4" /> {{ $t('nav.integrations') }}
                </button>
                <button @click="$emit('open-scheduler')" class="nav-pill-item flex items-center gap-2">
                    <Clock class="w-4 h-4" /> {{ $t('nav.scheduler') }}
                </button>
                <button @click="$emit('open-skills')" class="nav-pill-item flex items-center gap-2">
                    <Sparkles class="w-4 h-4" /> {{ $t('nav.skills') }}
                </button>
            </nav>

            <!-- Right: Settings (desktop) + New Chat -->
            <div class="flex items-center gap-3">
                <button
                    @click="$emit('open-settings')"
                    class="hidden md:block p-2.5 text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-surface)] rounded-full transition-all"
                    :title="$t('nav.settings')"
                >
                    <Settings class="w-5 h-5" />
                </button>
                <button
                    @click="$emit('new-chat')"
                    class="btn-primary gap-2"
                >
                    <Plus class="w-4 h-4" /><span class="hidden md:inline">{{ $t('nav.newChat') }}</span>
                </button>
            </div>
        </div>
    </header>
</template>

<script setup>
import { Menu, LayoutGrid, Plug, Clock, Settings, Plus, Sparkles } from 'lucide-vue-next'

defineEmits([
    'toggle-sidebar',
    'open-mobile-nav',
    'open-apps',
    'open-integrations',
    'open-scheduler',
    'open-settings',
    'open-skills',
    'new-chat'
])
</script>
