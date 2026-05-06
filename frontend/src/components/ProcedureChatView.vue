<template>
    <div class="flex flex-col h-screen items-center justify-center bg-[var(--bg-base)] gap-4">
        <div v-if="error" class="text-center max-w-sm px-6">
            <AlertCircle class="w-10 h-10 text-red-400 mx-auto mb-3" />
            <p class="text-sm font-medium text-[var(--text-primary)] mb-1">{{ error }}</p>
            <a :href="`/p/${slug}`" class="text-xs text-blue-400 hover:underline">Try again</a>
        </div>

        <template v-else>
            <div class="w-8 h-8 border-2 border-blue-500/30 border-t-blue-500 rounded-full animate-spin"></div>
            <p class="text-sm text-[var(--text-muted)]">{{ message }}</p>
        </template>
    </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { AlertCircle } from 'lucide-vue-next'
import { useApi } from '../composables/useApi.js'

const props = defineProps({
    slug: String,
    initialSessionId: { type: String, default: null },
})

const { getProcedureInfo, createProcedureSession, getProcedureSession } = useApi()

const error   = ref(null)
const message = ref('Loading procedure…')

onMounted(async () => {
    // If session ID already in URL — redirect straight to chat
    if (props.initialSessionId) {
        try {
            const data = await getProcedureSession(props.slug, props.initialSessionId)
            window.location.replace(`/c/${data.conversation_id}`)
            return
        } catch { /* fall through to error */ }
        error.value = 'Session not found.'
        return
    }

    // No session yet → verify procedure exists, create session, redirect
    try {
        message.value = 'Loading procedure…'
        await getProcedureInfo(props.slug)
    } catch {
        error.value = 'Procedure not found or has been deactivated.'
        return
    }

    try {
        message.value = 'Starting…'
        const data = await createProcedureSession(props.slug)
        // Redirect to the normal chat with this conversation
        window.location.replace(`/c/${data.conversation_id}`)
    } catch (e) {
        error.value = e.message
    }
})
</script>
