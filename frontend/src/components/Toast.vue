<template>
    <Teleport to="body">
        <div class="fixed bottom-4 right-4 z-[100] flex flex-col gap-2">
            <TransitionGroup name="toast">
                <div
                    v-for="toast in toasts"
                    :key="toast.id"
                    class="flex items-center gap-3 px-4 py-3 rounded-xl shadow-lg backdrop-blur-sm min-w-[280px] max-w-[400px]"
                    :class="toastClasses[toast.type]"
                >
                    <!-- Icon -->
                    <component :is="icons[toast.type]" class="w-5 h-5 flex-shrink-0" />

                    <!-- Message -->
                    <span class="text-sm font-medium flex-1">{{ toast.message }}</span>

                    <!-- Close button -->
                    <button
                        @click="removeToast(toast.id)"
                        class="p-1 rounded-lg opacity-60 hover:opacity-100 transition-opacity"
                    >
                        <X class="w-4 h-4" />
                    </button>
                </div>
            </TransitionGroup>
        </div>
    </Teleport>
</template>

<script setup>
import { CheckCircle, XCircle, Info, X } from 'lucide-vue-next'
import { useToast } from '../composables/useToast'

const { toasts, removeToast } = useToast()

const icons = {
    success: CheckCircle,
    error: XCircle,
    info: Info
}

const toastClasses = {
    success: 'bg-emerald-500/90 text-white',
    error: 'bg-red-500/90 text-white',
    info: 'bg-blue-500/90 text-white'
}
</script>

<style scoped>
.toast-enter-active {
    transition: all 0.3s ease-out;
}

.toast-leave-active {
    transition: all 0.2s ease-in;
}

.toast-enter-from {
    opacity: 0;
    transform: translateX(100px);
}

.toast-leave-to {
    opacity: 0;
    transform: translateX(100px);
}

.toast-move {
    transition: transform 0.3s ease;
}
</style>
