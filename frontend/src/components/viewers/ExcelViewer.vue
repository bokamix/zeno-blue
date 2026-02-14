<template>
    <div class="excel-viewer">
        <div v-if="loading" class="flex items-center justify-center h-64">
            <span class="text-[var(--text-muted)]">Parsing spreadsheet...</span>
        </div>

        <!-- Sheet tabs -->
        <div v-else-if="sheets.length > 0" class="flex flex-col h-full">
            <div v-if="sheets.length > 1" class="flex gap-1 mb-3 border-b border-[var(--border-subtle)] pb-2">
                <button
                    v-for="(sheet, idx) in sheets"
                    :key="sheet.name"
                    @click="activeSheet = idx"
                    class="px-3 py-1.5 text-sm rounded-t transition-colors"
                    :class="activeSheet === idx
                        ? 'bg-[var(--bg-elevated)] text-[var(--text-primary)]'
                        : 'text-[var(--text-muted)] hover:text-[var(--text-secondary)] hover:bg-[var(--bg-surface)]'"
                >
                    {{ sheet.name }}
                </button>
            </div>

            <!-- Table -->
            <div class="overflow-x-auto flex-1">
                <table class="min-w-full text-sm border-collapse">
                    <tbody>
                        <tr
                            v-for="(row, rowIdx) in sheets[activeSheet]?.data || []"
                            :key="rowIdx"
                            :class="rowIdx === 0 ? 'bg-[var(--bg-surface)]' : 'hover:bg-[var(--bg-surface)]/50'"
                        >
                            <td
                                v-for="(cell, colIdx) in row"
                                :key="colIdx"
                                class="px-3 py-2 border border-[var(--border-subtle)] text-[var(--text-secondary)]"
                                :class="rowIdx === 0 ? 'font-medium text-[var(--text-primary)]' : ''"
                            >
                                {{ cell ?? '' }}
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>

            <div class="text-xs text-[var(--text-muted)] mt-2">
                {{ sheets[activeSheet]?.data?.length || 0 }} rows
            </div>
        </div>

        <div v-else-if="error" class="text-red-400 p-4">
            {{ error }}
        </div>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import * as XLSX from 'xlsx'

const props = defineProps({
    url: { type: String, required: true }
})

const loading = ref(true)
const sheets = ref([])
const activeSheet = ref(0)
const error = ref(null)

onMounted(async () => {
    try {
        const res = await fetch(props.url)
        const arrayBuffer = await res.arrayBuffer()
        const workbook = XLSX.read(arrayBuffer, { type: 'array' })

        sheets.value = workbook.SheetNames.map(name => ({
            name,
            data: XLSX.utils.sheet_to_json(workbook.Sheets[name], { header: 1 })
        }))
    } catch (e) {
        console.error('Failed to load Excel:', e)
        error.value = 'Failed to parse spreadsheet: ' + e.message
    } finally {
        loading.value = false
    }
})
</script>
