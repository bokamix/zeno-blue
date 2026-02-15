<template>
    <div
        class="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
        @click.self="$emit('close')"
    >
        <div class="glass-solid rounded-3xl w-full max-w-lg max-h-[80vh] flex flex-col animate-modal-enter relative overflow-hidden">
            <!-- Gradient top accent -->
            <div class="absolute top-0 left-8 right-8 h-px bg-gradient-to-r from-transparent via-amber-500/50 to-transparent"></div>

            <!-- Modal Header -->
            <div class="flex items-center justify-between p-6 border-b border-white/5">
                <div class="flex items-center gap-3">
                    <div class="p-2 rounded-xl bg-gradient-to-br from-amber-500/20 to-orange-500/20">
                        <Sparkles class="w-5 h-5 text-amber-400" />
                    </div>
                    <h2 class="text-lg font-semibold text-[var(--text-primary)]">{{ $t('modals.customSkills.title') }}</h2>
                </div>
                <div class="flex items-center gap-2">
                    <button
                        v-if="!isEditing"
                        @click="startCreate"
                        class="px-3 py-1.5 text-xs rounded-lg font-medium transition-all bg-amber-500/20 text-amber-400 hover:bg-amber-500/30"
                    >
                        {{ $t('modals.customSkills.createSkill') }}
                    </button>
                    <button @click="$emit('close')" class="p-2 rounded-xl text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-surface)] transition-all">
                        <X class="w-5 h-5" />
                    </button>
                </div>
            </div>

            <!-- Modal Body -->
            <div class="flex-1 overflow-y-auto p-6 custom-scroll">
                <!-- Create/Edit Form -->
                <div v-if="isEditing" class="space-y-4">
                    <div>
                        <label class="text-xs text-zinc-500 mb-1 block">{{ $t('modals.customSkills.nameLabel') }}</label>
                        <input
                            v-model="editForm.name"
                            type="text"
                            :placeholder="$t('modals.customSkills.namePlaceholder')"
                            class="w-full px-3 py-2 text-sm rounded-lg bg-[var(--bg-elevated)] text-[var(--text-primary)] border border-[var(--border-subtle)] outline-none focus:border-amber-500/50"
                        />
                    </div>
                    <div>
                        <label class="text-xs text-zinc-500 mb-1 block">{{ $t('modals.customSkills.descriptionLabel') }}</label>
                        <input
                            v-model="editForm.description"
                            type="text"
                            :placeholder="$t('modals.customSkills.descriptionPlaceholder')"
                            class="w-full px-3 py-2 text-sm rounded-lg bg-[var(--bg-elevated)] text-[var(--text-primary)] border border-[var(--border-subtle)] outline-none focus:border-amber-500/50"
                        />
                    </div>
                    <div>
                        <label class="text-xs text-zinc-500 mb-1 block">{{ $t('modals.customSkills.instructionsLabel') }}</label>
                        <textarea
                            v-model="editForm.instructions"
                            :placeholder="$t('modals.customSkills.instructionsPlaceholder')"
                            rows="8"
                            class="w-full px-3 py-2 text-sm rounded-lg bg-[var(--bg-elevated)] text-[var(--text-primary)] border border-[var(--border-subtle)] outline-none focus:border-amber-500/50 resize-y min-h-[120px] max-h-[300px] font-mono"
                        ></textarea>
                    </div>
                    <p v-if="formError" class="text-xs text-red-400">{{ formError }}</p>
                    <div class="flex items-center gap-2 justify-end">
                        <button
                            @click="cancelEdit"
                            class="px-4 py-2 text-sm rounded-lg font-medium transition-all bg-white/10 text-zinc-300 hover:bg-white/20"
                        >
                            {{ $t('common.cancel') }}
                        </button>
                        <button
                            @click="handleSave"
                            :disabled="saving || !editForm.name.trim() || !editForm.instructions.trim()"
                            class="px-4 py-2 text-sm rounded-lg font-medium transition-all bg-amber-500/20 text-amber-400 hover:bg-amber-500/30 disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {{ saving ? $t('common.saving') : $t('common.save') }}
                        </button>
                    </div>
                </div>

                <!-- Skills List -->
                <div v-else>
                    <!-- Loading -->
                    <div v-if="loading" class="text-center py-12">
                        <p class="text-zinc-400">{{ $t('common.loading') }}</p>
                    </div>

                    <!-- Empty State -->
                    <div v-else-if="skills.length === 0" class="text-center py-12">
                        <div class="w-16 h-16 rounded-2xl bg-gradient-to-br from-amber-500/10 to-orange-500/10 flex items-center justify-center mx-auto mb-4">
                            <Sparkles class="w-8 h-8 text-amber-400/50" />
                        </div>
                        <p class="text-zinc-400 mb-2">{{ $t('modals.customSkills.noSkills') }}</p>
                        <p class="text-xs text-zinc-500">{{ $t('modals.customSkills.noSkillsHint') }}</p>
                    </div>

                    <!-- Skill Cards -->
                    <div v-else class="space-y-3">
                        <div
                            v-for="skill in skills"
                            :key="skill.id"
                            class="bg-white/5 border border-white/5 rounded-xl p-4 hover:bg-white/[0.07] transition-colors"
                        >
                            <div class="flex items-start justify-between">
                                <div class="flex-1 min-w-0">
                                    <h3 class="text-sm font-medium text-[var(--text-primary)] truncate">{{ skill.name }}</h3>
                                    <p v-if="skill.description" class="text-xs text-zinc-500 mt-0.5 line-clamp-2">{{ skill.description }}</p>
                                </div>
                                <div class="flex items-center gap-1 flex-shrink-0 ml-3">
                                    <button
                                        @click="startEdit(skill)"
                                        class="p-1.5 text-zinc-400 hover:text-amber-400 hover:bg-amber-500/20 rounded-lg transition-all"
                                        :title="$t('modals.customSkills.editSkill')"
                                    >
                                        <Pencil class="w-3.5 h-3.5" />
                                    </button>
                                    <button
                                        v-if="deletingId !== skill.id"
                                        @click="deletingId = skill.id"
                                        class="p-1.5 text-zinc-400 hover:text-red-400 hover:bg-red-500/20 rounded-lg transition-all"
                                        :title="$t('common.delete')"
                                    >
                                        <Trash2 class="w-3.5 h-3.5" />
                                    </button>
                                    <div v-else class="flex items-center gap-1">
                                        <button
                                            @click="handleDelete(skill.id)"
                                            class="px-2 py-1 text-[10px] rounded-lg font-medium bg-red-500/20 text-red-400 hover:bg-red-500/30 transition-all"
                                        >
                                            {{ $t('common.delete') }}
                                        </button>
                                        <button
                                            @click="deletingId = null"
                                            class="px-2 py-1 text-[10px] rounded-lg font-medium bg-white/10 text-zinc-300 hover:bg-white/20 transition-all"
                                        >
                                            {{ $t('common.cancel') }}
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { Sparkles, X, Pencil, Trash2 } from 'lucide-vue-next'
import { useApi } from '../../composables/useApi'

const emit = defineEmits(['close'])
const api = useApi()

const skills = ref([])
const loading = ref(true)
const saving = ref(false)
const formError = ref(null)
const deletingId = ref(null)

// Edit state
const isEditing = ref(false)
const editingSkillId = ref(null)
const editForm = ref({ name: '', description: '', instructions: '' })

const loadSkills = async () => {
    loading.value = true
    try {
        skills.value = await api.getCustomSkills()
    } catch (e) {
        console.error('Failed to load custom skills', e)
    } finally {
        loading.value = false
    }
}

const startCreate = () => {
    editingSkillId.value = null
    editForm.value = { name: '', description: '', instructions: '' }
    formError.value = null
    isEditing.value = true
}

const startEdit = (skill) => {
    editingSkillId.value = skill.id
    editForm.value = {
        name: skill.name,
        description: skill.description || '',
        instructions: skill.instructions || '',
    }
    formError.value = null
    isEditing.value = true
}

const cancelEdit = () => {
    isEditing.value = false
    editingSkillId.value = null
    formError.value = null
}

const handleSave = async () => {
    if (!editForm.value.name.trim() || !editForm.value.instructions.trim()) return
    saving.value = true
    formError.value = null
    try {
        if (editingSkillId.value) {
            await api.updateCustomSkill(editingSkillId.value, editForm.value)
        } else {
            await api.createCustomSkill(editForm.value)
        }
        isEditing.value = false
        editingSkillId.value = null
        await loadSkills()
    } catch (e) {
        formError.value = e.message
    } finally {
        saving.value = false
    }
}

const handleDelete = async (skillId) => {
    try {
        await api.deleteCustomSkill(skillId)
        deletingId.value = null
        await loadSkills()
    } catch (e) {
        console.error('Failed to delete skill', e)
    }
}

onMounted(() => {
    loadSkills()
})
</script>
