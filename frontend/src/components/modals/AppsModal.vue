<template>
    <div
        class="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
        @click.self="$emit('close')"
    >
        <div class="glass-solid rounded-3xl w-full max-w-lg max-h-[80vh] flex flex-col animate-modal-enter relative overflow-hidden">
            <!-- Gradient top accent -->
            <div class="absolute top-0 left-8 right-8 h-px bg-gradient-to-r from-transparent via-blue-500/50 to-transparent"></div>

            <!-- Modal Header -->
            <div class="flex items-center justify-between p-6 border-b border-white/5">
                <div class="flex items-center gap-3">
                    <div class="p-2 rounded-xl bg-gradient-to-br from-blue-500/20 to-purple-500/20">
                        <LayoutGrid class="w-5 h-5 text-blue-400" />
                    </div>
                    <h2 class="text-lg font-semibold text-[var(--text-primary)]">{{ $t('modals.apps.title') }}</h2>
                </div>
                <button @click="$emit('close')" class="p-2 rounded-xl text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-surface)] transition-all">
                    <X class="w-5 h-5" />
                </button>
            </div>

            <!-- Modal Body -->
            <div class="flex-1 overflow-y-auto p-6 custom-scroll">
                <!-- Empty State -->
                <div v-if="apps.length === 0" class="text-center py-12">
                    <div class="w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-500/10 to-purple-500/10 flex items-center justify-center mx-auto mb-4">
                        <LayoutGrid class="w-8 h-8 text-blue-400/50" />
                    </div>
                    <p class="text-zinc-400">{{ $t('modals.apps.noApps') }}</p>
                </div>

                <!-- App List -->
                <div v-else class="space-y-3">
                    <div
                        v-for="app in apps"
                        :key="app.app_id"
                        class="bg-white/5 border border-white/5 rounded-xl p-4 hover:bg-white/[0.07] transition-colors"
                    >
                        <div class="flex items-start justify-between">
                            <div class="flex-1 min-w-0">
                                <!-- Name + status indicator (with inline edit) -->
                                <div class="flex items-center gap-2">
                                    <span
                                        class="w-2.5 h-2.5 rounded-full flex-shrink-0"
                                        :class="app.alive ? 'bg-emerald-500 shadow-lg shadow-emerald-500/50' : 'bg-zinc-500'"
                                    ></span>
                                    <!-- Edit mode -->
                                    <div v-if="editingAppId === app.app_id" class="flex items-center gap-2 flex-1">
                                        <input
                                            ref="editInput"
                                            v-model="editingName"
                                            @keydown.enter="saveAppName(app)"
                                            @keydown.escape="cancelEdit"
                                            class="flex-1 px-2 py-1 bg-[var(--bg-surface)] border border-[var(--border-subtle)] rounded-lg text-[var(--text-primary)] text-sm focus:outline-none focus:border-blue-500"
                                            :placeholder="$t('modals.apps.enterName')"
                                        />
                                        <button
                                            @click="saveAppName(app)"
                                            class="p-1.5 text-emerald-400 hover:text-emerald-300 hover:bg-emerald-500/20 rounded-lg transition-all"
                                            :title="$t('common.save')"
                                        >
                                            <Check class="w-4 h-4" />
                                        </button>
                                        <button
                                            @click="cancelEdit"
                                            class="p-1.5 text-zinc-400 hover:text-zinc-300 hover:bg-white/10 rounded-lg transition-all"
                                            :title="$t('common.cancel')"
                                        >
                                            <X class="w-4 h-4" />
                                        </button>
                                    </div>
                                    <!-- Display mode -->
                                    <span v-else class="font-medium text-[var(--text-primary)]">{{ app.name }}</span>
                                </div>
                                <!-- URL (clickable) -->
                                <a
                                    v-if="app.url && app.alive"
                                    :href="app.url"
                                    target="_blank"
                                    class="text-sm text-blue-400 hover:text-blue-300 mt-1 block truncate transition-colors"
                                >
                                    {{ app.url }}
                                </a>
                            </div>
                            <!-- Actions -->
                            <div class="flex items-center gap-2 ml-4 flex-shrink-0">
                                <!-- Edit button -->
                                <button
                                    v-if="editingAppId !== app.app_id"
                                    @click="startEdit(app)"
                                    class="p-2 text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-white/10 rounded-lg transition-all"
                                    :title="$t('modals.apps.rename')"
                                >
                                    <Pencil class="w-4 h-4" />
                                </button>
                                <!-- Delete button -->
                                <button
                                    v-if="editingAppId !== app.app_id"
                                    @click="confirmDeleteApp(app)"
                                    class="p-2 text-[var(--text-secondary)] hover:text-red-400 hover:bg-red-500/20 rounded-lg transition-all"
                                    :title="$t('common.delete')"
                                >
                                    <Trash2 class="w-4 h-4" />
                                </button>
                                <!-- Restart button (only if alive) -->
                                <button
                                    v-if="app.alive && editingAppId !== app.app_id"
                                    @click="restartApp(app)"
                                    class="p-2 text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-white/10 rounded-lg transition-all"
                                    :title="$t('common.restart')"
                                >
                                    <RefreshCw class="w-4 h-4" />
                                </button>
                                <!-- Toggle (start/stop) -->
                                <button
                                    v-if="editingAppId !== app.app_id"
                                    @click="toggleApp(app)"
                                    class="px-4 py-2 text-sm rounded-lg font-medium transition-all"
                                    :class="app.alive
                                        ? 'bg-red-500/20 text-red-400 hover:bg-red-500/30 border border-red-500/20'
                                        : 'bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30 border border-emerald-500/20'"
                                >
                                    {{ app.alive ? $t('common.stop') : $t('common.start') }}
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { LayoutGrid, X, RefreshCw, Pencil, Trash2, Check } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()
const emit = defineEmits(['close'])

const apps = ref([])
const editingAppId = ref(null)
const editingName = ref('')
const editInput = ref(null)

const fetchApps = async () => {
    try {
        const res = await fetch('/apps')
        if (res.ok) {
            apps.value = await res.json()
        }
    } catch (e) {
        console.error('Failed to fetch apps', e)
    }
}

const toggleApp = async (app) => {
    const action = app.alive ? '__stop' : '__start'
    try {
        const res = await fetch(`/apps/${app.app_id}/${action}`, { method: 'POST' })
        if (res.ok) {
            await fetchApps()
        }
    } catch (e) {
        console.error('Failed to toggle app', e)
    }
}

const restartApp = async (app) => {
    try {
        const res = await fetch(`/apps/${app.app_id}/__restart`, { method: 'POST' })
        if (res.ok) {
            await fetchApps()
        }
    } catch (e) {
        console.error('Failed to restart app', e)
    }
}

const startEdit = (app) => {
    editingAppId.value = app.app_id
    editingName.value = app.name
    nextTick(() => {
        if (editInput.value) {
            const input = Array.isArray(editInput.value) ? editInput.value[0] : editInput.value
            input?.focus()
            input?.select()
        }
    })
}

const cancelEdit = () => {
    editingAppId.value = null
    editingName.value = ''
}

const saveAppName = async (app) => {
    if (!editingName.value.trim()) {
        cancelEdit()
        return
    }

    try {
        const res = await fetch(`/apps/${app.app_id}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: editingName.value.trim() })
        })
        if (res.ok) {
            await fetchApps()
        }
    } catch (e) {
        console.error('Failed to rename app', e)
    }
    cancelEdit()
}

const confirmDeleteApp = async (app) => {
    if (!confirm(t('modals.apps.confirmDelete', { name: app.name }))) {
        return
    }

    try {
        const res = await fetch(`/apps/${app.app_id}`, { method: 'DELETE' })
        if (res.ok) {
            await fetchApps()
        }
    } catch (e) {
        console.error('Failed to delete app', e)
    }
}

onMounted(() => {
    fetchApps()
})
</script>
