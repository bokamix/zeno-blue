<template>
    <div class="flex flex-col h-full overflow-hidden">
        <!-- Header -->
        <div class="px-6 py-5 border-b border-[var(--border-subtle)] shrink-0 flex items-center justify-between">
            <div>
                <h2 class="text-base font-semibold text-[var(--text-primary)]">Procedures</h2>
                <p class="text-xs text-[var(--text-muted)] mt-0.5">AI-powered shareable workflows</p>
            </div>
            <button @click="openCreate" class="btn-primary gap-2 text-sm">
                <Plus class="w-4 h-4" /> New Procedure
            </button>
        </div>

        <!-- List -->
        <div class="flex-1 overflow-y-auto p-6">
            <div v-if="loading" class="flex items-center justify-center h-32">
                <div class="w-5 h-5 border-2 border-blue-500/30 border-t-blue-500 rounded-full animate-spin"></div>
            </div>

            <div v-else-if="procedures.length === 0" class="flex flex-col items-center justify-center h-48 text-center">
                <div class="w-12 h-12 rounded-xl bg-blue-500/10 flex items-center justify-center mb-3">
                    <Workflow class="w-6 h-6 text-blue-400" />
                </div>
                <p class="text-sm font-medium text-[var(--text-primary)] mb-1">No procedures yet</p>
                <p class="text-xs text-[var(--text-muted)]">Create a procedure to share an AI-guided workflow.</p>
            </div>

            <div v-else class="space-y-3">
                <div
                    v-for="proc in procedures"
                    :key="proc.id"
                    class="bg-[var(--bg-surface)] border border-[var(--border-subtle)] rounded-xl overflow-hidden transition-colors"
                    :class="expandedId === proc.id ? 'border-blue-500/30' : 'hover:border-blue-500/20'"
                >
                    <!-- Procedure row -->
                    <div class="p-4">
                        <div class="flex items-start justify-between gap-3">
                            <div class="min-w-0 flex-1">
                                <div class="flex items-center gap-2 mb-1">
                                    <h3 class="text-sm font-semibold text-[var(--text-primary)] truncate">{{ proc.name }}</h3>
                                    <span class="text-xs text-[var(--text-muted)] shrink-0 font-mono">/{{ proc.slug }}</span>
                                </div>
                                <p class="text-xs text-[var(--text-muted)] line-clamp-2">{{ proc.skill_prompt }}</p>
                                <div class="flex items-center gap-3 mt-2">
                                    <span class="text-xs text-[var(--text-muted)] flex items-center gap-1">
                                        <Paperclip class="w-3 h-3" />{{ proc.files?.length || 0 }} file{{ proc.files?.length !== 1 ? 's' : '' }}
                                    </span>
                                </div>
                            </div>
                            <div class="flex items-center gap-1 shrink-0">
                                <!-- run error inline -->
                                <span v-if="runError === proc.id" class="text-xs text-red-400 mr-1">Failed to start</span>
                                <button
                                    @click="runProcedure(proc)"
                                    :disabled="runningId === proc.id"
                                    class="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg transition-colors bg-blue-500/10 text-blue-400 hover:bg-blue-500/20 disabled:opacity-50"
                                    title="Run procedure"
                                >
                                    <div v-if="runningId === proc.id" class="w-3 h-3 border-2 border-blue-400/30 border-t-blue-400 rounded-full animate-spin"></div>
                                    <Play v-else class="w-3.5 h-3.5 fill-current" />
                                    Run
                                </button>
                                <!-- sessions toggle -->
                                <button
                                    @click="toggleSessions(proc)"
                                    class="p-2 rounded-lg transition-colors"
                                    :class="expandedId === proc.id ? 'text-blue-400 bg-blue-500/10' : 'text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-elevated)]'"
                                    title="View invocations"
                                >
                                    <History class="w-4 h-4" />
                                </button>
                                <button
                                    @click="copyLink(proc)"
                                    class="p-2 text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-elevated)] rounded-lg transition-colors"
                                    title="Copy share link"
                                >
                                    <component :is="copiedId === proc.id ? Check : Link" class="w-4 h-4" :class="copiedId === proc.id ? 'text-green-400' : ''" />
                                </button>
                                <button
                                    @click="openEdit(proc)"
                                    class="p-2 text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--bg-elevated)] rounded-lg transition-colors"
                                    title="Edit"
                                >
                                    <Pencil class="w-4 h-4" />
                                </button>
                                <!-- delete: first click shows confirm, second click deletes -->
                                <button
                                    v-if="deletingId !== proc.id"
                                    @click="deletingId = proc.id"
                                    class="p-2 text-[var(--text-muted)] hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
                                    title="Delete"
                                >
                                    <Trash2 class="w-4 h-4" />
                                </button>
                                <div v-else class="flex items-center gap-1">
                                    <button @click="doDelete(proc)" class="px-2 py-1 text-[10px] rounded-lg font-medium bg-red-500/20 text-red-400 hover:bg-red-500/30 transition-colors">Delete</button>
                                    <button @click="deletingId = null" class="px-2 py-1 text-[10px] rounded-lg font-medium bg-[var(--bg-elevated)] text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors">Cancel</button>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Sessions panel -->
                    <div v-if="expandedId === proc.id" class="border-t border-[var(--border-subtle)]">
                        <div class="px-4 py-2 flex items-center justify-between">
                            <span class="text-xs font-medium text-[var(--text-secondary)]">Invocations</span>
                            <span v-if="!sessionsLoading && sessions[proc.id]" class="text-xs text-[var(--text-muted)]">{{ sessions[proc.id].length }}</span>
                        </div>

                        <div v-if="sessionsLoading" class="flex items-center justify-center py-6">
                            <div class="w-4 h-4 border-2 border-blue-500/30 border-t-blue-500 rounded-full animate-spin"></div>
                        </div>

                        <div v-else-if="!sessions[proc.id] || sessions[proc.id].length === 0" class="px-4 pb-4 text-xs text-[var(--text-muted)]">
                            No invocations yet.
                        </div>

                        <div v-else class="divide-y divide-[var(--border-subtle)]">
                            <a
                                v-for="s in sessions[proc.id]"
                                :key="s.id"
                                :href="`/c/${s.conversation_id}`"
                                class="flex items-center gap-3 px-4 py-2.5 hover:bg-[var(--bg-elevated)] transition-colors group"
                            >
                                <!-- status dot -->
                                <span
                                    class="w-2 h-2 rounded-full shrink-0"
                                    :class="{
                                        'bg-green-400': s.status === 'done',
                                        'bg-blue-400 animate-pulse': s.status === 'in_progress',
                                        'bg-yellow-400': s.status === 'waiting_for_user',
                                        'bg-[var(--text-muted)]': !['done','in_progress','waiting_for_user'].includes(s.status)
                                    }"
                                ></span>

                                <!-- preview / date -->
                                <div class="flex-1 min-w-0">
                                    <p class="text-xs text-[var(--text-primary)] truncate">{{ s.preview || 'Untitled conversation' }}</p>
                                    <p class="text-[10px] text-[var(--text-muted)] mt-0.5">{{ formatDate(s.created_at) }}</p>
                                </div>

                                <!-- status label -->
                                <span
                                    class="text-[10px] font-medium px-1.5 py-0.5 rounded-md shrink-0"
                                    :class="{
                                        'bg-green-500/10 text-green-400': s.status === 'done',
                                        'bg-blue-500/10 text-blue-400': s.status === 'in_progress',
                                        'bg-yellow-500/10 text-yellow-400': s.status === 'waiting_for_user',
                                        'bg-[var(--bg-elevated)] text-[var(--text-muted)]': !['done','in_progress','waiting_for_user'].includes(s.status)
                                    }"
                                >{{ statusLabel(s.status) }}</span>

                                <!-- open arrow -->
                                <ExternalLink class="w-3.5 h-3.5 text-[var(--text-muted)] opacity-0 group-hover:opacity-100 transition-opacity shrink-0" />
                            </a>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Create/Edit Modal -->
    <Teleport to="body">
        <div v-if="showModal" class="fixed inset-0 z-50 flex items-center justify-center p-4">
            <div class="absolute inset-0 bg-black/60 backdrop-blur-sm" @click="closeModal"></div>
            <div class="relative bg-[var(--bg-surface)] border border-[var(--border-subtle)] rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col">
                <!-- Modal Header -->
                <div class="px-6 py-4 border-b border-[var(--border-subtle)] flex items-center justify-between shrink-0">
                    <h3 class="text-base font-semibold text-[var(--text-primary)]">
                        {{ editingId ? 'Edit Procedure' : 'New Procedure' }}
                    </h3>
                    <button @click="closeModal" class="p-1.5 text-[var(--text-muted)] hover:text-[var(--text-primary)] rounded-lg transition-colors">
                        <X class="w-4 h-4" />
                    </button>
                </div>

                <!-- Modal Body -->
                <div class="flex-1 overflow-y-auto px-6 py-4 space-y-4">
                    <!-- Name -->
                    <div>
                        <label class="block text-xs font-medium text-[var(--text-secondary)] mb-1.5">Name</label>
                        <input
                            v-model="form.name"
                            placeholder="e.g. Contract Review"
                            class="w-full bg-[var(--bg-base)] border border-[var(--border-subtle)] rounded-xl px-3 py-2.5 text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] outline-none focus:border-blue-500/50 transition-colors"
                        />
                    </div>

                    <!-- Slug -->
                    <div>
                        <label class="block text-xs font-medium text-[var(--text-secondary)] mb-1.5">URL slug</label>
                        <div class="flex items-center gap-2 bg-[var(--bg-base)] border border-[var(--border-subtle)] rounded-xl px-3 py-2.5">
                            <span class="text-xs text-[var(--text-muted)] shrink-0">/p/</span>
                            <input
                                v-model="form.slug"
                                placeholder="contract-review"
                                class="flex-1 bg-transparent text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] outline-none font-mono"
                            />
                        </div>
                    </div>

                    <!-- Skill Prompt -->
                    <div>
                        <label class="block text-xs font-medium text-[var(--text-secondary)] mb-1.5">Instructions (skill prompt)</label>
                        <textarea
                            v-model="form.skill_prompt"
                            placeholder="Describe what AI should do, what information to collect, how to process it, and what output to produce…"
                            rows="7"
                            class="w-full bg-[var(--bg-base)] border border-[var(--border-subtle)] rounded-xl px-3 py-2.5 text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] outline-none focus:border-blue-500/50 transition-colors resize-none"
                        ></textarea>
                    </div>

                    <!-- Completion condition -->
                    <div>
                        <label class="block text-xs font-medium text-[var(--text-secondary)] mb-1.5">
                            Completion condition
                            <span class="text-[var(--text-muted)] font-normal ml-1">(optional)</span>
                        </label>
                        <input
                            v-model="form.completion_condition"
                            placeholder="Leave blank for default: end with [PROCEDURE_COMPLETE]"
                            class="w-full bg-[var(--bg-base)] border border-[var(--border-subtle)] rounded-xl px-3 py-2.5 text-sm text-[var(--text-primary)] placeholder-[var(--text-muted)] outline-none focus:border-blue-500/50 transition-colors"
                        />
                    </div>

                    <!-- Reference Files -->
                    <div v-if="editingId">
                        <label class="block text-xs font-medium text-[var(--text-secondary)] mb-2">Reference files</label>
                        <div class="space-y-2 mb-2">
                            <div
                                v-for="file in currentFiles"
                                :key="file.id"
                                class="flex items-center justify-between bg-[var(--bg-base)] border border-[var(--border-subtle)] rounded-lg px-3 py-2"
                            >
                                <div class="flex items-center gap-2 min-w-0">
                                    <FileText class="w-3.5 h-3.5 text-[var(--text-muted)] shrink-0" />
                                    <span class="text-xs text-[var(--text-primary)] truncate">{{ file.original_name }}</span>
                                    <span class="text-xs text-[var(--text-muted)] shrink-0">{{ formatBytes(file.file_size) }}</span>
                                </div>
                                <button
                                    @click="removeFile(file)"
                                    class="p-1 text-[var(--text-muted)] hover:text-red-400 rounded transition-colors shrink-0"
                                >
                                    <X class="w-3.5 h-3.5" />
                                </button>
                            </div>
                        </div>
                        <!-- Upload -->
                        <label class="flex items-center gap-2 px-3 py-2 bg-[var(--bg-base)] border border-dashed border-[var(--border-subtle)] rounded-lg cursor-pointer hover:border-blue-500/40 transition-colors">
                            <Upload class="w-4 h-4 text-[var(--text-muted)]" />
                            <span class="text-xs text-[var(--text-muted)]">
                                {{ uploading ? 'Uploading…' : 'Add file (PDF, DOCX, TXT)' }}
                            </span>
                            <input type="file" class="hidden" accept=".pdf,.docx,.txt,.md,.csv" @change="handleFileUpload" :disabled="uploading" />
                        </label>
                    </div>
                    <div v-else class="text-xs text-[var(--text-muted)] bg-[var(--bg-base)] rounded-xl px-3 py-2.5 border border-[var(--border-subtle)]">
                        You can upload reference files after creating the procedure.
                    </div>
                </div>

                <!-- Modal Footer -->
                <div class="px-6 py-4 border-t border-[var(--border-subtle)] flex items-center justify-between shrink-0">
                    <div v-if="modalError" class="text-xs text-red-400">{{ modalError }}</div>
                    <div v-else></div>
                    <div class="flex gap-2">
                        <button @click="closeModal" class="px-4 py-2 text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors">Cancel</button>
                        <button @click="save" :disabled="saving" class="btn-primary text-sm gap-2">
                            <Loader2 v-if="saving" class="w-3.5 h-3.5 animate-spin" />
                            {{ saving ? 'Saving…' : (editingId ? 'Save changes' : 'Create') }}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </Teleport>
</template>

<script setup>
import { ref, watch, onMounted } from 'vue'
import { Plus, Workflow, Pencil, Trash2, Link, Check, X, FileText, Upload, Paperclip, Loader2, Play, History, ExternalLink } from 'lucide-vue-next'
import { useApi } from '../composables/useApi.js'

const { getProcedures, createProcedure, updateProcedure, deleteProcedure, uploadProcedureFile, deleteProcedureFile, createProcedureSession, getProcedureSessions } = useApi()

const runningId = ref(null)
const runError = ref(null)

const runProcedure = async (proc) => {
    if (runningId.value) return
    runningId.value = proc.id
    runError.value = null
    try {
        const data = await createProcedureSession(proc.slug)
        window.location.href = `/c/${data.conversation_id}`
    } catch {
        runError.value = proc.id
        setTimeout(() => { if (runError.value === proc.id) runError.value = null }, 3000)
    } finally {
        runningId.value = null
    }
}

const procedures = ref([])
const loading = ref(true)
const showModal = ref(false)
const editingId = ref(null)
const deletingId = ref(null)
const currentFiles = ref([])
const saving = ref(false)
const uploading = ref(false)
const modalError = ref('')
const copiedId = ref(null)

const expandedId = ref(null)
const sessions = ref({})
const sessionsLoading = ref(false)

const form = ref({ name: '', slug: '', skill_prompt: '', completion_condition: '' })

const formatBytes = (b) => {
    if (!b) return ''
    if (b < 1024) return b + ' B'
    if (b < 1024 * 1024) return (b / 1024).toFixed(0) + ' KB'
    return (b / (1024 * 1024)).toFixed(1) + ' MB'
}

const formatDate = (iso) => {
    if (!iso) return ''
    const d = new Date(iso)
    return d.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' })
}

const statusLabel = (s) => {
    if (s === 'done') return 'Done'
    if (s === 'in_progress') return 'In progress'
    if (s === 'waiting_for_user') return 'Waiting'
    return s
}

const toggleSessions = async (proc) => {
    if (expandedId.value === proc.id) {
        expandedId.value = null
        return
    }
    expandedId.value = proc.id
    if (sessions.value[proc.id]) return
    sessionsLoading.value = true
    try {
        sessions.value[proc.id] = await getProcedureSessions(proc.id)
    } catch {
        sessions.value[proc.id] = []
    } finally {
        sessionsLoading.value = false
    }
}

const slugify = (s) => s.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')

watch(() => form.value.name, (v) => {
    if (!editingId.value) form.value.slug = slugify(v)
})

const load = async () => {
    loading.value = true
    try { procedures.value = await getProcedures() }
    catch { /* ignore */ }
    finally { loading.value = false }
}

const openCreate = () => {
    editingId.value = null
    currentFiles.value = []
    form.value = { name: '', slug: '', skill_prompt: '', completion_condition: '' }
    modalError.value = ''
    showModal.value = true
}

const openEdit = (proc) => {
    editingId.value = proc.id
    currentFiles.value = [...(proc.files || [])]
    form.value = {
        name: proc.name,
        slug: proc.slug,
        skill_prompt: proc.skill_prompt,
        completion_condition: proc.completion_condition || '',
    }
    modalError.value = ''
    showModal.value = true
}

const closeModal = () => { showModal.value = false; editingId.value = null }

const save = async () => {
    if (!form.value.name.trim()) { modalError.value = 'Name is required'; return }
    if (!form.value.skill_prompt.trim()) { modalError.value = 'Instructions are required'; return }
    saving.value = true
    modalError.value = ''
    try {
        const payload = {
            name: form.value.name.trim(),
            slug: form.value.slug.trim() || slugify(form.value.name),
            skill_prompt: form.value.skill_prompt.trim(),
            completion_condition: form.value.completion_condition.trim() || null,
        }
        if (editingId.value) {
            await updateProcedure(editingId.value, payload)
        } else {
            await createProcedure(payload)
        }
        await load()
        closeModal()
    } catch (e) {
        modalError.value = e.message
    } finally {
        saving.value = false
    }
}

const doDelete = async (proc) => {
    deletingId.value = null
    try {
        await deleteProcedure(proc.id)
        await load()
    } catch { /* ignore */ }
}

const handleFileUpload = async (e) => {
    const file = e.target.files?.[0]
    if (!file || !editingId.value) return
    uploading.value = true
    try {
        const result = await uploadProcedureFile(editingId.value, file)
        currentFiles.value.push({ id: result.id, original_name: result.original_name, file_size: result.file_size })
        await load()
    } catch (err) {
        modalError.value = err.message
    } finally {
        uploading.value = false
        e.target.value = ''
    }
}

const removeFile = async (file) => {
    if (!editingId.value) return
    try {
        await deleteProcedureFile(editingId.value, file.id)
        currentFiles.value = currentFiles.value.filter(f => f.id !== file.id)
        await load()
    } catch { /* ignore */ }
}

const copyLink = (proc) => {
    const url = `${window.location.origin}/p/${proc.slug}`
    navigator.clipboard.writeText(url).catch(() => {})
    copiedId.value = proc.id
    setTimeout(() => copiedId.value = null, 2000)
}

onMounted(load)
</script>
