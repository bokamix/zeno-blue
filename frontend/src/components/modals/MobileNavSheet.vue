<template>
    <Teleport to="body">
        <div class="fixed inset-0 z-[100] md:hidden">
            <!-- Overlay -->
            <div
                @click="$emit('close')"
                class="absolute inset-0 bg-black/60 backdrop-blur-sm"
            ></div>

            <!-- Sheet -->
            <div class="absolute bottom-0 left-0 right-0 bg-[var(--bg-surface)] rounded-t-3xl animate-slide-up safe-area-bottom border-t border-[var(--border-subtle)]">
                <!-- Handle bar -->
                <div class="flex justify-center py-3">
                    <div class="w-10 h-1 bg-zinc-600 rounded-full"></div>
                </div>

                <!-- Options grid -->
                <div class="px-4 pb-6 grid grid-cols-2 gap-3">
                    <button
                        @click="$emit('open-apps')"
                        class="nav-tile"
                    >
                        <div class="nav-tile-icon bg-gradient-to-br from-blue-500/20 to-purple-500/20">
                            <LayoutGrid class="w-6 h-6 text-blue-400" />
                        </div>
                        <span class="nav-tile-label">{{ $t('nav.apps') }}</span>
                    </button>
                    <button
                        @click="$emit('open-integrations')"
                        class="nav-tile"
                    >
                        <div class="nav-tile-icon bg-gradient-to-br from-sky-500/20 to-fuchsia-500/20">
                            <Plug class="w-6 h-6 text-sky-400" />
                        </div>
                        <span class="nav-tile-label">{{ $t('nav.integrations') }}</span>
                    </button>
                    <button
                        @click="$emit('open-scheduler')"
                        class="nav-tile"
                    >
                        <div class="nav-tile-icon bg-gradient-to-br from-cyan-500/20 to-blue-500/20">
                            <Clock class="w-6 h-6 text-cyan-400" />
                        </div>
                        <span class="nav-tile-label">{{ $t('nav.scheduler') }}</span>
                    </button>
                    <button
                        @click="$emit('open-skills')"
                        class="nav-tile"
                    >
                        <div class="nav-tile-icon bg-gradient-to-br from-amber-500/20 to-orange-500/20">
                            <Sparkles class="w-6 h-6 text-amber-400" />
                        </div>
                        <span class="nav-tile-label">{{ $t('nav.skills') }}</span>
                    </button>
                    <button
                        @click="$emit('open-settings')"
                        class="nav-tile"
                    >
                        <div class="nav-tile-icon bg-gradient-to-br from-zinc-500/20 to-slate-500/20">
                            <Settings class="w-6 h-6 text-zinc-400" />
                        </div>
                        <span class="nav-tile-label">{{ $t('nav.settings') }}</span>
                    </button>
                </div>
            </div>
        </div>
    </Teleport>
</template>

<script setup>
import { LayoutGrid, Plug, Clock, Settings, Sparkles } from 'lucide-vue-next'

defineEmits(['close', 'open-apps', 'open-integrations', 'open-scheduler', 'open-skills', 'open-settings'])
</script>

<style scoped>
.nav-tile {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.75rem;
    padding: 1.25rem 1rem;
    border-radius: 1rem;
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
    color: var(--text-primary);
    cursor: pointer;
    transition: all 0.2s ease;
}

.nav-tile:hover {
    background: var(--bg-elevated);
    border-color: rgba(37, 99, 235, 0.4);
}

.nav-tile:active {
    transform: scale(0.98);
}

.nav-tile-icon {
    padding: 0.75rem;
    border-radius: 0.75rem;
}

.nav-tile-label {
    font-size: 0.875rem;
    font-weight: 500;
}

/* Light mode adjustments */
[data-theme="light"] .nav-tile {
    background: #ffffff;
    border: 1px solid rgba(0, 0, 0, 0.1);
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

[data-theme="light"] .nav-tile:hover {
    background: #ffffff;
    border-color: rgba(79, 70, 229, 0.4);
    box-shadow: 0 4px 12px rgba(79, 70, 229, 0.15);
}
</style>
