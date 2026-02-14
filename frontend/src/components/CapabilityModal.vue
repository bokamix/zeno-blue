<template>
    <Teleport to="body">
        <Transition name="modal">
            <div
                class="modal-backdrop"
                @click.self="$emit('close')"
            >
                <div class="modal-card">
                    <p class="modal-text">{{ text }}</p>
                    <div class="modal-actions">
                        <button
                            @click="$emit('use', text)"
                            class="btn-primary"
                        >
                            Use this
                        </button>
                        <button
                            @click="$emit('close')"
                            class="btn-secondary"
                        >
                            Close
                        </button>
                    </div>
                </div>
            </div>
        </Transition>
    </Teleport>
</template>

<script setup>
defineProps({
    text: {
        type: String,
        required: true
    }
})

defineEmits(['use', 'close'])
</script>

<style scoped>
.modal-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.7);
    backdrop-filter: blur(4px);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 100;
    padding: 1rem;
}

.modal-card {
    background: var(--bg-surface, #1e1e1e);
    border: 1px solid var(--border-subtle, rgba(255, 255, 255, 0.1));
    border-radius: 16px;
    padding: 2rem;
    max-width: 500px;
    width: 100%;
    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
}

.modal-text {
    font-size: 1.125rem;
    line-height: 1.6;
    color: var(--text-primary);
    margin-bottom: 1.5rem;
}

.modal-actions {
    display: flex;
    gap: 0.75rem;
    justify-content: flex-end;
}

.btn-primary {
    padding: 0.625rem 1.25rem;
    font-size: 0.875rem;
    font-weight: 500;
    color: white;
    background: #2563eb;
    border: none;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.2s;
}

.btn-primary:hover {
    background: #1d4ed8;
}

.btn-secondary {
    padding: 0.625rem 1.25rem;
    font-size: 0.875rem;
    font-weight: 500;
    color: var(--text-secondary);
    background: var(--bg-hover, rgba(255, 255, 255, 0.05));
    border: 1px solid var(--border-subtle, rgba(255, 255, 255, 0.1));
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.2s;
}

.btn-secondary:hover {
    background: var(--bg-hover, rgba(255, 255, 255, 0.1));
    color: var(--text-primary);
}

/* Transition */
.modal-enter-active,
.modal-leave-active {
    transition: opacity 0.2s ease;
}

.modal-enter-active .modal-card,
.modal-leave-active .modal-card {
    transition: transform 0.2s ease, opacity 0.2s ease;
}

.modal-enter-from,
.modal-leave-to {
    opacity: 0;
}

.modal-enter-from .modal-card,
.modal-leave-to .modal-card {
    transform: scale(0.95);
    opacity: 0;
}
</style>
