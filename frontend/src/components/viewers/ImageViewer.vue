<template>
    <div class="image-viewer flex items-center justify-center">
        <img
            :src="url"
            :alt="filename"
            class="max-w-full max-h-[80vh] object-contain rounded"
            @error="onError"
        />
    </div>
</template>

<script setup>
const props = defineProps({
    url: { type: String, required: true },
    filename: { type: String, default: 'image' }
})

const onError = (e) => {
    console.error('Failed to load image:', e)
}
</script>
