<template>
    <div class="video-viewer flex items-center justify-center">
        <video
            :src="url"
            controls
            class="max-w-full max-h-[80vh] rounded bg-black"
            @error="onError"
        >
            Your browser does not support the video tag.
        </video>
    </div>
</template>

<script setup>
const props = defineProps({
    url: { type: String, required: true },
    filename: { type: String, default: 'video' }
})

const onError = (e) => {
    console.error('Failed to load video:', e)
}
</script>
