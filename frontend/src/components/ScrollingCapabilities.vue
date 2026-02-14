<template>
    <div class="scrolling-capabilities" :class="{ 'input-focused': allPaused }">
        <!-- Columns - background decoration only -->
        <div
            v-for="(column, idx) in columns"
            :key="idx"
            class="column"
        >
            <div
                class="column-inner"
                :class="['paused-' + allPaused, 'delay-' + idx]"
            >
                <div
                    v-for="(item, i) in getColumnItems(column)"
                    :key="i"
                    class="item"
                >
                    {{ item }}
                </div>
            </div>
        </div>

    </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick, watch } from 'vue'

const props = defineProps({
    capabilities: {
        type: Array,
        default: () => []
    }
})

const columns = ref([[], [], [], []])
const allPaused = ref(false)

// Check if an input is currently focused
const checkActiveElement = () => {
    const el = document.activeElement
    if (el && (el.tagName === 'INPUT' || el.tagName === 'TEXTAREA' || el.isContentEditable)) {
        allPaused.value = true
    }
}

// Shuffle and distribute items into columns
const distributeCapabilities = () => {
    if (props.capabilities.length === 0) return

    // Reset columns
    columns.value = [[], [], [], []]

    const shuffled = [...props.capabilities].sort(() => Math.random() - 0.5)
    shuffled.forEach((item, i) => {
        columns.value[i % 4].push(item)
    })
}

// Watch for capabilities changes (e.g., when locale changes)
watch(() => props.capabilities, distributeCapabilities, { immediate: true })

onMounted(() => {
    distributeCapabilities()

    // Check if input is already focused when component mounts
    // Use multiple checks to catch async focus from parent components
    checkActiveElement()
    nextTick(checkActiveElement)
    requestAnimationFrame(checkActiveElement)

    // Pause animations when any input/textarea is focused (user is typing)
    document.addEventListener('focusin', handleFocusIn)
    document.addEventListener('focusout', handleFocusOut)
})

onUnmounted(() => {
    document.removeEventListener('focusin', handleFocusIn)
    document.removeEventListener('focusout', handleFocusOut)
})

const handleFocusIn = (e) => {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.isContentEditable) {
        allPaused.value = true
    }
}

const handleFocusOut = (e) => {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.isContentEditable) {
        allPaused.value = false
    }
}

// Duplicate items for seamless loop
const getColumnItems = (column) => {
    return [...column, ...column]
}

</script>

<style scoped>
.scrolling-capabilities {
    position: absolute;
    inset: 0;
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 1.5rem;
    overflow: hidden;
    padding: 0 3rem;
    touch-action: none;
    overscroll-behavior: none;
}

.column {
    overflow: hidden;
    position: relative;
    z-index: 1;
    touch-action: none;
    height: 100%;
}

.column-inner {
    display: flex;
    flex-direction: column;
    gap: 1rem;
    animation: scroll-down linear infinite;
    min-height: 200vh;
    will-change: transform;
    transform: translateZ(0);
    backface-visibility: hidden;
}

/* Different speeds for parallax effect - slow for subtle background */
.column-inner.delay-0 { animation-duration: 120s; }
.column-inner.delay-1 { animation-duration: 150s; }
.column-inner.delay-2 { animation-duration: 130s; }
.column-inner.delay-3 { animation-duration: 140s; }

.column-inner.paused-true {
    animation-play-state: paused;
}

@keyframes scroll-down {
    0% {
        transform: translateY(-100vh);
    }
    100% {
        transform: translateY(0);
    }
}

.item {
    font-size: 12px;
    line-height: 1.5;
    color: var(--text-secondary);
    opacity: 0.12;
    padding: 12px 16px;
    pointer-events: none;
    border-radius: 16px;
    background: var(--bg-surface);
    border: 1px solid var(--border-subtle);
}

/* Light mode - subtle but visible */
[data-theme="light"] .item {
    opacity: 0.25;
    background: var(--bg-surface);
    border: 1px solid rgba(0, 0, 0, 0.06);
}

/* Background items are non-interactive - no hover effects */

/* Responsive - 4 columns on desktop, 3 on laptop, 2 on mobile */
@media (max-width: 1024px) {
    .scrolling-capabilities {
        grid-template-columns: repeat(3, 1fr);
        padding: 0 2rem;
    }
    .column:nth-child(4) {
        display: none;
    }
}

@media (max-width: 640px) {
    .scrolling-capabilities {
        grid-template-columns: repeat(2, 1fr);
        padding: 0 1rem;
        gap: 0.75rem;
    }
    .column:nth-child(3),
    .column:nth-child(4) {
        display: none;
    }
    .item {
        font-size: 11px;
        padding: 10px 12px;
        border-radius: 12px;
    }
    /* Even slower animations on mobile to reduce CPU load */
    .column-inner.delay-0 { animation-duration: 180s; }
    .column-inner.delay-1 { animation-duration: 200s; }
}

/* Hide animations completely when input is focused (mobile performance) */
@media (max-width: 768px) {
    .scrolling-capabilities.input-focused {
        visibility: hidden;
        pointer-events: none;
    }
}

/* Accessibility - respect reduced motion preference */
@media (prefers-reduced-motion: reduce) {
    .column-inner {
        animation: none;
    }
}
</style>
