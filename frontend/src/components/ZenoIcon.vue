<template>
    <span class="zeno-icon" :style="{ width: size + 'px', height: size + 'px' }">
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path
                d="M13 2L4 14h7l-1 8 9-12h-7l1-8z"
                :fill="color"
                stroke-linejoin="round"
            />
        </svg>
    </span>
</template>

<script setup>
defineProps({
    size: {
        type: [Number, String],
        default: 24
    },
    color: {
        type: String,
        default: 'currentColor'
    }
})
</script>
